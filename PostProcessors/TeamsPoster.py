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

from __future__ import absolute_import
from __future__ import print_function
from autopkglib import Processor, ProcessorError

import requests

__all__ = ["TeamsPoster"]

class TeamsPoster(Processor):
    description = ("Posts to Microsoft Teams via webhook based on processor given summary result (JSSImporter, url_downloader, pkg_copier, etc...). "
                    "Takes the work from Graham Pugh with the slacker post processor"
                    "http://grahampugh.github.io/2017/12/22/slack-for-autopkg-jssimporter.html"
                    "https://medium.com/nintexperts/sending-microsoft-teams-messages-using-webhooks-and-the-nintex-workflow-cloud-6654c5fa97e6")
    input_variables = {
        "Processor_name":{
            "required": True,
            "description": ("Name of the processor (case sensitive) for which the summary should be post to Microsoft Teams")
        },
        "trigger_key":{
            "required": False,
            "description": ("The key from the summary that will trigger the post, the key value must be a boolean. If there isn't any key, the summary will always be posted")
        },
        "webhook_url": {
            "required": True,
            "description": ("Microsoft Teams webhook.")
        }
    }
    output_variables = {
        "posted_to_Teams": {
            "description": "Summarize post to Microsoft Teams (boolean)"
        },
        "posted_summary": {
            "description": "Which summary has been posted"
        },
    }

    __doc__ = description

    def payload_maker(self, summary_result):
        payload = {
            "summary": summary_result["summary_text"],
            "sections": []
        }
        facts_dict = {
            "facts": []
        }
        activityTitle = {
            "activityTitle": '<b>New item added to Jamf Pro <a href="{0}">{0}</a></b>'.format(self.env.get("JSS_URL"))
        }
        payload["sections"].append(activityTitle)

        for entry in summary_result["data"]:
            # print "{0} : {1}".format(entry, summary_result["data"][entry])
            key_summary={
                "name": entry,
                "value": summary_result["data"][entry]
            }
            facts_dict["facts"].append(key_summary)
        payload["sections"].append(facts_dict)
        return payload

    def main(self):
        processor_summary_result = self.env.get("{0}_summary_result".format(self.env.get("Processor_name")))
        trigger_key = self.env.get("trigger_key")
        webhook_url = self.env.get("webhook_url")
        trigger = True

        if trigger_key in processor_summary_result["data"].keys():
            print("Trigger key: ", trigger_key)
            # trigger = processor_summary_result["data"][trigger_key]
            trigger = False if not processor_summary_result["data"][trigger_key] else True

        payload = self.payload_maker(processor_summary_result)

        if trigger:
            response = requests.post(webhook_url, json=payload)
            if response.status_code != 200:
                raise Exception(
                                'Request to Microsoft Teams returned an error %s, the response is:\n%s'
                                % (response.status_code, response.text)
                                )
            self.env["posted_to_Teams"] = True
            self.env["posted_summary"] = "{0}_summary_result".format(self.env.get("Processor_name"))
        else:
            self.env["posted_to_Teams"] = False
            self.env["posted_summary"] = ""




if __name__ == "__main__":
    processor = TeamsPoster()
    processor.execute_shell()