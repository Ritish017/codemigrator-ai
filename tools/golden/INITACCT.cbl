       IDENTIFICATION DIVISION.
       PROGRAM-ID. INITACCT.
      *> Test-harness helper: creates an empty indexed ACCOUNTS.DAT with the
      *> same record layout as ACCOUNT.cbl, because ACCOUNT.cbl opens the file
      *> I-O and fails with status 35 when it does not exist yet.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCOUNT-FILE ASSIGN TO "ACCOUNTS.DAT"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS ACC-NUMBER.
       DATA DIVISION.
       FILE SECTION.
       FD  ACCOUNT-FILE.
       01  ACCOUNT-RECORD.
           05 ACC-NUMBER          PIC 9(10).
           05 ACC-HOLDER-NAME     PIC X(40).
           05 ACC-TYPE            PIC X(02).
           05 ACC-BALANCE         PIC S9(11)V99 COMP-3.
           05 ACC-OPEN-DATE       PIC 9(08).
           05 ACC-STATUS          PIC X(01).
       PROCEDURE DIVISION.
           OPEN OUTPUT ACCOUNT-FILE
           CLOSE ACCOUNT-FILE
           STOP RUN.
