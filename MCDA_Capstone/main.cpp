#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <stdexcept>
#include <exception>

#include <Eigen/Dense>

#include "AHP_Class.h"
#include "TOPSIS_Class.h"

using std::cout;
using std::cerr;
using std::endl;

TOPSIS_Class::Vector8 ExtractAHPWeightsFromWeightedNormalizedData(
    const Eigen::MatrixXd& weightedNormalizedData
)
{
    /*
        I am using the Excel table as weighted-normalized TOPSIS data.

        In TOPSIS:
            weighted_normalized_column = normalized_column * AHP_weight

        Since a vector-normalized column has norm 1,
        the norm of each weighted-normalized column gives the applied AHP weight.
    */

    if (weightedNormalizedData.cols() != AHP_Class::CriteriaCount)
    {
        throw std::invalid_argument("Weighted-normalized data must have 8 criteria columns.");
    }

    TOPSIS_Class::Vector8 extractedWeights;

    for (int j = 0; j < AHP_Class::CriteriaCount; ++j)
    {
        double columnNorm = weightedNormalizedData.col(j).norm();

        if (columnNorm <= 1e-12)
        {
            throw std::runtime_error("A criterion column has zero norm.");
        }

        extractedWeights(j) = columnNorm;
    }

    double weightSum = extractedWeights.sum();

    if (weightSum <= 0.0)
    {
        throw std::runtime_error("Extracted AHP weight sum is invalid.");
    }

    return extractedWeights / weightSum;
}

double GetColumnNormSum(
    const Eigen::MatrixXd& weightedNormalizedData
)
{
    /*
        I use this only to print S+ and S- values close to the Excel scale.
        It does not affect the TOPSIS score or ranking.
    */

    double sum = 0.0;

    for (int j = 0; j < weightedNormalizedData.cols(); ++j)
    {
        sum += weightedNormalizedData.col(j).norm();
    }

    return sum;
}

void PrintExtractedWeights(
    const TOPSIS_Class::Vector8& weights
)
{
    cout << "Extracted AHP Weights" << endl;
    cout << "---------------------" << endl;

    for (int i = 0; i < AHP_Class::CriteriaCount; ++i)
    {
        auto criterion = static_cast<AHP_Class::Criteria>(i);

        cout << std::left << std::setw(15)
            << AHP_Class::GetCriteriaName(criterion)
            << " : "
            << std::fixed << std::setprecision(6)
            << weights(i)
            << endl;
    }

    cout << endl;
}

void PrintTOPSISResults(
    const std::vector<TOPSIS_Class::TopsisResult>& results,
    double excelDistanceScale
)
{
    cout << "TOPSIS Ranking Results" << endl;
    cout << "----------------------" << endl;

    cout << std::left
        << std::setw(6) << "Rank"
        << std::setw(34) << "Phone"
        << std::setw(12) << "S+"
        << std::setw(12) << "S-"
        << std::setw(12) << "C+"
        << endl;

    cout << std::string(76, '-') << endl;

    for (const auto& result : results)
    {
        /*
            Internally, TOPSIS may scale distances slightly because the extracted
            weights are normalized. C+ and ranking do not change under common scaling.
            Multiplying by excelDistanceScale makes S+ and S- close to the table.
        */

        double excelSPlus = result.DistanceToIdeal * excelDistanceScale;
        double excelSMinus = result.DistanceToWorst * excelDistanceScale;

        cout << std::left
            << std::setw(6) << result.Rank
            << std::setw(34) << result.PhoneName
            << std::setw(12) << std::fixed << std::setprecision(5) << excelSPlus
            << std::setw(12) << std::fixed << std::setprecision(5) << excelSMinus
            << std::setw(12) << std::fixed << std::setprecision(4) << result.Score
            << endl;
    }

    cout << endl;
}

