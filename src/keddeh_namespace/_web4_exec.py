"""Apply actual Linux process file bounds before executing an owner package."""
import os
import resource
import sys


def main():
    if len(sys.argv)<2:raise SystemExit('an executable argv is required')
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024*1024,64*1024*1024))
    os.execvpe(sys.argv[1],sys.argv[1:],os.environ)

if __name__=='__main__':main()
