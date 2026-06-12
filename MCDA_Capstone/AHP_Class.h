#pragma once

#include <Eigen/Dense>
#include <string>

class AHP_Class
{
public:
    static constexpr int CriteriaCount = 8;

    enum Criteria
    {
        Price = 0,
        Battery,
        Camera,
        Performance,
        Storage,
        Weight,
        Charging,
        ScreenRatio
    };

    enum class WeightMethod
    {
        GeometricMean,
        EigenVector
    };

    using Matrix8 = Eigen::Matrix<double, CriteriaCount, CriteriaCount>;
    using Vector8 = Eigen::Matrix<double, CriteriaCount, 1>;

public:
    // Kept from your original design.
    // TOPSIS can read this array if you want.
    float CriteriaWeights[CriteriaCount];

public:
    AHP_Class();

    // Resets all criteria comparisons to equal importance.
    void ResetComparisons();

    /*
        Sets pairwise importance.

        Example:
        SetComparison(Camera, Price, 5.0);

        Meaning:
        Camera is 5 times more important than Price.

        Reverse value is automatically inserted:
        Price compared to Camera = 1 / 5.
    */
    void SetComparison(
        Criteria criterionA,
        Criteria criterionB,
        double importanceOfAOverB
    );

    /*
        Calculates the final AHP weights.

        Default is GeometricMean because it is easier and stable.
        EigenVector is the classical AHP eigenvector method.
    */
    void CalculateWeights(
        WeightMethod method = WeightMethod::GeometricMean
    );

    // Returns Consistency Ratio. Usually CR < 0.10 is acceptable.
    double CalculateConsistencyRatio() const;

    // Returns true if CR <= threshold.
    bool IsConsistent(double threshold = 0.10) const;

    // Returns weights as Eigen vector. This is best for TOPSIS.
    Vector8 GetWeightsVector() const;

    // Returns single weight from public array.
    float GetWeight(Criteria criterion) const;

    // Returns the full pairwise comparison matrix.
    Matrix8 GetComparisonMatrix() const;

    // Returns readable criterion name.
    static const char* GetCriteriaName(Criteria criterion);

private:
    Matrix8 comparisonMatrix_;
    Vector8 weightVector_;
    WeightMethod currentMethod_;

private:
    static int ToIndex(Criteria criterion);

    static void ValidateImportanceValue(double value);

    void ValidatePairwiseMatrix() const;

    Vector8 ComputeWeightsGeometricMean() const;

    Vector8 ComputeWeightsEigenVector() const;

    double CalculateLambdaMax(const Vector8& weights) const;

    static double GetRandomIndex(int n);

    void CopyWeightsToPublicArray();
};