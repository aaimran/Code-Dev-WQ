!> Module to hold and validate all runtime configuration parameters.
MODULE config_mod
  USE datatypes, ONLY: real_wp
  IMPLICIT NONE

  PRIVATE

  PUBLIC :: config_t, cfg, config_read, config_validate

  TYPE :: config_t
    !> Problem response type (e.g., 'elastic', 'constant-Q-8M')
    CHARACTER(LEN=32) :: response = 'elastic'
    !> Finite difference order
    INTEGER :: iord = 4
    !> Fault model
    INTEGER :: ifault = 1

    !> Constant Q parameters
    REAL(real_wp) :: Qp_inv = 0.0
    REAL(real_wp) :: Qs_inv = 0.0

    !> Frequency-dependent Q parameters
    REAL(real_wp) :: Q_op_f_trans = 1.0
    REAL(real_wp) :: Q_op_gamma = 0.7

    ! Add other parameters from namelists here...

  END TYPE config_t

  !> Global instance of the configuration type
  TYPE(config_t) :: cfg

CONTAINS

  !> Placeholder for subroutine to read all namelists into the cfg type
  SUBROUTINE config_read()
    ! In a real implementation, this would open the input file,
    ! read all namelists, and populate the 'cfg' variable.
    PRINT *, "Reading configuration..."
  END SUBROUTINE config_read

  !> Validates the configuration stored in the global 'cfg' variable.
  SUBROUTINE config_validate()
    PRINT *, "Validating configuration..."
    IF (TRIM(cfg%response) == 'constant-Q-8M' .AND. cfg%Qs_inv <= 0.0) THEN
      STOP "ERROR: 'constant-Q-8M' requires a positive Qs_inv value."
    END IF
    ! Add more validation checks here...
  END SUBROUTINE config_validate

END MODULE config_mod