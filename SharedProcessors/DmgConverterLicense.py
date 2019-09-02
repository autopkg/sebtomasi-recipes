#!/usr/bin/env python

from __future__ import absolute_import, print_function

import re
import shutil
import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["DmgConverterLicense"]

class DmgConverterLicense(Processor):
    '''Substitute a character from a given string and return the parsed string'''
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "string",
        },
    }

    output_variables = {
        "pathname":{
            "required": True,
            "description": "Path to the converted file.",
        },
    }

    description = __doc__

    def main(self):
        dmg = self.env["dmg_path"]
        new_dmg = re.sub(r".dmg","",dmg)+"_Converted"
        #####Remove a license agreement from the dmg
        subprocess.check_call(["/usr/bin/hdiutil","convert","-quiet",dmg,"-format","UDTO","-o",new_dmg ])
        print(new_dmg+".cdr")
        shutil.move(new_dmg+".cdr",new_dmg+".dmg")
        self.env["pathname"] = new_dmg+".dmg"

if __name__ == "__main__":
    processor = DmgConverterLicense()
    processor.execute_shell()
