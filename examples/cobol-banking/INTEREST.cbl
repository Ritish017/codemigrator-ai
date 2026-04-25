       IDENTIFICATION DIVISION.
       PROGRAM-ID. INTEREST.
       AUTHOR. RITISH-KURMA.
      *>****************************************************
      *> COMPOUND INTEREST POSTING
      *> Iterates through all SAVINGS accounts and credits
      *> compound interest for the period. Compounding cycles
      *> are configurable; default is 12 (monthly).
      *>****************************************************

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT ACCOUNT-FILE ASSIGN TO "ACCOUNTS.DAT"
               ORGANIZATION IS INDEXED
               ACCESS MODE IS SEQUENTIAL
               RECORD KEY IS ACC-NUMBER
               FILE STATUS IS WS-FILE-STATUS.

           SELECT REPORT-FILE ASSIGN TO "INTEREST.RPT"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  ACCOUNT-FILE.
       01  ACCOUNT-RECORD.
           05 ACC-NUMBER          PIC 9(10).
           05 ACC-HOLDER-NAME     PIC X(40).
           05 ACC-TYPE            PIC X(02).
              88 ACC-SAVINGS      VALUE "SV".
           05 ACC-BALANCE         PIC S9(11)V99 COMP-3.
           05 ACC-OPEN-DATE       PIC 9(08).
           05 ACC-STATUS          PIC X(01).
              88 ACC-ACTIVE       VALUE "A".

       FD  REPORT-FILE.
       01  REPORT-LINE            PIC X(132).

       WORKING-STORAGE SECTION.
       01  WS-FILE-STATUS         PIC X(02).
       01  WS-EOF                 PIC X(01) VALUE "N".
           88 WS-AT-EOF           VALUE "Y".

       01  WS-PARAMS.
           05 WS-ANNUAL-RATE      PIC S9(03)V9(04) VALUE 0.0450.
           05 WS-PERIODS          PIC 9(03) VALUE 12.
           05 WS-YEARS            PIC 9(03) VALUE 1.

       01  WS-MATH.
           05 WS-PERIOD-RATE      PIC S9(03)V9(09) COMP-3.
           05 WS-FACTOR           PIC S9(05)V9(09) COMP-3 VALUE 1.
           05 WS-N-COMPOUNDS      PIC 9(05).
           05 WS-IDX              PIC 9(05).
           05 WS-OLD-BALANCE      PIC S9(11)V9(02) COMP-3.
           05 WS-NEW-BALANCE      PIC S9(11)V9(02) COMP-3.
           05 WS-INTEREST         PIC S9(11)V9(02) COMP-3.
           05 WS-TOTAL-INTEREST   PIC S9(13)V9(02) COMP-3 VALUE 0.

       01  WS-COUNTERS.
           05 WS-ACCOUNTS-READ    PIC 9(07) VALUE 0.
           05 WS-ACCOUNTS-CREDITED PIC 9(07) VALUE 0.

       01  WS-DISPLAY.
           05 WS-DISPLAY-INTEREST PIC $$,$$$,$$$,$$9.99.
           05 WS-DISPLAY-TOTAL    PIC $$,$$$,$$$,$$$,$$9.99.
           05 WS-REPORT-LINE      PIC X(132).

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM OPEN-FILES
           PERFORM COMPUTE-PERIOD-RATE
           PERFORM PROCESS-ACCOUNTS UNTIL WS-AT-EOF
           PERFORM WRITE-SUMMARY
           PERFORM CLOSE-FILES
           STOP RUN.

       OPEN-FILES.
           OPEN I-O ACCOUNT-FILE
           OPEN OUTPUT REPORT-FILE.

       COMPUTE-PERIOD-RATE.
      *>     i = annual_rate / periods
           DIVIDE WS-ANNUAL-RATE BY WS-PERIODS GIVING WS-PERIOD-RATE
           COMPUTE WS-N-COMPOUNDS = WS-PERIODS * WS-YEARS
      *>     factor = (1 + i) ** n  -- expand via PERFORM-VARYING
           MOVE 1 TO WS-FACTOR
           PERFORM VARYING WS-IDX FROM 1 BY 1
               UNTIL WS-IDX > WS-N-COMPOUNDS
               COMPUTE WS-FACTOR = WS-FACTOR * (1 + WS-PERIOD-RATE)
           END-PERFORM.

       PROCESS-ACCOUNTS.
           READ ACCOUNT-FILE NEXT
               AT END MOVE "Y" TO WS-EOF
           END-READ
           IF NOT WS-AT-EOF
               ADD 1 TO WS-ACCOUNTS-READ
               IF ACC-SAVINGS AND ACC-ACTIVE
                   PERFORM CREDIT-INTEREST
               END-IF
           END-IF.

       CREDIT-INTEREST.
           MOVE ACC-BALANCE TO WS-OLD-BALANCE
           COMPUTE WS-NEW-BALANCE = WS-OLD-BALANCE * WS-FACTOR
           COMPUTE WS-INTEREST    = WS-NEW-BALANCE - WS-OLD-BALANCE
           MOVE WS-NEW-BALANCE TO ACC-BALANCE
           REWRITE ACCOUNT-RECORD
           ADD WS-INTEREST    TO WS-TOTAL-INTEREST
           ADD 1              TO WS-ACCOUNTS-CREDITED
           MOVE WS-INTEREST   TO WS-DISPLAY-INTEREST
           STRING "ACC=" ACC-NUMBER
                  " HOLDER=" ACC-HOLDER-NAME
                  " INTEREST=" WS-DISPLAY-INTEREST
                  DELIMITED BY SIZE INTO WS-REPORT-LINE
           WRITE REPORT-LINE FROM WS-REPORT-LINE.

       WRITE-SUMMARY.
           MOVE WS-TOTAL-INTEREST TO WS-DISPLAY-TOTAL
           STRING "TOTAL INTEREST CREDITED: " WS-DISPLAY-TOTAL
                  DELIMITED BY SIZE INTO WS-REPORT-LINE
           WRITE REPORT-LINE FROM WS-REPORT-LINE
           STRING "ACCOUNTS CREDITED: " WS-ACCOUNTS-CREDITED
                  " / READ: " WS-ACCOUNTS-READ
                  DELIMITED BY SIZE INTO WS-REPORT-LINE
           WRITE REPORT-LINE FROM WS-REPORT-LINE.

       CLOSE-FILES.
           CLOSE ACCOUNT-FILE
           CLOSE REPORT-FILE.
