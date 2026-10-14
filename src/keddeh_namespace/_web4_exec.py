"""Apply actual Linux process file bounds before executing an owner package."""
import os
import resource
import sys


def main():
    if len(sys.argv)<2:raise SystemExit('an executable argv is required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    budget=int(os.environ.get('KEDDEH_FILE_BUDGET',64*1024*1024))
    if budget not in (64*1024*1024,256*1024*1024):raise ValueError('unsupported file budget')
    resource.setrlimit(resource.RLIMIT_FSIZE,(budget,budget))
    os.execvpe(sys.argv[1],sys.argv[1:],os.environ)

if __name__=='__main__':main()
