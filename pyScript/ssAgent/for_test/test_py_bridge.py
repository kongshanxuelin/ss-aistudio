import os
import sys
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
print(base_dir)

sys.path.append(base_dir)
import PyBridge

if __name__ == "__main__":
    print("in test_py_bridge")
    print(help(PyBridge))
    # PyBridge.StartProcess("upload file", 10, 1, 1)
    