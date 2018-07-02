import psycopg2
import datetime
from enum import Enum
import math
global cur, dueClassNum, stuNum


hlp = '''
Enter command to operate

as - Add Student
    Format: as StudentID StudentName
    StudentID should be a 13-digit number.
    No constraint for StudentName.

aa - Add Attendance record
    Format: aa ClassDate AbsentStudentID1 AbsentStudentID2 ...
    Assume the record is for a next class. Please enter at a time ALL the students absent from one class.
    eg, The last time is 14th then this entry means ALL the students absent from 15th class.
    AbsentStudentIDs can be null, which means all students are present at that class.

is - Inquire by Student
    Format: is StudentID/StudentName
    The student's absence will be shown.

ic - Inquire by Class
    Format: ic ClassNumber(1 - first 2 - second...)/ClassDate(mm-dd, eg 09-05)
    Students absent from that class will be shown.

ia - Inquire by Attendance
    Format: ia AttendanceThreshold(integer percentage, eg 80 representing 80%)
    Students with Attendance below the threshold will be shown.

g - Get the present number of students and classes

n - erase all the records to start a New semester

hp - show this Help

s - Save changes

x - Abort changes since last save

q - save changes and Quit

xq - Quit without saving changes

This help won't be shown after running a command unless 'hp' is called.
'''


class Hint(Enum):
    InvalidCommand = "Invalid Command! Please Re-Enter"
    NoStudent = "No student in database! Please use 'as' to Add Student"
    NoClass = "No attendance record in database! Please use 'aa' to Add Attendance record"
    StudentNotFound = "Student not found!"
    DateInvalid = "No class on this date!"
    ClassOverflow = "This class has not been recorded."
    ClassNoAbsence = "No students were absent from that class."
    StudentNoAbsence = "is a good student with no absence till now."
    GoodStudents = "No students have attendance below the given threshold."

class Exep(Exception):
    def __init__(self, hint):
        Exception.__init__(self)
        self.message = hint.value


def getStudentNumber():
    global cur
    # SQL: SELECT COUNT(*) FROM "Student"
    cur.execute("SELECT COUNT(*) FROM \"Student\"")
    res = cur.fetchone()[0]
    try:
        if res == 0:
            raise Exep(Hint.NoStudent)
    except Exep as e:
        print(e.message)
    else:
        return res

def getDueClassNumber():
    global cur
    # SQL: SELECT COUNT(*) FROM "Date"
    cur.execute("SELECT COUNT(*) FROM \"Date\"")
    res = cur.fetchone()[0]
    try:
        if res == 0:
            raise Exep(Hint.NoClass)
    except Exep as e:
        print(e.message)
    else:
        return res + 1


def addStudent(str):
    global cur, stuNum
    (ID, Name) = str.split()
    # SQL: INSERT INTO "Student" VALUES (ID, Name)
    cur.execute("INSERT INTO \"Student\" VALUES (%s, %s)", (ID, Name))
    # SQL: INSERT INTO "Attendance"("ID", "Absence") VALUES (ID, 0)
    cur.execute("INSERT INTO \"Attendance\"(\"ID\", \"Absence\") VALUES (%s, 0)", (ID, ))
    if stuNum is None:
        stuNum = 1
    else:
        stuNum += 1
    print("Add Student Successfully!")
  
