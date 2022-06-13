import lzma
import os
import shutil
from zipfile import ZipFile, ZIP_DEFLATED


def file_len(file):
    file_name, extension = os.path.splitext(file)
    if extension == ".temp":
        file_name, extension = os.path.splitext(file_name)
    if extension == ".xz":
        with lzma.open(file, mode='rt') as f:
            for i, l in enumerate(f):
                pass
        return i + 1
    elif extension == ".zip":
        with ZipFile(file) as z:
            zip_file_list = z.namelist()
            with z.open(zip_file_list[0]) as f:
                for i, l in enumerate(f):
                    pass
        return i + 1
    else:
        with open(file) as f:
            for i, l in enumerate(f):
                pass
        return i + 1


def move_file(source_absolute_file_path, target_absolute_folder_path, filename):
    if not os.path.exists(target_absolute_folder_path):
        os.makedirs(target_absolute_folder_path)

    target_absolute_file_path = os.path.join(target_absolute_folder_path, filename)

    if os.path.isfile(target_absolute_file_path):
        if file_len(source_absolute_file_path) > file_len(target_absolute_file_path):
            shutil.move(source_absolute_file_path, target_absolute_file_path)
        else:
            os.remove(source_absolute_file_path)
    else:
        shutil.move(source_absolute_file_path, target_absolute_file_path)


def move_file_to_zip(source_absolute_file_path, target_absolute_folder_path, file):
    file_name, extension = os.path.splitext(file)

    if extension == ".xz":
        move_file(source_absolute_file_path, target_absolute_folder_path, file)
        return
    if extension == ".zip":
        move_file(source_absolute_file_path, target_absolute_folder_path, file)
        return

    target_absolute_temp_folder_path = target_absolute_folder_path + "\\temp\\"

    if not os.path.exists(target_absolute_folder_path):
        os.makedirs(target_absolute_folder_path)
    if not os.path.exists(target_absolute_temp_folder_path):
        os.makedirs(target_absolute_temp_folder_path)

    target_absolute_file_path = os.path.join(target_absolute_folder_path, file) + ".zip"
    target_absolute_temp_file_path = os.path.join(target_absolute_temp_folder_path, file) + ".zip"

    if os.path.isfile(target_absolute_file_path):
        if file_len(source_absolute_file_path) <= file_len(target_absolute_file_path):
            os.remove(source_absolute_file_path)
            return

    with ZipFile(target_absolute_temp_file_path,
                 mode='w',
                 compression=ZIP_DEFLATED,
                 compresslevel=1) as f:
        f.write(source_absolute_file_path, os.path.basename(source_absolute_file_path))
    shutil.move(target_absolute_temp_file_path, target_absolute_file_path)
    os.remove(source_absolute_file_path)


def open_file(source_absolute_path, extension):
    if extension == ".json":
        with open(source_absolute_path, 'r') as input_file:
            data = input_file.read()
    elif extension == ".xz":
        with lzma.open(source_absolute_path) as input_file:
            data = input_file.read().decode("utf-8").encode("utf-8")
    elif extension == ".zip":
        with ZipFile(source_absolute_path) as z:
            zip_file_list = z.namelist()
            with z.open(zip_file_list[0]) as input_file:
                data = input_file.read().decode("latin-1").encode("utf-8")
    elif extension == ".temp":
        initial_filename, initial_extension = os.path.splitext(source_absolute_path[:-5])
        data = open_file(source_absolute_path, initial_extension)
    else:
        raise NotImplementedError("open file function doesn't support " + extension + " as extension")

    return data


def list_files(dirlist):
    files = []

    while len(dirlist) > 0:
        for (dirpath, dirnames, filenames) in os.walk(dirlist.pop()):
            dirlist.extend(dirnames)
            files.extend(map(lambda n: os.path.join(*n), zip([dirpath] * len(filenames), filenames)))

    return files