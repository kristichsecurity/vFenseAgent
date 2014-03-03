import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from core import MainCore

if __name__ == "__main__":

    main_core = MainCore("agent")
    main_core.run()