def addAttendance(ClassDate, AbsentList):
    allIgnored = (len(AbsentList) != 0)
    global dueClassNum, cur
    AbsentList = list(set(AbsentList))
    for absence in AbsentList:
        # SQL: SELECT * FROM "Student" WHERE "ID" = absence
        cur.execute("SELECT * FROM \"Student\" WHERE \"ID\" = %s", (absence, ))
        if cur.fetchone() is None:
            print("Student {0} don't exist and is IGNORED!".format(absence))
        else:
            allIgnored = False
            if dueClassNum is None:
                dueClassNum = 1
            elif AbsentList[0] == absence:
                # SQL: ALTER TABLE "Attendance"
                #      ADD "dueClassNum" BOOLEAN
                cur.execute(
                    "ALTER TABLE \"Attendance\"     \
                    ADD \"%s\" BOOLEAN", (dueClassNum, )) 
            # SQL: UPDATE "Attendance" 
            #      SET "dueClassNum" = FALSE, 
            #          "Absence" = "Absence" + 1
            #      WHERE "ID" = absence
            cur.execute(
                "UPDATE \"Attendance\" SET \"%s\" = FALSE,   \
                \"Absence\" = \"Absence\" + 1 \
                WHERE \"ID\" = %s"
                , (dueClassNum, absence))
    if not allIgnored:
        if len(AbsentList) == 0:
            print("No students are absent from this class.")
        # Set students' Attendance
        # SQL: UPDATE "Attendance"
        #      SET "dueClassNum" = TRUE
        #      WHERE "dueClassNum" IS NULL
        cur.execute("UPDATE \"Attendance\" SET \"%(t)s\" = TRUE \
                   WHERE \"%(t)s\" IS NULL", {'t': dueClassNum})     
        # Set class Date 
        # SQL: INSERT INTO "Date" VALUES (ClassDate)
        cur.execute("INSERT INTO \"Date\" VALUES (%s)", (ClassDate, )) 
        dueClassNum += 1
        print("Add Class Successfully!")
    else:
        print("ALL the students in this entry don't exist! No change is carried out")
         
def inquireStudent(str, mode):
    global cur
    # mode = ID or Name
    # SQL: SELECT "Student"."Name", "Attendance".* 
    #      FROM "Attendance", "Student"
    #      WHERE "Attendance"."ID" = "Student"."ID" AND "Student"."mode" = str
    cur.execute(
        "SELECT \"Attendance\".*, \"Student\".\"Name\"  \
        FROM \"Attendance\", \"Student\"  \
        WHERE \"Attendance\".\"ID\" = \"Student\".\"ID\" AND \"Student\".\"{0}\" = %s".format(mode)
        , (str, ))
    rec = cur.fetchone()
    # rec[0] is Name, rec[1] is ID, rec[2] is absence count, rec[3:] is attendance record
    try:
        if rec is None:
            raise Exep(Hint.StudentNotFound)
    except Exep as e:
        print(e.message)
    else:                
        print("Student:")
        print(rec[1], rec[0])
        try:
            if rec[2] == 0:
                raise Exep(Hint.StudentNoAbsence)
        except Exep as e:
            print(e.message)
        else:
            # Get his absent classes and dates
            res = list()
            global dueClassNum
            for i in range(1, dueClassNum):
                if not rec[i + 2]:
                    res.append(i)
            attendance = format(1 - rec[2] / (dueClassNum - 1), '.0%')
            print("Attendance: {0}".format(attendance), "Absent times: {0}".format(rec[17]))
            print("Absent date(s): ", end = '')
            for abst in res:
                # SQL: SELECT * FROM "Date" 
                cur.execute("SELECT * FROM \"Date\"")
                date = cur.fetchall()[abst][0]
                print(date, end = ' ')
            print()

def inquireClassSeq(seq):
    global cur
    # SQL: SELECT "Student".*
    #      FROM "Attendance", "Student"
    #      WHERE "Attendance"."seq" = FALSE AND "Attendance"."ID" = "Student"."ID"
    cur.execute(
        "SELECT \"Student\".*  \
        FROM \"Attendance\", \"Student\"   \
        WHERE \"Attendance\".\"%s\" = FALSE AND \"Attendance\".\"ID\" = \"Student\".\"ID\""
        , (seq, ))
    rec = cur.fetchall()
    try:
        if len(rec) == 0:
            raise Exep(Hint.ClassNoAbsence)
    except Exep as e:
        print(e.message)
    else:
        # SQL: SELECT * FROM "Date"
        cur.execute("SELECT * FROM \"Date\"")
        date = cur.fetchall()[seq][0]
        print("The following student(s) was/were absent from that class({0}):".format(date))
        for (ID, Name) in rec:
            print(ID, Name)
        global stuNum
        absentPercent = format(len(rec) / stuNum, '.0%')
        print("{0} student(s) in total, accounting for {1} of all the students.".format(len(rec), absentPercent))

