'''
Worker node, which calculates the cyclomatic complexity of a set of files given to it.
The worker will follow the work-stealing pattern, i..e requesting work from the manager.
'''

import requests
from flask_restful import Resource, Api, reqparse
from flask import Flask, request

import Utilities as utils
from radon.cli.harvest import CCHarvester

MANAGER_URL = "http://127.0.0.1:5000"
WORKER_REGISTRATION_URL = "http://127.0.0.1:5000/register_worker"
WORKER_ID = ""
ROOT_DIR = "WorkerDir"


class Worker(object):

    def __init__(self):
        while True:
            try:
                self.worker_id = register_worker()
                break
            except:
                # probably just waiting for the manager to finish starting up
                pass
        self.root_dir = ROOT_DIR + WORKER_ID
        self.repo = utils.get_git_repository(self.root_dir)
        self.running = True

        
    # Fetches work from the manager by polling.
    def fetch_work(self):
        while(self.running):
            # request work
            work = requests.get(MANAGER_URL, json={"worker_id": WORKER_ID})
            if work.json()['running'] is "False":
                self.running = False
                break
            if work is not None:
                commit = work.json()['commit']
                if commit == -1:
                    # manager instructed us to terminate
                    self.running = False
                    break
                elif commit == -2:
                    # we are waiting for all workers to join
                    pass
                else:
                    self.do_work(commit)

        utils.print_to_console("Worker" + WORKER_ID, 'The manager instructed us to terminate')

    # Calculates the average Cyclomatic Complexity of the given commit.    
    def do_work(self, commit):
        total_complexity = 0
        num_files_assessed = 0
        
        # get the files in this commit, and calculate the complexity of each. 
        file_names = utils.get_files_at_commit(commit, self.root_dir)
        for file_name in file_names:
            total_complexity += self.calculate_file_complexity(file_name)
            num_files_assessed += 1
        
        # calculate the average of all the files
        average_complexity = utils.calculate_average(total_complexity, num_files_assessed)

        response = requests.post(MANAGER_URL, json={'average_complexity': average_complexity})

    # Calculates the cyclomatic complexity of the given file
    def calculate_file_complexity(self, file_name):
        utils.print_to_console('Worker' + WORKER_ID, 'Calculating complexity for file {0}'.format(file_name))
        file_complexity = 0
        file = open(file_name, 'r')
        results = CCHarvester(file_name, utils.get_CCHarvester_config()).gobble(file)

        for result in results:
            file_complexity += int(result.complexity)

        utils.print_to_console('Worker' + WORKER_ID, "Total complexity of {0}: {1}".format(file_name, str(file_complexity)))
        return file_complexity

# Sends a registration request to the Manager, obtaining a unique ID for this worker.
def register_worker():
    global WORKER_ID
    response = requests.get(WORKER_REGISTRATION_URL, json={'registration_request': True})
    worker_id = response.json()['worker_id']
    if worker_id is not None:
        WORKER_ID = str(worker_id)
    return str(worker_id)


if __name__ == '__main__':
    worker = Worker()
    worker.fetch_work()
