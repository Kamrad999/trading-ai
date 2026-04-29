@echo off
cd C:\Users\kamra\CascadeProjects\TRADING-AI-REFACTORED
git add -A
git commit -m "fix(ci): stabilize pipeline, isolate execution tests, safe install step"
git push origin main
echo Done
