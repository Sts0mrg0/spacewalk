#
# Copyright (c) 2008 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

""" Code for tagging Spacewalk/Satellite packages. """

import os
import re
import commands
import StringIO

from time import strftime

from spacewalk.releng.common import find_spec_file, run_command, BuildCommon, \
        debug

class Tagger(BuildCommon):
    """
    Parent package tagging class.

    Includes functionality for a standard Spacewalk package build. Packages
    which require other unusual behavior can subclass this to inject the
    desired behavior.
    """
    def __init__(self, debug=False):
        BuildCommon.__init__(self, debug)

        self.spec_file = os.path.join(self.full_project_dir,
                self.spec_file_name)

        self.today = strftime("%a %b %d %Y")
        (self.git_user, self.git_email) = self._get_git_user_info()
        self.changelog_regex = re.compile('\\*\s%s\s%s\s<%s>' % (self.today,
            self.git_user, self.git_email))

    def run(self, options):
        """
        Perform the actions requested of the tagger.

        NOTE: this method may do nothing if the user requested no build actions
        be performed. (i.e. only release tagging, etc)
        """
        if options.tag_version:
            self._tag_version()

    def _tag_version(self):
        """ Tag a new version of the package. (i.e. x.y.z+1) """
        self._check_today_in_changelog()
        new_version = self._bump_version()
        self._update_changelog(new_version)
        self._update_package_metadata(new_version)

        # Create the actual git tag for this version:

    def _check_today_in_changelog(self):
        """ 
        Verify that there is a changelog entry for today's date and the git 
        user's name and email address.

        i.e. * Thu Nov 27 2008 My Name <me@example.com>
        """
        f = open(self.spec_file, 'r')
        found_changelog = False
        for line in f.readlines():
            match = self.changelog_regex.match(line)
            if not found_changelog and match:
                found_changelog = True
        f.close()

        if not found_changelog:
            # TODO: Instead of dying here, we could try to add one automatically
            # and generate the changelog entries from the first line of the git commit
            # history for all commits since the last package version was tagged.
            raise Exception("No changelog entry found: '* %s %s <%s>'" % (
                self.today, self.git_user, self.git_email))
        else:
            debug("Found changelog entry.")

    def _update_changelog(self, new_version):
        """
        Update the changelog with the new version.
        """
        # Not thrilled about having to re-read the file here but we need to
        # check for the changelog entry before making any modifications, then
        # bump the version, then update the changelog.
        f = open(self.spec_file, 'r')
        buf = StringIO.StringIO()
        for line in f.readlines():
            match = self.changelog_regex.match(line)
            if match:
                buf.write("%s %s\n" % (match.group(), new_version))
            else:
                buf.write(line)
        f.close()

        # Write out the new file contents with our modified changelog entry:
        f = open(self.spec_file, 'w')
        f.write(buf.getvalue())
        f.close()
        buf.close()

    def _bump_version(self):
        # TODO: Do this here instead of calling out to an external Perl script:
        old_version = self._get_spec_version()
        cmd = "perl %s/bump-version.pl bump-version --specfile %s" % \
                (self.rel_eng_dir, self.spec_file)
        run_command(cmd)
        new_version = self._get_spec_version()
        print "Tagging new version of %s: %s -> %s" % (self.project_name,
            old_version, new_version)
        return new_version

    def _update_package_metadata(self, new_version, release=False):
        """
        We track package metadata in the rel-eng/packages/ directory. Each
        file here stores the latest package version (for the git branch you
        are on) as well as the relative path to the project's code. (from the
        git root)

        Set release to True when bumping the package release. (as opposed to
        it's version)
        """
        self._clear_package_metadata()

        # Write out our package metadata:
        metadata_file = os.path.join(self.rel_eng_dir, "packages",
                self.project_name)
        f = open(metadata_file, 'w')
        f.write("%s %s" % (new_version, self.relative_project_dir))
        f.close()

        # Git add it (in case it's a new file):
        run_command("git add %s" % metadata_file)
        run_command("git add %s" % os.path.join(self.full_project_dir,
            self.spec_file_name))

        release_type = "release"
        if release:
            release_type = "minor release"

        run_command('git commit -m "Automatic commit of package ' +
                '[%s] %s [%s]."' % (self.project_name, release_type,
                    new_version))

        tag_msg = "Tagging package [%s] version [%s] in directory [%s]." % \
                (self.project_name, new_version, self.relative_project_dir)

        tag = "%s-%s" % (self.project_name, new_version)
        print "Creating new tag: %s" % tag
        run_command('git tag -m "%s" %s' % (tag_msg, tag))

    def _clear_package_metadata(self):
        """
        Remove all rel-eng/packages/ files that have a relative path
        matching the package we're tagging a new version of. Normally
        this just removes the previous package file but if we were
        renaming oldpackage to newpackage, this would git rm
        rel-eng/packages/oldpackage and add
        rel-eng/packages/spacewalk-newpackage.
        """
        metadata_dir = os.path.join(self.rel_eng_dir, "packages")
        for filename in os.listdir(metadata_dir):
            metadata_file = os.path.join(metadata_dir, filename) # full path

            if os.path.isdir(metadata_file) or filename.startswith("."):
                continue

            temp_file = open(metadata_file, 'r')
            (version, relative_dir) = temp_file.readline().split(" ")
            relative_dir = relative_dir.strip() # sometimes has a newline

            if relative_dir == self.relative_project_dir:
                debug("Found metadata for our prefix: %s" %
                        metadata_file)
                debug("   version: %s" % version)
                debug("   dir: %s" % relative_dir)
                if filename == self.project_name:
                    debug("Updating %s with new version." %
                            metadata_file)
                else:
                    print "WARNING: %s also references %s" % (filename,
                            self.relative_project_dir)
                    print "Assuming package has been renamed and removing it."
                    run_command("git rm %s" % metadata_file)

    def _get_git_user_info(self):
        """ Return the user.name and user.email git config values. """
        return (run_command('git config --get user.name'), 
                run_command('git config --get user.email'))

    def _get_spec_version(self):
        """ Get the package version from the spec file. """
        command = """rpm -q --qf '%%{version}-%%{release}\n' --define "_sourcedir %s" --define 'dist %%undefined' --specfile %s | head -1""" % (self.full_project_dir, self.spec_file_name)
        return run_command(command)



