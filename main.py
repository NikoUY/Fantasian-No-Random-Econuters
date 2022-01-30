# py3
# requirements:
#   UnityPy
#       pip install UnityPy
#   pythonnet 3+
#       pip install git+https://github.com/pythonnet/pythonnet/
#   TypeTreeGenerator
#       https://github.com/K0lb3/TypeTreeGenerator
#       requires .NET 5.0 SDK
#           https://dotnet.microsoft.com/download/dotnet/5.0

import UnityPy

import os, math, shutil, sys, pprint, string
from typing import Dict
from pathlib import Path

# C# Stuff
from clr_loader import get_coreclr
from pythonnet import set_runtime

ROOT = os.path.dirname(os.path.realpath(__file__))
TYPETREE_GENERATOR_PATH = os.path.join(ROOT, "TypeTreeGenerator")

App_Path = "/Applications/FANTASIAN.app"
Patched_App_Dest = str(Path.home()) + "/FANTASIAN NO RANDOM ENCOUNTERES.app"

def patch_data_resource(file_path: string, g: "Generator"):
    env = UnityPy.load(file_path)

    # Search, get info and modify files
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            d = obj.read()
            if d.name in ["EncounterInfoTable", "PlayerParameterInfoTable_PC001", "PlayerParameterInfoTable_PC002",
                            "PlayerParameterInfoTable_PC003", "PlayerParameterInfoTable_PC004", "PlayerParameterInfoTable_PC005",
                            "PlayerParameterInfoTable_PC006", "PlayerParameterInfoTable_PC007", "PlayerParameterInfoTable_PC008",
                            "PassiveProgramInfoTable"]:
                script = d.m_Script.read()
                trees = generate_tree(g, script.m_AssemblyName, script.m_ClassName, script.m_Namespace)
                tree = obj.read_typetree(trees[script.m_ClassName])
                if d.name == "EncounterInfoTable":
                    # Disable random encounters, some events may look like random encounters in game but they are not.
                    for item_index, item in enumerate(tree["items"]):
                        for group_index, _ in enumerate(item["groups"]):
                            tree["items"][item_index]["groups"][group_index]["rate"] = 0
                elif "PlayerParameterInfoTable" in d.name:
                    # QOL: Enable faster movement speed on all the characters

                    # The game will ignore the skills after an empty string so we use one of the empty strings instead of appending
                    # it to the end.
                    for index, item in enumerate(tree["items"][0]["passiveIds"]):
                        if item == "":
                            tree["items"][0]["passiveIds"][index] = "BT_FieldMoveSpeedUp"
                            break
                elif d.name == "PassiveProgramInfoTable":
                    # Disable EXP Jewels
                    count = 0
                    for index, item in enumerate(tree["items"]):
                        if "ExpUp" in item["id"]:
                            tree["items"][index]["parameters"][0]["value"] = "1.0"
                            if count == 1:
                                break
                            else:
                                count +=1

                obj.save_typetree(tree, trees[script.m_ClassName])

    with open(file_path, "wb") as f:
        f.write(env.file.save())

def create_generator(dll_folder: str):
    """Loads TypeTreeGenerator library and returns an instance of the Generator class."""
    # Temporarily add the typetree generator dir to paths,
    # so that pythonnet can find its files
    sys.path.append(TYPETREE_GENERATOR_PATH)

    import clr
    clr.AddReference("TypeTreeGenerator")

     # import Generator class from the loaded library
    from Generator import Generator

    g = Generator()
    g.loadFolder(dll_folder)

    return g

def generate_tree(g: "Generator", assembly: str, class_name: str, namespace: str, unity_version=[2020, 3, 13, 1],) -> Dict[str, Dict]:
    """Generates the typetree structure / nodes for the specified class."""
    
    # C# System.Array
    from System import Array

    unity_version_cs = Array[int](unity_version)

    # fetch all type definitions
    def_iter = g.getTypeDefs(assembly, class_name, namespace)

    # create the nodes
    trees = {}

    for d in def_iter:
        nodes = g.convertToTypeTreeNodes(d, unity_version_cs)
        trees[d.Name] = [
            {
                "level" : node.m_Level,
                "type" : node.m_Type,
                "name" : node.m_Name,
                "meta_flag" : node.m_MetaFlag,
            }
            for node in nodes
        ]

    return trees

if __name__ == "__main__":
    #Set the correct runtime for pythonnet
    rt = get_coreclr(os.path.join(TYPETREE_GENERATOR_PATH, "TypeTreeGenerator.runtimeconfig.json"))
    set_runtime(rt)

    if os.path.exists(Patched_App_Dest):
        print("Found a patched version of the game, removing it to create a new one")
        shutil.rmtree(Patched_App_Dest)

    print("Making a copy of the game at {}".format(Patched_App_Dest))
    shutil.copytree(App_Path, Patched_App_Dest)

    print("Creating Generator")
    g = create_generator(os.path.join(ROOT, "DummyDll"))

    file_path = Patched_App_Dest + "/Contents/Resources/Data/data.unity3d"
    print("Patching {}".format(file_path))
    patch_data_resource(file_path, g)

    print("Patching Lua Scripts")
    #patch_script()

    print("Done!, the patched version of the game is located at {}".format(Patched_App_Dest))
