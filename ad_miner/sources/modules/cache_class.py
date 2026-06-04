import os
import pickle
import csv

from ad_miner.sources.modules.cache_security import load_cache_entry


class Cache:
    def __init__(self, arguments):
        self.cache_prefix = "./cache_neo4j/" + arguments.cache_prefix
        self.csv_path = "render_%s/csv/" % arguments.cache_prefix
        try:
            os.mkdir("cache_neo4j")
        except FileExistsError:
            pass

    # todo add checksum
    def createCacheEntry(self, filename, data):
        # if (len(data)):
        full_name = self.cache_prefix + "_" + filename
        with open(full_name, "wb") as f:
            pickle.dump(data, f)

    # todo add checksum
    def retrieveCacheEntry(self, filename):

        full_name = self.cache_prefix + "_" + filename
        if os.path.exists(full_name):
            with open(full_name, "rb") as f:
                return load_cache_entry(f)
        return False

    def createCsvFileFromRequest(self, filename, data, object_type):
        try:
            if data and len(data):
                with open(self.csv_path + filename + ".csv", "w") as f:
                    if object_type is dict:
                        csv_columns = data[0].keys()
                        writer = csv.DictWriter(f, fieldnames=csv_columns)
                        writer.writeheader()
                    elif object_type is list:
                        writer = csv.writer(f, delimiter=",")
                    else:
                        writer = csv.writer(f, delimiter=",")
                        data = []
                    # for elem in data:
                    # 	writer.writerow(elem)
                    writer.writerows(data)
        except IOError as e:
            print("I/O error (cache might be corrupted)")
            print(e)
            exit(0)