def inquireClassDate(str):
    global cur
    try:
        date = datetime.datetime.strptime(str)
        # SQL: SELECT * FROM "Date"
        cur.execute("SELECT * FROM \"Date\"")
        rec = cur.fetchone()
        seq = 1        
        while rec[0] != date:
            rec = cur.fetchone()
            seq += 1
            if rec is None:
                raise Exep(Hint.DateInvalid)      
        inquireClassSeq(seq)  
    except ValueError:
        # bad Date entry, eg 14-40
        raise Exep(Hint.InvalidCommand)                
    except Exep as e:
        print(e.message)         
            

def inquireAttendance(thresh):
    global cur
    # SQL: SELECT "Student".*, "Attendance"."Absence"
    #      FROM "Student", "Attendance"
    #      WHERE "Student"."ID" = "Attendance"."ID" AND "Attendance"."Absence" >= thresh
    cur.execute(
        "SELECT \"Student\".*, \"Attendance\".\"Absence\" \
        FROM \"Student\", \"Attendance\"    \
        WHERE \"Student\".\"ID\" = \"Attendance\".\"ID\" AND \"Attendance\".\"Absence\" >= %s"
        , (thresh, ))
    rec = cur.fetchall()
    try:
        if len(rec) == 0:
            raise Exep(Hint.GoodStudents)
    except Exep as e:
        print(e.message)
    else:
        print("Students with low attendance:")
        for (ID, Name, Absence) in rec:
            print(ID, Name, "Absent times: {0}".format(Absence))
        global dueClassNum
        print("Total number of classes is {0}".format(dueClassNum - 1))

# Signature and Connect to database
print("------ Logic's Attendance Management System ------")
print("Connecting to Database...", end = '')
conn = psycopg2.connect(database = "postgres", user = "postgres", password = "slcjua", 
                        host = "localhost", port = "5432")
cur = conn.cursor()
print("Connection Established!")
print(hlp)


try:
    # Create tables, if tables already exist ProgrammingError will be raised
    # SQL: CREATE TABLE "Student"
    #      ("ID" CHAR(13) PRIMARY KEY,
    #      "Name" TEXT NOT NULL)    
    cur.execute(
        "CREATE TABLE \"Student\"    \
        (\"ID\" CHAR(13) PRIMARY KEY,     \
        \"Name\" TEXT NOT NULL)"
        )
    # SQL: CREATE TABLE "Attendance"
    #      ("ID" CHAR(13) PRIMARY KEY,
    #      "Absence" SMALLINT NOT NULL,
    #      "1" BOOLEAN,
    #      FOREIGN KEY("ID") REFERENCES "Student"("ID"))
    cur.execute(
        '''CREATE TABLE \"Attendance\"
        (\"ID\" CHAR(13) PRIMARY KEY,
        \"Absence\" SMALLINT NOT NULL,
        \"1\" BOOLEAN,
        FOREIGN KEY(\"ID\") REFERENCES \"Student\"(\"ID\")
        )'''
        )
    # SQL: CREATE TABLE "Date"
    #      ("Date" DATE PRIMARY KEY)
    cur.execute(
        "CREATE TABLE \"Date\"   \
        (\"Date\" DATE PRIMARY KEY)")
except psycopg2.ProgrammingError:
    # the Error disables afterward SQL through psycopg2
    # rollback to enable
    conn.rollback()
else:
    print("Database newly setup.")

stuNum = getStudentNumber()
if stuNum is not None:
    dueClassNum = getDueClassNumber()
else:
    dueClassNum = None

