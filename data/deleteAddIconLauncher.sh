#!/bin/bash
myfile="application:\/\/"$1".desktop"
list=`gsettings get com.canonical.Unity.Launcher favorites`
removedlist=`echo $list | sed s/"'${myfile}', "//`
gsettings set com.canonical.Unity.Launcher favorites "$removedlist"
addlist=`echo $list | sed s/]/", '${myfile}']"/` 
sleep 1
gsettings set com.canonical.Unity.Launcher favorites "$addlist"