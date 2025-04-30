import os
import comtypes
import comtypes.client
# def get_files(folder_path):
#     return os.listdir(folder_path)
 
# 使用示例
# folder_path = '/path/to/your/folder'
# filenames = get_filenames(folder_path)
# print(filenames)

def CheckSplitRepeat(s, t):
    lst = s.split(t)
    lst_without_spaces = [s.strip() for s in lst]
    #print("set {}, lst {}", len(set(lst_without_spaces)) , len(lst_without_spaces))
    return len(set(lst_without_spaces)) == len(lst_without_spaces)

def WordToPdf(docx):        #use microsoft.office 
    print("docx:", docx)
    if not os.path.exists(docx):
        return -1
    dir = os.path.dirname(docx)
    fullname = os.path.basename(docx)
    lst = os.path.splitext(fullname)
    print("dir:", dir)
    print("fullname:", fullname)
    print("lst:", lst)
    filename = lst[-2]
    ext = lst[-1]
    print("filename:", filename)
    print("ext:", ext)
    if not ext == ".docx" and not ext == ".doc":
        return -2
    pdf = dir + "\\" + filename + ".pdf"
    print("pdf:", pdf)
    ret = 1
    try:
        word = comtypes.client.CreateObject("Word.Application")
        doc = word.Documents.Open(FileName=docx)
        doc.SaveAs(pdf, FileFormat=17)
        doc.Close()
        word.Quit()
    except Exception as e:
        print(str(e))
        ret = -3
    return ret


# print(process)

def main():
    WordToPdf("E:\\sdmp3-client[master]\\Build\\Debug\\temp\\file\\fileVerify\\安徽颍上农村商业银行股份有限公司2023年度报告.docx")

if __name__ == "__main__":
    main()