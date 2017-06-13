#!/usr/bin/python

from Aion.utils.data import *
from Aion.utils.graphics import *

from androguard.session import Session
import numpy

import os, json, threading

def returnEmptyFeatures():
    """
    A dummy function used by timers to return empty feature vectors (lists)
    """
    prettyPrint("Analysis timeout. Returning empty feature vector", "warning")
    return []

def extractAndroguardFeatures(apkPath):
    """Extracts static numerical features from APK using Androguard"""
    try:
        features = []
        if os.path.exists(apkPath.replace(".apk",".static")):
            prettyPrint("Found a pre-computed static features file")
            try:
                content = open(apkPath.replace(".apk", ".static")).read()
                features = [float(f) for f in content[1:-1].split(',')]
                return features

            except Exception as e:
                prettyPrintError(e)
                prettyPrint("Could not extract features from \".static\" file. Continuing as usual", "warning")
        if verboseON():
            prettyPrint("Starting analysis on \"%s\"" % apkPath, "debug")
        analysisSession = Session()
        if not os.path.exists(apkPath):
            prettyPrint("Could not find the APK file \"%s\"" % apkPath, "warning")
            return []
        # 1. Analyze APK and retrieve its components
        #t = threading.Timer(300.0, returnEmptyFeatures) # Guarantees not being stuck on analyzing an APK
        #t.start()
        analysisSession.add(apkPath, open(apkPath).read())
        if type(analysisSession.analyzed_apk.values()) == list:
            apk = analysisSession.analyzed_apk.values()[0][0]
        else:
            apk = analysisSession.analyzed_apk.values()[0]
        dex = analysisSession.analyzed_dex.values()[0][0]
        vm = analysisSession.analyzed_dex.values()[0][1]
        # 2. Add features to the features vector
        # 2.a. The APK-related features
        minSDKVersion = 0.0 if not apk.get_min_sdk_version() else float(apk.get_min_sdk_version())
        maxSDKVersion = 0.0 if not apk.get_max_sdk_version() else float(apk.get_max_sdk_version())
        features.append(minSDKVersion)
        features.append(maxSDKVersion)
        features.append(float(len(apk.get_activities()))) # No. of activities
        features.append(float(len(apk.get_services()))) # No. of services
        features.append(float(len(apk.get_receivers()))) # No. of broadcast receivers
        features.append(float(len(apk.get_providers()))) # No. of providers
        aospPermissions = float(len(apk.get_requested_aosp_permissions())) # AOSP permissions
        thirdPartyPermissions = float(len(apk.get_requested_third_party_permissions())) # Third-party permissions
        totalPermissions = aospPermissions + thirdPartyPermissions
        dangerousPermissions = 0.0
        for p in apk.get_details_permissions():
            if apk.get_details_permissions()[p][0] == "dangerous":
                dangerousPermissions += 1.0 
        features.append(totalPermissions) # No. of permissions
        if totalPermissions > 0:
            features.append(aospPermissions/totalPermissions) # AOSP permissions : Total permissions
            features.append(thirdPartyPermissions/totalPermissions) # Third-party permissions : Total permissions
            features.append(dangerousPermissions/totalPermissions) # Dangerous permissions : Total permissions
        else:
            features.append(0)
            features.append(0)
            features.append(0)
        # 2.b. The DEX-related features
        features.append(float(len(dex.get_classes()))) # Total number of classes
        features.append(float(len(dex.get_strings()))) # Total number of strings

    except Exception as e:
        prettyPrintError(e)
        return []
    
    return features     


