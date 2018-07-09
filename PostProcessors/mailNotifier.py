#!/usr/bin/python
# -*- coding: utf-8 -*-

from autopkglib import Processor, ProcessorError

from email.mime.text import MIMEText
import smtplib

__all__ = ["mailNotifier"]

class mailNotifier(Processor):
    description = ("Sends an email based on output of a JSSImporter run. "
                    "Widely inspired by Graham R Pugh's work"
                    "http://grahampugh.github.io/2017/12/22/slack-for-autopkg-jssimporter.html")
    input_variables = {
        "JSS_URL": {
            "required": False,
            "description": ("JSS_URL.")
        },
        "policy_category": {
            "required": False,
            "description": ("Policy Category.")
        },
        "category": {
            "required": False,
            "description": ("Package Category.")
        },
        "prod_name": {
            "required": False,
            "description": ("PROD_NAME")
        },
        "jss_changed_objects": {
            "required": False,
            "description": ("Dictionary of added or changed values.")
        },
        "jss_importer_summary_result": {
            "required": False,
            "description": ("Description of interesting results.")
        },
        "smtp_settings": {
            "required": False,
            "description": ("SMTP server settings")
        },
        "mail_from": {
            "required": False,
            "description": ("Sender email address")
        },
        "mail_to": {
            "required": False,
            "description": ("Recever email address")
        }
    }
    output_variables = {
    }

    __doc__ = description


    def mailer(self,subject, mailFrom, mailTo, mailContent):
        server = smtplib.SMTP('mail.ctip.ch', 25)
        msg = MIMEText(mailContent)
        msg['Subject'] = u"{0}".format(subject)
        msg['From'] = mailFrom
        msg['To'] = mailTo
        server.sendmail(msg["from"], msg['To'], msg.as_string())
        server.quit()


    def main(self):
        JSS_URL = self.env.get("JSS_URL")
        policy_category = self.env.get("policy_category")
        category = self.env.get("category")
        prod_name = self.env.get("prod_name")
        jss_changed_objects = self.env.get("jss_changed_objects")
        jss_importer_summary_result = self.env.get("jss_importer_summary_result")
        mail_to = self.env.get("mail_to")
        mail_from = self.env.get("mail_from")

        if jss_changed_objects:
            jss_policy_name = "%s" % jss_importer_summary_result["data"]["Policy"]
            jss_policy_version = "%s" % jss_importer_summary_result["data"]["Version"]
            jss_uploaded_package = "%s" % jss_importer_summary_result["data"]["Package"]
            print "JSS address: %s" % JSS_URL
            print "Title: %s" % prod_name
            print "Policy: %s" % jss_policy_name
            print "Version: %s" % jss_policy_version
            print "Category: %s" % category
            print "Policy Category: %s" % policy_category
            print "Package: %s" % jss_uploaded_package

            if jss_uploaded_package:
                subject = "New uploaded package for {0} is available".format(prod_name)
                message = '''A new version of {0} has been uploaded
                Jamf Pro Server : {1}
                Package : {2}
                Version : {3}
                Policy : {4}
                '''.format(JSS_URL, prod_name,jss_uploaded_package,jss_policy_version,jss_policy_name)
                self.mailer(subject,mail_from,mail_to,message)


if __name__ == "__main__":
    processor = mailNotifier()
    processor.execute_shell()