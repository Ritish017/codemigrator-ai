       IDENTIFICATION DIVISION.
       PROGRAM-ID. TRANSACT.
       AUTHOR. RITISH-KURMA.
      *>****************************************************
      *> TRANSACTION PROCESSING PROGRAM
      *> Processes deposits, withdrawals, and inter-account
      *> transfers. Reads from a transaction file and updates
      *> the master account file. Writes an audit log entry
      *> for every successful posting.
      *>****************************************************

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TRANS-FILE ASSIGN TO "TRANS.DAT"
               ORGANIZATION IS SEQUENTIAL
               FILE STATUS IS WS-TRANS-STATUS.

           SELECT ACCOUNT-FILE ASSIGN TO "ACCOUNTS.DAT"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS DYNAMIC
               RECORD KEY IS ACC-NUMBER
               FILE STATUS IS WS-ACCT-STATUS.

           SELECT AUDIT-FILE ASSIGN TO "AUDIT.LOG"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-AUDIT-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  TRANS-FILE.
       01  TRANS-RECORD.
           05 TR-TXN-ID           PIC 9(10).
           05 TR-TYPE             PIC X(02).
              88 TR-DEPOSIT       VALUE "DP".
              88 TR-WITHDRAW      VALUE "WD".
              88 TR-TRANSFER      VALUE "TF".
           05 TR-FROM-ACCT        PIC 9(10).
           05 TR-TO-ACCT          PIC 9(10).
           05 TR-AMOUNT           PIC S9(11)V99 COMP-3.
           05 TR-TIMESTAMP        PIC 9(14).

       FD  ACCOUNT-FILE.
       01  ACCOUNT-RECORD.
           05 ACC-NUMBER          PIC 9(10).
           05 ACC-HOLDER-NAME     PIC X(40).
           05 ACC-TYPE            PIC X(02).
           05 ACC-BALANCE         PIC S9(11)V99 COMP-3.
           05 ACC-OPEN-DATE       PIC 9(08).
           05 ACC-STATUS          PIC X(01).

       FD  AUDIT-FILE.
       01  AUDIT-LINE             PIC X(120).

       WORKING-STORAGE SECTION.
       01  WS-TRANS-STATUS        PIC X(02).
       01  WS-ACCT-STATUS         PIC X(02).
       01  WS-AUDIT-STATUS        PIC X(02).
       01  WS-EOF                 PIC X(01) VALUE "N".
           88 WS-AT-EOF           VALUE "Y".
       01  WS-COUNTERS.
           05 WS-PROCESSED        PIC 9(07) VALUE 0.
           05 WS-FAILED           PIC 9(07) VALUE 0.
       01  WS-AUDIT-MSG           PIC X(120).
       01  WS-DISPLAY-AMT         PIC $$,$$$,$$$,$$9.99.

       PROCEDURE DIVISION.
       MAIN-DRIVER.
           PERFORM OPEN-FILES
           PERFORM READ-TRANS
           PERFORM UNTIL WS-AT-EOF
               PERFORM DISPATCH-TRANSACTION
               PERFORM READ-TRANS
           END-PERFORM
           PERFORM CLOSE-FILES
           DISPLAY "PROCESSED: " WS-PROCESSED
           DISPLAY "FAILED:    " WS-FAILED
           STOP RUN.

       OPEN-FILES.
           OPEN INPUT TRANS-FILE
           OPEN I-O ACCOUNT-FILE
           OPEN EXTEND AUDIT-FILE.

       READ-TRANS.
           READ TRANS-FILE
               AT END MOVE "Y" TO WS-EOF
           END-READ.

       DISPATCH-TRANSACTION.
           EVALUATE TRUE
               WHEN TR-DEPOSIT  PERFORM POST-DEPOSIT
               WHEN TR-WITHDRAW PERFORM POST-WITHDRAW
               WHEN TR-TRANSFER PERFORM POST-TRANSFER
               WHEN OTHER       ADD 1 TO WS-FAILED
           END-EVALUATE.

       POST-DEPOSIT.
           MOVE TR-TO-ACCT TO ACC-NUMBER
           READ ACCOUNT-FILE
           IF WS-ACCT-STATUS = "00"
               ADD TR-AMOUNT TO ACC-BALANCE
               REWRITE ACCOUNT-RECORD
               ADD 1 TO WS-PROCESSED
               STRING "DEPOSIT  " TR-TXN-ID " ACC=" TR-TO-ACCT
                      " AMT=" TR-AMOUNT
                      DELIMITED BY SIZE INTO WS-AUDIT-MSG
               WRITE AUDIT-LINE FROM WS-AUDIT-MSG
           ELSE
               ADD 1 TO WS-FAILED
           END-IF.

       POST-WITHDRAW.
           MOVE TR-FROM-ACCT TO ACC-NUMBER
           READ ACCOUNT-FILE
           IF WS-ACCT-STATUS = "00"
               IF ACC-BALANCE >= TR-AMOUNT
                   SUBTRACT TR-AMOUNT FROM ACC-BALANCE
                   REWRITE ACCOUNT-RECORD
                   ADD 1 TO WS-PROCESSED
                   STRING "WITHDRAW " TR-TXN-ID " ACC=" TR-FROM-ACCT
                          " AMT=" TR-AMOUNT
                          DELIMITED BY SIZE INTO WS-AUDIT-MSG
                   WRITE AUDIT-LINE FROM WS-AUDIT-MSG
               ELSE
                   ADD 1 TO WS-FAILED
               END-IF
           ELSE
               ADD 1 TO WS-FAILED
           END-IF.

       POST-TRANSFER.
           MOVE TR-FROM-ACCT TO ACC-NUMBER
           READ ACCOUNT-FILE
           IF WS-ACCT-STATUS = "00" AND ACC-BALANCE >= TR-AMOUNT
               SUBTRACT TR-AMOUNT FROM ACC-BALANCE
               REWRITE ACCOUNT-RECORD
               MOVE TR-TO-ACCT TO ACC-NUMBER
               READ ACCOUNT-FILE
               IF WS-ACCT-STATUS = "00"
                   ADD TR-AMOUNT TO ACC-BALANCE
                   REWRITE ACCOUNT-RECORD
                   ADD 1 TO WS-PROCESSED
                   STRING "TRANSFER " TR-TXN-ID
                          " FROM=" TR-FROM-ACCT
                          " TO="   TR-TO-ACCT
                          " AMT="  TR-AMOUNT
                          DELIMITED BY SIZE INTO WS-AUDIT-MSG
                   WRITE AUDIT-LINE FROM WS-AUDIT-MSG
               ELSE
                   ADD 1 TO WS-FAILED
               END-IF
           ELSE
               ADD 1 TO WS-FAILED
           END-IF.

       CLOSE-FILES.
           CLOSE TRANS-FILE
           CLOSE ACCOUNT-FILE
           CLOSE AUDIT-FILE.