# Get Command and check validity
while True:
    try:
        cmd = input('>')
        if cmd == "hp":
            # Help
            print(hlp)
        elif cmd == "n":
            # New
            print("Are you sure to wipe out all the records of students? Y - Yes Other - No: ", end = '')
            ch = input()
            if ch == 'Y':
                # SQL: DROP TABLE "Attendance" CASCADE
                #      DROP TABLE "Student" CASCADE
                #      DROP TABLE "Date" CASCADE
                cur.execute("DROP TABLE \"Attendance\" CASCADE")
                cur.execute("DROP TABLE \"Student\" CASCADE")
                cur.execute("DROP TABLE \"Date\" CASCADE")                
                stuNum = dueClassNum = None
                print("All records are deleted Successfully!")               
        elif cmd == "g":
            # Get number
            pstuNum = stuNum
            if pstuNum is None:
                pstuNum = 0
            classNum = dueClassNum
            if classNum is None:
                classNum = 0
            else:
                classNum -= 1
            print("Number of Students = {0}, Number of Classes = {1}".format(pstuNum, classNum))
        elif cmd == "q":
            # save Quit
            print("Are you sure to SAVE all changes and Quit? Y - Yes Other - No: ", end = '')
            ch = input()
            if ch == 'Y':
                conn.commit()
                break
        elif cmd == "xq":
            # unsave Quit
            print("Are you sure to ABORT all changes and Quit? Y - Yes Other - No: ", end = '')
            ch = input()
            if ch == 'Y':
                conn.rollback()
                break
        elif cmd == "s":
            # Save
            conn.commit()
            print("Changes saved!")
        elif cmd == "x":
            # Abort
            conn.rollback()
            print("Changes aborted!")            
        else:            
            if cmd[0] == 'a':
                if cmd[1:3] == "s ":
                    # Add Student
                    try:
                        if cmd[3:16].isdigit() and cmd[16] == ' ' and cmd[17] != ' ':
                            addStudent(cmd[3:])
                        else:
                            raise Exep(Hint.InvalidCommand)
                    except IndexError:
                        raise Exep(Hint.InvalidCommand)
                    except Exep as e:
                        print(e.message)
                elif cmd[1:3] == "a ":
                    # Add Attendance
                    if stuNum is None:
                        raise Exep(Hint.NoStudent)
                    tmp = cmd[3:].split()
                    IDs = Date = None
                    try:
                        Date = datetime.datetime.strptime(tmp[0], "%m-%d")
                    except ValueError:
                        raise Exep(Hint.InvalidCommand)
                    try:
                        IDs = tmp[1:]
                    except IndexError:
                        IDs = list()
                    for ID in IDs:
                        if len(ID) != 13 or (not ID.isdigit()):
                            raise Exep(Hint.InvalidCommand)
                    addAttendance(Date, IDs)
                else:
                    raise Exep(Hint.InvalidCommand)
            elif cmd[0] == 'i':
                if stuNum is None:
                    raise Exep(Hint.NoStudent)
                elif dueClassNum is None:
                    raise Exep(Hint.NoClass)
                elif cmd[1:3] == "s ":
                    # Inquire Student
                    if cmd[3].isdigit():
                        if cmd[4:16].isdigit() and len(cmd) == 16:        
                            # by ID                    
                            inquireStudent(cmd[3:], "ID")
                        else:
                            raise Exep(Hint.InvalidCommand)
                    else:
                        # by Name
                        inquireStudent(cmd[3:], "Name")
                elif cmd[1:3] == "a ":
                    # Inquire Attendance
                    if cmd[3:].isdigit() and len(cmd) < 6:
                        threshold = dueClassNum - math.ceil(int(cmd[3:]) * (dueClassNum - 1) / 100)
                        inquireAttendance(threshold)
                    else:
                        raise Exep(Hint.InvalidCommand)
                elif cmd[1:3] == "c ":
                    # Inquire Class
                    if cmd[3:].isdigit():
                        Seq = int(cmd[3:])
                        if Seq < dueClassNum:
                            # by Seq
                            inquireClassSeq(Seq)
                        else:
                            raise Exep(Hint.ClassOverflow)
                    else:
                        # by Date
                        inquireClassDate(cmd[3:])
                else:
                    raise Exep(Hint.InvalidCommand)
            else:
                raise Exep(Hint.InvalidCommand)
    except Exep as e:
        print(e.message)

# Close
print("Closing Connection...", end = '')
cur.close()
conn.close()
print("Connection Closed!\n")
print("Thank you for using!")
print("------ Logic's Attendance Management System ------")