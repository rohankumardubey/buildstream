import os
import pytest
import zipfile

from buildstream._pipeline import PipelineError
from buildstream import _yaml
from tests.testutils import cli

DATA_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'zip',
)


def _assemble_zip(workingdir, dstfile):
    old_dir = os.getcwd()
    os.chdir(workingdir)
    with zipfile.ZipFile(dstfile, "w") as zip:
        for root, dirs, files in os.walk('.'):
            names = dirs + files
            names = [os.path.join(root, name) for name in names]
            for name in names:
                zip.write(name)
    os.chdir(old_dir)


def generate_project(project_dir, tmpdir):
    project_file = os.path.join(project_dir, "project.conf")
    _yaml.dump({
        'name': 'foo',
        'aliases': {
            'tmpdir': "file:///" + str(tmpdir)
        }
    }, project_file)


# Test that without ref, consistency is set appropriately.
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'no-ref'))
def test_no_ref(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)
    assert cli.get_element_state(project, 'target.bst') == 'no reference'


# Test that when I fetch a nonexistent URL, errors are handled gracefully.
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'fetch'))
def test_fetch_bad_url(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)

    # Try to fetch it
    result = cli.run(project=project, args=[
        'fetch', 'target.bst'
    ])
    assert result.exit_code != 0
    assert result.exception
    assert isinstance(result.exception, PipelineError)


# Test that when I fetch with an invalid ref, it fails.
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'fetch'))
def test_fetch_bad_ref(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)

    # Create a local tar
    src_zip = os.path.join(str(tmpdir), "a.zip")
    _assemble_zip(os.path.join(str(datafiles), "content"), src_zip)

    # Try to fetch it
    result = cli.run(project=project, args=[
        'fetch', 'target.bst'
    ])
    assert result.exit_code != 0
    assert result.exception
    assert isinstance(result.exception, PipelineError)


# Test that when tracking with a ref set, there is a warning
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'fetch'))
def test_track_warning(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)

    # Create a local tar
    src_zip = os.path.join(str(tmpdir), "a.zip")
    _assemble_zip(os.path.join(str(datafiles), "content"), src_zip)

    # Track it
    result = cli.run(project=project, args=[
        'track', 'target.bst'
    ])
    assert result.exit_code == 0
    assert "Potential man-in-the-middle attack!" in result.stderr


def _list_dir_contents(srcdir):
    contents = set()
    for _, dirs, files in os.walk(srcdir):
        for d in dirs:
            contents.add(d)
        for f in files:
            contents.add(f)
    return contents


# Test that a staged checkout matches what was tarred up, with the default first subdir
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'fetch'))
def test_stage_default_basedir(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    # Create a local tar
    src_zip = os.path.join(str(tmpdir), "a.zip")
    _assemble_zip(os.path.join(str(datafiles), "content"), src_zip)

    # Track, fetch, build, checkout
    result = cli.run(project=project, args=['track', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['fetch', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['build', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['checkout', 'target.bst', checkoutdir])
    assert result.exit_code == 0

    # Check that the content of the first directory is checked out (base-dir: '*')
    original_dir = os.path.join(str(datafiles), "content", "a")
    original_contents = _list_dir_contents(original_dir)
    checkout_contents = _list_dir_contents(checkoutdir)
    assert(checkout_contents == original_contents)


# Test that a staged checkout matches what was tarred up, with an empty base-dir
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'no-basedir'))
def test_stage_no_basedir(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    # Create a local tar
    src_zip = os.path.join(str(tmpdir), "a.zip")
    _assemble_zip(os.path.join(str(datafiles), "content"), src_zip)

    # Track, fetch, build, checkout
    result = cli.run(project=project, args=['track', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['fetch', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['build', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['checkout', 'target.bst', checkoutdir])
    assert result.exit_code == 0

    # Check that the full content of the tarball is checked out (base-dir: '')
    original_dir = os.path.join(str(datafiles), "content")
    original_contents = _list_dir_contents(original_dir)
    checkout_contents = _list_dir_contents(checkoutdir)
    assert(checkout_contents == original_contents)


# Test that a staged checkout matches what was tarred up, with an explicit basedir
@pytest.mark.datafiles(os.path.join(DATA_DIR, 'explicit-basedir'))
def test_stage_explicit_basedir(cli, tmpdir, datafiles):
    project = os.path.join(datafiles.dirname, datafiles.basename)
    generate_project(project, tmpdir)
    checkoutdir = os.path.join(str(tmpdir), "checkout")

    # Create a local tar
    src_zip = os.path.join(str(tmpdir), "a.zip")
    _assemble_zip(os.path.join(str(datafiles), "content"), src_zip)

    # Track, fetch, build, checkout
    result = cli.run(project=project, args=['track', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['fetch', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['build', 'target.bst'])
    assert result.exit_code == 0
    result = cli.run(project=project, args=['checkout', 'target.bst', checkoutdir])
    assert result.exit_code == 0

    # Check that the content of the first directory is checked out (base-dir: '*')
    original_dir = os.path.join(str(datafiles), "content", "a")
    original_contents = _list_dir_contents(original_dir)
    checkout_contents = _list_dir_contents(checkoutdir)
    assert(checkout_contents == original_contents)
