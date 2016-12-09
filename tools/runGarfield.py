#!/usr/bin/python

from Aion.data_generation.stimulation.Garfield import Garfield
from Aion.utils.data import *     # Needed for accessing configuration files
from Aion.utils.graphics import * # Needed for pretty printing
import introspy # Used for analysis of 

import os, sys, glob, shutil, argparse, subprocess

def defineArguments():
    parser = argparse.ArgumentParser(prog="runGarfield.py", description="A tool to drive \"Aion\"'s Garfield fuzzer.")
    parser.add_argument("-s", "--sdkdir", help="The path to Android SDK", required=True)
    parser.add_argument("-d", "--indir", help="The directory containing the APK's to analyze", required=True)
    parser.add_argument("-t", "--analysistime", help="How long to run monkeyrunner (in seconds)", required=False, default=60)
    parser.add_argument("-o", "--outdir", help="The directory to save the analyzed APK behavior", required=False, default="./garfield_out")
    return parser

def main():
    try:
        argumentParser = defineArguments()
        arguments = argumentParser.parse_args()
        prettyPrint("Welcome to the \"Garfield\", the fuzz tester")

        # Some sanity checks
        if not os.path.exists(arguments.sdkdir):
             prettyPrint("Unable to locate the Android SDK. Exiting", "error")
             return False

        monkeyRunnerPath = arguments.sdkdir + "/tools/monkeyrunner"
        adbPath = arguments.sdkdir + "/platform-tools/adb"

        # All set, let's do what we're here for
        allAPKs = glob.glob("%s/*.apk" % arguments.indir)
        if len(allAPKs) < 1:
            prettyPrint("Could not find any APK's under \"%s\". Exiting" % arguments.indir, "error")
            return False

        prettyPrint("Successfully retrieved %s APK's from \"%s\"" % (len(allAPKs), arguments.indir))
        for path in allAPKs:
            # 1. Statically analyze the APK using androguard
            currentAPK = Garfield(path)
            if verboseON():
                prettyPrint("Analyzing APK: \"%s\"" % path, "debug")

            if not currentAPK.analyzeAPK():
                prettyPrint("Analysis of APK \"%s\" failed. Skipping" % path, "warning")
                continue
            # 2. Generate Monkeyrunner script
            if not currentAPK.generateRunnerScript(int(arguments.analysistime)):
                prettyPrint("Generation of \"Monkeyrunner\" script failed. Skipping", "warning")
                continue
            # 3. Run the generated script
            args = [monkeyRunnerPath, currentAPK.runnerScript]
            subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]
            # 4. Download the introspy.db
            #x = raw_input("continue? ")
            args = [adbPath, "pull", "/data/data/%s/databases/introspy.db" % str(currentAPK.APK.package)]
            subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE).communicate()[0]
            # 5. Analyze the downloaded database
            # 5.a. Check that the database exists and is not empty
            if os.path.exists("introspy.db"):
                if int(os.path.getsize("introspy.db")) == 0:
                    prettyPrint("The database generated by Introspy is empty. Skipping", "warning")
                    continue
            # Last line of defense
            try:
                db = introspy.DBAnalyzer("introspy.db", "foobar")
            except sqlite3.OperationalError as sql:
                prettyPrint("The database generated by Introspy is probably empty. Skipping", "warning")

            trace = db.get_traced_calls_as_JSON()
            # 6. Write trace to [outdir]
            if not os.path.exists(arguments.outdir):
                if verboseON():
                    prettyPrint("Directory \"%s\" does not exit. Creating one" % arguments.outdir, "debug")
                os.mkdir(arguments.outdir)
 
            traceFile = open("%s/%s.json" % (arguments.outdir, currentAPK.APK.package), "w")
            traceFile.write(trace)
            traceFile.close()
 
            html = introspy.HTMLReportGenerator(db, "foobar")
            html.write_report_to_directory("%s/%s" % (arguments.outdir, currentAPK.APK.package))
            
            prettyPrint("Done analyzing \"%s\"" % currentAPK.APK.package)

            
    except Exception as e:
        prettyPrintError(e)
        return False
    
    prettyPrint("Good day to you ^_^")
    return True

if __name__ == "__main__":
    main() 