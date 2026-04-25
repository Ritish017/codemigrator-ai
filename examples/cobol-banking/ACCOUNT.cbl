       IDENTIFICATION DIVISION.
       PROGRAM-ID. ACCOUNT.
       AUTHOR. RITISH-KURMA.
      *>****************************************************
      *> ACCOUNT MAINTENANCE PROGRAM
      *> Creates new bank accounts and queries existing
      *> account details from the master account file.
      *>****************************************************

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCOUNT-FILE ASSIGN TO "ACCOUNTS.DAT"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS ACC-NUMBER
               FILE STATUS IS WS-FILE-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  ACCOUNT-FILE.
       01  ACCOUNT-RECORD.
           05 ACC-NUMBER          PIC 9(10).
           05 ACC-HOLDER-NAME     PIC X(40).
           05 ACC-TYPE            PIC X(02).
              88 ACC-CHECKING     VALUE "CK".
              88 ACC-SAVINGS      VALUE "SV".
           05 ACC-BALANCE         PIC S9(11)V99 COMP-3.
           05 ACC-OPEN-DATE       PIC 9(08).
           05 ACC-STATUS          PIC X(01).
              88 ACC-ACTIVE       VALUE "A".
              88 ACC-CLOSED       VALUE "C".

       WORKING-STORAGE SECTION.
       01  WS-FILE-STATUS         PIC X(02).
       01  WS-OPERATION           PIC X(01).
           88 WS-CREATE           VALUE "C".
           88 WS-QUERY            VALUE "Q".
       01  WS-INPUT-ACC-NUMBER    PIC 9(10).
       01  WS-INPUT-NAME          PIC X(40).
       01  WS-INPUT-TYPE          PIC X(02).
       01  WS-INPUT-DEPOSIT       PIC S9(11)V99 COMP-3.
       01  WS-DISPLAY-BALANCE     PIC $$,$$$,$$$,$$9.99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           OPEN I-O ACCOUNT-FILE
           IF WS-FILE-STATUS NOT = "00" AND WS-FILE-STATUS NOT = "05"
               DISPLAY "ERROR OPENING ACCOUNT FILE: " WS-FILE-STATUS
               STOP RUN
           END-IF
           PERFORM READ-OPERATION
           EVALUATE WS-OPERATION
               WHEN "C" PERFORM CREATE-ACCOUNT
               WHEN "Q" PERFORM QUERY-ACCOUNT
               WHEN OTHER DISPLAY "INVALID OPERATION"
           END-EVALUATE
           CLOSE ACCOUNT-FILE
           STOP RUN.

       READ-OPERATION.
           DISPLAY "OPERATION (C=CREATE, Q=QUERY): "
           ACCEPT WS-OPERATION.

       CREATE-ACCOUNT.
           DISPLAY "ACCOUNT NUMBER: "
           ACCEPT WS-INPUT-ACC-NUMBER
           DISPLAY "HOLDER NAME: "
           ACCEPT WS-INPUT-NAME
           DISPLAY "TYPE (CK/SV): "
           ACCEPT WS-INPUT-TYPE
           DISPLAY "INITIAL DEPOSIT: "
           ACCEPT WS-INPUT-DEPOSIT
           MOVE WS-INPUT-ACC-NUMBER TO ACC-NUMBER
           MOVE WS-INPUT-NAME       TO ACC-HOLDER-NAME
           MOVE WS-INPUT-TYPE       TO ACC-TYPE
           MOVE WS-INPUT-DEPOSIT    TO ACC-BALANCE
           MOVE FUNCTION CURRENT-DATE(1:8) TO ACC-OPEN-DATE
           MOVE "A"                 TO ACC-STATUS
           WRITE ACCOUNT-RECORD
           IF WS-FILE-STATUS = "00"
               DISPLAY "ACCOUNT CREATED SUCCESSFULLY"
           ELSE
               DISPLAY "WRITE FAILED: " WS-FILE-STATUS
           END-IF.

       QUERY-ACCOUNT.
           DISPLAY "ACCOUNT NUMBER: "
           ACCEPT WS-INPUT-ACC-NUMBER
           MOVE WS-INPUT-ACC-NUMBER TO ACC-NUMBER
           READ ACCOUNT-FILE
           IF WS-FILE-STATUS = "00"
               MOVE ACC-BALANCE TO WS-DISPLAY-BALANCE
               DISPLAY "HOLDER : " ACC-HOLDER-NAME
               DISPLAY "TYPE   : " ACC-TYPE
               DISPLAY "BALANCE: " WS-DISPLAY-BALANCE
               DISPLAY "STATUS : " ACC-STATUS
           ELSE
               DISPLAY "ACCOUNT NOT FOUND"
           END-IF.
