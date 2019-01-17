#!/usr/bin/python
#
# Copyright 2018 Sebastien Tomasi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from autopkglib import Processor, ProcessorError

import json
import requests
import os
import base64
import xml.etree.ElementTree as ET

__all__ = ["PatchManagement"]


class PatchManagement(Processor):
    description = ("Create a software tile and a patch policy scoped to a testing group and exclude a NOT MANAGED group. The templates are in the parent folder")
    input_variables = {
        "jss_importer_summary_result": {
            "required": True,
            "description": ("Description of interesting results.")
        },
        "patch_server": {
            "required": True,
            "description": ("Patch server where the definition exists")
        },
        "softwaretitleconfig_id":{
            "required": True,
            "description": ("Jamf software title settings ID")
        },
    }
    output_variables = {
        "PatchManagement_summary_result": {
            "description": "Description of interesting results."
        },
    }

    __doc__ = description

    def jamf_requests(self, url, action, payload=None):
        b64val = base64.b64encode("{0}:{1}".format(self.env["API_USERNAME"], self.env["API_PASSWORD"]))
        authorization = "Basic {0}".format(b64val)
        headers = {
            "Accept": "application/xml",
            'Authorization': authorization
        }
        url_response = requests.request(action, url, data=payload, headers=headers)
        if url_response.status_code == 500:
            raise Exception("The server {0} does not respond correctly".format(self.env["JSS_URL"]))
        return url_response

    def xml_lookup(self, data, lookup_path):
        root = ET.ElementTree(ET.fromstring(data))
        found_value = []
        for value in root.findall(lookup_path):
            found_value.append(value.text)
        return found_value

    def find_file_in_override_postprocessors_path(self, path):
        override_path = ""
        repo_path = ""
        for entry in self.env["RECIPE_SEARCH_DIRS"]:
            if os.path.exists(os.path.join(entry,"PostProcessors",path)):
                repo_path = os.path.join(entry,"PostProcessors",path)
        for entry in self.env["RECIPE_OVERRIDE_DIRS"]:
            if os.path.exists(os.path.join(os.path.expanduser(entry),path)):
                override_path = os.path.join(os.path.expanduser(entry),path)
        if override_path:
            return override_path
        else:
            return repo_path

    def replace_text(self, text, replace_dict):  # pylint: disable=no-self-use
        """Substitute items in a text string.
        Args:
            text: A string with embedded %tags%.
            replace_dict: A dict, where
                key: Corresponds to the % delimited tag in text.
                value: Text to swap in.
        Returns:
            The text after replacement.
        """
        for key, value in replace_dict.iteritems():
            # Wrap our keys in % to match template tags.
            text = text.replace("%%%s%%" % key, value)
        return text

    def get_pkg_id(self, pkg_name):
        url = "{0}/JSSResource/packages/name/{1}".format(self.env["JSS_URL"], pkg_name)
        response = self.jamf_requests(url, "GET")
        pkg_id = self.xml_lookup(response.text, "id")
        return pkg_id[0]

    def update_softwaretitle(self,replace_dict, jamf_id):
        with open(self.find_file_in_override_postprocessors_path("SoftwareTitle.xml"), "r") as template_file:
            text = template_file.read()
        template = self.replace_text(text, replace_dict)
        url = "{0}/JSSResource/patchsoftwaretitles/id/{1}".format(self.env["JSS_URL"],str(jamf_id))
        u_softwaretitle = self.jamf_requests(url, "PUT", template)
        return u_softwaretitle

    def create_update_patchpolicy(self, replace_dict):
        with open(self.find_file_in_override_postprocessors_path("PatchPolicy.xml"), "r") as template_file:
            text = template_file.read()
        template = self.replace_text(text, replace_dict)
        url = "{0}/JSSResource/patchpolicies/softwaretitleconfig/id/{1}".format(self.env["JSS_URL"],str(replace_dict["JAMF_ID"]))
        cu_patchpolicy = self.jamf_requests(url, "POST", template)
        return cu_patchpolicy

    def summarize(self, report):
        """If anything has been added or updated, report back."""
        # Only summarize if something has happened.
        # if any(value for value in self.env["jss_changed_objects"].values()):
            # Create a blank summary.
        self.env["PatchManagement_summary_result"] = {
            "summary_text": "The following changes were made to the Patch Management:",
            "report_fields": [
                "Patch Server", "Software title", "Software title version", "Package", "Version", "Patch policy",
                "Package Uploaded", "Patch policy created or modified"
            ],
            "data": {
                "Patch Server": "",
                "Software title": "",
                "Software title version": "",
                "Package": "",
                "Version": "",
                "Patch policy": "",
                "Package Uploaded": "",
                "Patch policy created or modified": ""
            }
        }
        data = self.env["PatchManagement_summary_result"]["data"]
        for entry in report:
            data[entry] = report[entry] if report[entry] else ""

    def main(self):
        jss_importer_summary_result = self.env.get("jss_importer_summary_result")
        jamf_id = self.env.get("softwaretitleconfig_id")
        patch_server_name = self.env.get("patch_server")
        # Checking if the Patch Server exists
        self.output("Looking for the PatchServer {0}".format(patch_server_name))
        url = "{0}/JSSResource/patchinternalsources/name/{1}".format(self.env["JSS_URL"], patch_server_name)
        patch_server = self.jamf_requests(url, "GET")
        if patch_server.status_code == 404:
            url = "{0}/JSSResource/patchexternalsources/name/{1}".format(self.env["JSS_URL"], patch_server_name)
            patch_server = self.jamf_requests(url, "GET")
            if patch_server.status_code == 404:
                raise Exception('The patch server "{0}" provided does not exists on {1}'.format(patch_server_name, self.env["JSS_URL"]))
        self.output("The PatchServer {0} has been found on {1}".format(patch_server_name, self.env["JSS_URL"]))

        # Checking if the Software Title exists
        self.output('Looking for the software title "{0}"'.format(jamf_id))
        url = "{0}/JSSResource/patchsoftwaretitles/id/{1}".format(self.env["JSS_URL"], jamf_id)
        software_title = self.jamf_requests(url, "GET")
        if software_title.status_code == 404:
            raise Exception('The software title "{0}" provided does not exists on {1}'.format(jamf_id, self.env["JSS_URL"]))
        self.output('The software title "{0}" has been found'.format(jamf_id))

        # Checking if the Software Title comes from the Patch Server
        softwaretitle_name = self.xml_lookup(software_title.text, "name")[0]
        source_id = self.xml_lookup(software_title.text, "source_id")[0]
        patch_server_id = self.xml_lookup(patch_server.text, "id")[0]
        if source_id != patch_server_id:
            raise Exception("The software Title provided does not come from the patch server provided")
        # Checking if the package can be added to the software title
        patch_versions = self.xml_lookup(software_title.text, "versions/version/software_version")
        pkg_version = jss_importer_summary_result["data"]["Version"]
        version = ""
        go_ahead = False
        for entry in patch_versions:
            if pkg_version == entry:
                self.output("The package's version has been found on the software title")
                version = entry
                go_ahead = True
            elif pkg_version.startswith(entry):
                self.output("The package's version can be used for the software title for version {0}".format(entry))
                version = entry
                go_ahead = True
        if not go_ahead:
            raise Exception("The package's version has not been found on the software title")
        # Adding the package to the software title definition
        name = jss_importer_summary_result["data"]["Name"]
        pkg_name = jss_importer_summary_result["data"]["Package"]
        pkg_id = str(self.get_pkg_id(pkg_name))
        name_id = self.xml_lookup(software_title.text, "name_id")[0]
        dict_software_title = {
            "NAME": name,
            "NAME_ID": name_id,
            "SOURCE": source_id,
            "VERSION": version,
            "PACKAGE_ID": pkg_id,
            "PACKAGE_NAME": pkg_name
        }
        if pkg_name in self.xml_lookup(software_title.text, "versions/version/package/name") and pkg_id in self.xml_lookup(software_title.text, "versions/version/package/id"):
            self.output("The package's version is already part of the software title's definition")
        else:
            self.output("Adding package's version to the software title's definition")
            cu_softwaretitle = self.update_softwaretitle(dict_software_title, jamf_id)
            if cu_softwaretitle.status_code != 201:
                raise Exception('An error occured while updating the software title "{0}"'.format(jamf_id))
        # Checking if a patch policy needs to be created for this software title
        self.output('Looking for patch policies for software title "{0}"'.format(jamf_id))
        url = "{0}/JSSResource/patchpolicies/softwaretitleconfig/id/{1}".format(self.env["JSS_URL"], jamf_id)
        software_title_policies = self.jamf_requests(url,"GET")
        expected_patch_policy_name = "{0} - {1}".format(jss_importer_summary_result["data"]["Name"], jss_importer_summary_result["data"]["Version"])
        patch_policy_ids = self.xml_lookup(software_title_policies.text, "patch_policy/id")
        patch_policy_number = len(patch_policy_ids)
        dict_patch_policy = {
            "NAME": name,
            "JAMF_ID": jamf_id,
            "VERSION": version,
        }
        need_patchpolicy = True
        if software_title_policies.status_code == 200 and patch_policy_number == 0:
            self.output('A patch policy for the software tile "{0}" needs to be created'.format(jamf_id))
        else:
            for entry in patch_policy_ids:
                url = "{0}/JSSResource/patchpolicies/id/{1}".format(self.env["JSS_URL"], entry)
                patchpolicy = self.jamf_requests(url, "GET")
                target_version = self.xml_lookup(patchpolicy.text,"general/target_version")[0]
                patchpolicy_name = self.xml_lookup(patchpolicy.text,"general/name")[0]
                if version == target_version and patchpolicy_name == expected_patch_policy_name:
                    self.output('The patch policy "{0}" already exists for the software title "{1}"'.format(expected_patch_policy_name,jamf_id))
                    need_patchpolicy = False
                elif version == target_version:
                    self.output('A patch policy already exists for the "{0}" version with a different name'.format(target_version))
                    need_patchpolicy = False
        # Creating a patch policy for this software title
        if need_patchpolicy:
            self.output('No patch policy found for the software tile "{0}"'.format(jamf_id))
            patchpolicy = self.create_update_patchpolicy(dict_patch_policy)
            if patchpolicy.status_code == 201:
                self.output('The patch policy "{0}" has been created for the software title "{1}"'.format(expected_patch_policy_name, jamf_id))
                patchpolicy_created = True
            else:
                raise Exception('An error occurred while creating the patch policy')
        else:
            self.output("No patch policy had been created")
            patchpolicy_created = False
        data_report = {
            "Patch policy": expected_patch_policy_name,
            "Software title version": version,
            "Patch Server": patch_server_name,
            "Software title": name,
            "Version": pkg_version,
            "Package": pkg_name,
            "Package Uploaded": jss_importer_summary_result["data"]["Package_Uploaded"],
            "Patch policy created or modified": patchpolicy_created,
        }
        self.summarize(data_report)


if __name__ == "__main__":
    processor = PatchManagement()
    processor.execute_shell()