def extractIntrospyFeatures(apkJSONPath):
    """Extracts dynamic features from a JSON-based trace generated by Introspy"""
    try:
        features = []
        if not os.path.exists(apkJSONPath):
            prettyPrint("Could not find the JSON file \"%s\"" % apkJSONPath, "warning")
        else:
            apkJSON = json.loads(open(apkJSONPath).read())
            cryptoCalls, sslCalls, hashCalls = 0.0, 0.0, 0.0 # Crypto group
            fsCalls, prefCalls, uriCalls = 0.0, 0.0, 0.0 # Storage group
            ipcCalls = 0.0 # Ipc group
            webviewCalls = 0.0  # Misc group
            accountManagerCalls, activityCalls, downloadManagerCalls = 0.0, 0.0, 0.0
            contentResolverCalls, contextWrapperCalls, packageInstallerCalls = 0.0, 0.0, 0.0
            sqliteCalls, cameraCalls, displayManagerCalls, locationCalls = 0.0, 0.0, 0.0, 0.0
            audioRecordCalls, mediaRecorderCalls, networkCalls, wifiManagerCalls = 0.0, 0.0, 0.0, 0.0
            powerManagerCalls, smsManagerCalls, toastCalls, classCalls = 0.0, 0.0, 0.0, 0.0
            httpCookieCalls, urlCalls = 0.0, 0.0
            for call in apkJSON["calls"]:
                group, subgroup = call["group"], call["subgroup"]
                if group == "Crypto":
                    cryptoCalls = cryptoCalls + 1 if subgroup == "General crypto" else cryptoCalls
                    hashCalls = hashCalls + 1 if subgroup == "Hash" else hashCalls
                    sslCalls = sslCalls + 1 if subgroup == "Ssl" else sslCalls
                elif group == "Storage":
                    fsCalls = storageCalls + 1 if call["group"] == "Fs" else fsCalls
                    prefCalls = prefCalls + 1 if call["group"] == "Pref" else prefCalls
                    uriCalls = uriCalls + 1 if call["group"] == "Uri" else uriCalls
                elif group == "Ipc":
                    ipcCalls = ipcCalls + 1 if call["group"] == "Ipc" else ipcCalls
                elif group == "Misc":
                    webviewCalls = webviewCalls + 1 if call["group"] == "Webview" else webviewCalls
                elif group.lower().find("custom") != -1:
                    # Handle custom hooks
                    # android.accounts.AccountManager
                    if call["clazz"] == "android.accounts.AccountManager":
                        accountManagerCalls += 1
                    # android.app.Activity
                    elif call["clazz"] == "android.app.Activity":
                        activityCalls += 1
                    # android.app.DownloadManager
                    elif call["clazz"] == "android.app.DownloadManager":
                        downloadManagerCalls += 1 
                    # android.content.ContentResolver
                    elif call["clazz"] == "android.content.ContentResolver":
                        contentResolverCalls += 1
                    # android.content.ContextWrapper
                    elif call["clazz"] == "android.content.ContextWrapper":
                        contextWrapperCalls += 1
                    # android.content.pm.PackageInstaller
                    elif call["clazz"] == "android.content.pm.PackageInstaller":
                        packageInstallerCalls += 1
                    # android.database.sqlite.SQLiteDatabase
                    elif call["clazz"] == "android.database.sqlite.SQLiteDatabase":
                        sqliteCalls += 1
                    # android.hardware.Camera
                    elif call["clazz"] == "android.hardware.Camera":
                        cameraCalls += 1
                    # android.hardware.display.DisplayManager
                    elif call["clazz"] ==  "android.hardware.display.DisplayManager":
                        displayManagerCalls += 1
                    # android.location.Location
                    elif call["clazz"] == "android.location.Location":
                        locationCalls += 1
                    # android.media.AudioRecord
                    elif call["clazz"] == "android.media.AudioRecord":
                        audioRecordCalls += 1
                    # android.media.MediaRecorder
                    elif call["clazz"] == "android.media.MediaRecorder":
                        mediaRecorderCalls += 1
                    # android.net.Network
                    elif call["clazz"] == "android.net.Network":
                        networkCalls += 1
                    # android.net.wifi.WifiManager
                    elif call["clazz"] == "android.net.wifi.WifiManager":
                        wifiManagerCalls += 1
                    # android.os.PowerManager
                    elif call["clazz"] == "android.os.PowerManager":
                        powerManagerCalls += 1
                    # android.telephony.SmsManager
                    elif call["clazz"] == "android.telephony.SmsManager":
                        smsManagerCalls += 1
                    # android.widget.Toast
                    elif call["clazz"] == "android.widget.Toast":
                        toastCalls += 1
                    # java.lang.class
                    elif call["clazz"] == "java.lang.class":
                        classCalls += 1
                    # java.net.HttpCookie
                    elif call["clazz"] == "java.net.HttpCookie":
                        httpCookieCalls += 1
                    # java.net.URL
                    elif call["clazz"] == "java.net.URL":
                        urlCalls += 1

            features.append(cryptoCalls)
            features.append(sslCalls)
            features.append(hashCalls)
            features.append(fsCalls)
            features.append(prefCalls)
            features.append(uriCalls)
            features.append(ipcCalls)
            features.append(webviewCalls)
            features.append(accountManagerCalls)
            features.append(activityCalls)
            features.append(downloadManagerCalls)
            features.append(contentResolverCalls)
            features.append(contextWrapperCalls)
            features.append(packageInstallerCalls)
            features.append(sqliteCalls)
            features.append(cameraCalls)
            features.append(displayManagerCalls)
            features.append(locationCalls)
            features.append(audioRecordCalls)
            features.append(mediaRecorderCalls)
            features.append(networkCalls)
            features.append(wifiManagerCalls)
            features.append(powerManagerCalls)
            features.append(smsManagerCalls)
            features.append(toastCalls)
            features.append(classCalls)
            features.append(httpCookieCalls)
            features.append(urlCalls)

    except Exception as e:
        prettyPrintError(e)
        return []

    return features


