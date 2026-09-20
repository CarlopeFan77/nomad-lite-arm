#!/bin/bash

echo "================================="
echo "       NOMAD Lite ARM"
echo "       System Information"
echo "================================="
echo

echo "Architecture:"
uname -m
echo

echo "Operating System:"
grep PRETTY_NAME /etc/os-release | cut -d '"' -f2
echo

echo "Kernel:"
uname -r
echo

echo "CPU threads:"
nproc
echo

echo "Memory:"
free -h
echo

echo "Storage:"
df -h /
echo

echo "================================="
