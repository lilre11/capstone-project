#include "main.h"
#include <iostream>
#include "AHP_Class.h"

int main()
{
    AHP_Class ahp;

    /*
        IMPORTANT:
        SetComparison(A, B, value)
        means:
        A is value times more important than B.
    */

    ahp.SetComparison(AHP_Class::Camera, AHP_Class::Price, 5.0);
    ahp.SetComparison(AHP_Class::Battery, AHP_Class::Price, 3.0);
    ahp.SetComparison(AHP_Class::Performance, AHP_Class::Price, 4.0);
    ahp.SetComparison(AHP_Class::Camera, AHP_Class::Weight, 5.0);
    ahp.SetComparison(AHP_Class::Battery, AHP_Class::Weight, 4.0);
    ahp.SetComparison(AHP_Class::Charging, AHP_Class::Weight, 2.0);
    ahp.SetComparison(AHP_Class::ScreenRatio, AHP_Class::Weight, 2.0);
    ahp.SetComparison(AHP_Class::Performance, AHP_Class::Storage, 3.0);

    // We can use GeometricMean or EigenVector.
    ahp.CalculateWeights(AHP_Class::WeightMethod::GeometricMean);

    std::cout << "AHP Weights:\n\n";

    for (int i = 0; i < AHP_Class::CriteriaCount; ++i)
    {
        auto criterion = static_cast<AHP_Class::Criteria>(i);

        std::cout
            << AHP_Class::GetCriteriaName(criterion)
            << " = "
            << ahp.CriteriaWeights[i]
            << "\n";
    }

    double cr = ahp.CalculateConsistencyRatio();

    std::cout << "\nConsistency Ratio = " << cr << "\n";

    if (ahp.IsConsistent())
    {
        std::cout << "Judgments are consistent.\n";
    }
    else
    {
        std::cout << "Warning: Judgments are not consistent enough.\n";
    }

    return 0;
}