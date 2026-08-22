# Bambuddy plugin 1.3.10 hotfix

Physical X2D acceptance found a SQLAlchemy MissingGreenlet in the FilaMan plugin consumption writer after Bambuddy had correctly calculated and applied usage. This release bundles plugin 1.3.10, which eager-loads spool relationships and retries transient writes with the same idempotency key.