int main()
{
    try
    {
        /*
            Phone order is the same as the Excel table.
        */

        std::vector<std::string> phoneNames =
        {
            "Apple iPhone 17 Pro Max",
            "Samsung Galaxy S25 Ultra",
            "Oppo Find X9 Pro",
            "Samsung Galaxy Z Fold 7",
            "Asus ROG Phone 9 Pro",
            "OnePlus 13",
            "Xiaomi 15T",
            "Apple iPhone 16e",
            "Samsung Galaxy A56 5G",
            "Nothing CMF Phone 2 Pro"
        };

        /*
            Criterion order:
            Price, Battery, Camera, Performance, Storage, Weight, Charging, ScreenRatio

            These are already weighted-normalized values from the table.
            This means AHP weighting has already been applied before this point.
        */

        Eigen::MatrixXd weightedNormalizedData(10, AHP_Class::CriteriaCount);

        weightedNormalizedData <<
            0.03096, 0.05356, 0.07993, 0.08053, 0.02135, 0.01404, 0.02858, 0.00968,
            0.03354, 0.05263, 0.07663, 0.08528, 0.02135, 0.01325, 0.03215, 0.00978,
            0.03354, 0.07894, 0.07910, 0.09553, 0.02135, 0.01361, 0.05716, 0.00979,
            0.05162, 0.04631, 0.06839, 0.08135, 0.02135, 0.01307, 0.01786, 0.00952,
            0.03096, 0.06105, 0.06839, 0.09265, 0.04270, 0.01380, 0.04644, 0.00933,
            0.02322, 0.06316, 0.07251, 0.08742, 0.02135, 0.01295, 0.07145, 0.00959,
            0.01679, 0.05789, 0.07169, 0.06051, 0.02135, 0.01179, 0.04787, 0.00951,
            0.01547, 0.04216, 0.06098, 0.04782, 0.01067, 0.01015, 0.01786, 0.00921,
            0.01289, 0.05263, 0.05191, 0.02849, 0.01067, 0.01203, 0.03215, 0.00927,
            0.00643, 0.05263, 0.06098, 0.02022, 0.01067, 0.01124, 0.02358, 0.00915;

        /*
            Since the table already contains AHP-weighted values,
            I extract the AHP weights from the table instead of running AHP again.
        */

        TOPSIS_Class::Vector8 ahpWeights =
            ExtractAHPWeightsFromWeightedNormalizedData(weightedNormalizedData);

        PrintExtractedWeights(ahpWeights);

        TOPSIS_Class topsis;

        /*
            The current TOPSIS_Class expects a matrix and a weight vector.
            By giving it the weighted-normalized matrix and extracted weights,
            the internal normalization reconstructs the same TOPSIS structure
            up to a common scale factor.
        */

        topsis.SetDecisionMatrix(phoneNames, weightedNormalizedData);
        topsis.SetWeights(ahpWeights);

        /*
            Price and Weight are cost criteria.
            Lower values are better for them.

            All other criteria are benefit criteria.
            Higher values are better for them.
        */

        topsis.SetCriterionType(AHP_Class::Price, TOPSIS_Class::CriterionType::Cost);
        topsis.SetCriterionType(AHP_Class::Battery, TOPSIS_Class::CriterionType::Benefit);
        topsis.SetCriterionType(AHP_Class::Camera, TOPSIS_Class::CriterionType::Benefit);
        topsis.SetCriterionType(AHP_Class::Performance, TOPSIS_Class::CriterionType::Benefit);
        topsis.SetCriterionType(AHP_Class::Storage, TOPSIS_Class::CriterionType::Benefit);
        topsis.SetCriterionType(AHP_Class::Weight, TOPSIS_Class::CriterionType::Cost);
        topsis.SetCriterionType(AHP_Class::Charging, TOPSIS_Class::CriterionType::Benefit);
        topsis.SetCriterionType(AHP_Class::ScreenRatio, TOPSIS_Class::CriterionType::Benefit);

        std::vector<TOPSIS_Class::TopsisResult> results = topsis.Rank();

        double excelDistanceScale =
            GetColumnNormSum(weightedNormalizedData);

        PrintTOPSISResults(results, excelDistanceScale);
    }
    catch (const std::exception& ex)
    {
        cerr << "Error: " << ex.what() << endl;
        return 1;
    }

    return 0;
}