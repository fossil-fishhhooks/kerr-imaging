"""
standard equation
given voltage V1 -> retardance D1 @ W1 (wavelength)
Dcomp = standard 'compensator' offset
R = bifringence dispersion ratio; RLC = (deltaN_LC(W2)/deltaN_LC(W1))
--> Cauchy's Dispersion Model: bifringence deltaN ( Wx) = A + b/Wx^2
--> for LC A=0.13, b=0.007
--> for the compensator, there is a standard polymer its made of, with  A=0.008 B=0.0001
voltage V1 - > retardance D2 = (D1 + Dcomp) * (W1/W2) * RLC - Dcomp * (W1/W2) * Rcomp  @ W2
"""
## TODO: ^^^^^ check it plz ~Arin



def calculate_correct_delta2(lambda1, delta1_plus_deltac, lambda2, DELTAC): # notice delta1_plus_deltac because this is the dataset vlaue. units: nm, not waves!
    RLC = (0.13 + 7000.0/(lambda2*lambda2))/(0.13 + 7000.0/(lambda1*lambda1)) # constants in nm not micrometers
    RC = (0.008 + 100.0/(lambda2*lambda2))/(0.008 + 100.0/(lambda1*lambda1))
    delta2 = delta1_plus_deltac * (lambda1/lambda2) * RLC - DELTAC * (lambda1/lambda2) * RC
    return delta2