#include "AHP_Class.h"

#include <Eigen/Eigenvalues>
#include <cmath>
#include <stdexcept>
#include <algorithm>

AHP_Class::AHP_Class()
{
    ResetComparisons();
}

void AHP_Class::ResetComparisons()
{
    /*
        In AHP:
        1 means "equal importance".

        We initialize the full matrix with 1s.
        This means if we do not set a comparison, it is treated as equal importance.
    */
    comparisonMatrix_.setOnes();

    weightVector_.setConstant(1.0 / CriteriaCount);

    currentMethod_ = WeightMethod::GeometricMean;

    CopyWeightsToPublicArray();
}

int AHP_Class::ToIndex(Criteria criterion)
{
    int index = static_cast<int>(criterion);

    if (index < 0 || index >= CriteriaCount)
    {
        throw std::out_of_range("Invalid AHP criterion index.");
    }

    return index;
}

void AHP_Class::ValidateImportanceValue(double value)
{
    /*
        Saaty's AHP scale normally goes from 1/9 to 9.

        1     = equal importance
        3     = moderately more important
        5     = strongly more important
        7     = very strongly more important
        9     = extremely more important

        1/3, 1/5, etc. mean the opposite direction.
    */

    const double minValue = 1.0 / 9.0;
    const double maxValue = 9.0;
    const double epsilon = 1e-9;

    if (!std::isfinite(value))
    {
        throw std::invalid_argument("AHP comparison value must be finite.");
    }

    if (value <= 0.0)
    {
        throw std::invalid_argument("AHP comparison value must be positive.");
    }

    if (value < minValue - epsilon || value > maxValue + epsilon)
    {
        throw std::invalid_argument("AHP comparison value must be between 1/9 and 9.");
    }
}

void AHP_Class::SetComparison(
    Criteria criterionA,
    Criteria criterionB,
    double importanceOfAOverB
)
{
    ValidateImportanceValue(importanceOfAOverB);

    int i = ToIndex(criterionA);
    int j = ToIndex(criterionB);

    if (i == j)
    {
        if (std::abs(importanceOfAOverB - 1.0) > 1e-9)
        {
            throw std::invalid_argument("A criterion compared with itself must have value 1.");
        }

        comparisonMatrix_(i, j) = 1.0;
        return;
    }

    /*
        Example:
        If Camera is 5 times more important than Price:

        A(Camera, Price) = 5
        A(Price, Camera) = 1 / 5

        This reciprocal structure is essential in AHP.
    */
    comparisonMatrix_(i, j) = importanceOfAOverB;
    comparisonMatrix_(j, i) = 1.0 / importanceOfAOverB;

    /*
        Recalculate weights immediately.
        Since we only have 8 criteria, recalculation cost is tiny.
    */
    CalculateWeights(currentMethod_);
}

void AHP_Class::ValidatePairwiseMatrix() const
{
    const double epsilon = 1e-6;

    if (!comparisonMatrix_.allFinite())
    {
        throw std::runtime_error("AHP comparison matrix contains invalid values.");
    }

    for (int i = 0; i < CriteriaCount; ++i)
    {
        if (std::abs(comparisonMatrix_(i, i) - 1.0) > epsilon)
        {
            throw std::runtime_error("AHP matrix diagonal values must be 1.");
        }

        for (int j = 0; j < CriteriaCount; ++j)
        {
            if (comparisonMatrix_(i, j) <= 0.0)
            {
                throw std::runtime_error("AHP matrix values must be positive.");
            }

            /*
                AHP reciprocal rule:

                A(i, j) * A(j, i) should be 1.

                Example:
                Camera vs Price = 5
                Price vs Camera = 1/5
                5 * 1/5 = 1
            */
            double reciprocalCheck =
                comparisonMatrix_(i, j) * comparisonMatrix_(j, i);

            if (std::abs(reciprocalCheck - 1.0) > 1e-5)
            {
                throw std::runtime_error("AHP matrix reciprocal condition is broken.");
            }
        }
    }
}

AHP_Class::Vector8 AHP_Class::ComputeWeightsGeometricMean() const
{
    /*
        Geometric mean method:

        For each row:
        GM_i = (a_i1 * a_i2 * ... * a_in) ^ (1/n)

        Then normalize:
        w_i = GM_i / sum(GM)
    */

    Vector8 geometricMeans;

    for (int i = 0; i < CriteriaCount; ++i)
    {
        /*
            We use logs instead of directly multiplying all values.

            Direct product:
            product = a_i1 * a_i2 * ...

            Log version:
            log(product) = log(a_i1) + log(a_i2) + ...

            This is numerically safer.
        */
        double logSum = 0.0;

        for (int j = 0; j < CriteriaCount; ++j)
        {
            logSum += std::log(comparisonMatrix_(i, j));
        }

        geometricMeans(i) = std::exp(logSum / CriteriaCount);
    }

    double sum = geometricMeans.sum();

    if (sum <= 0.0)
    {
        throw std::runtime_error("AHP geometric mean sum is zero.");
    }

    return geometricMeans / sum;
}

AHP_Class::Vector8 AHP_Class::ComputeWeightsEigenVector() const
{
    /*
        Classical AHP can calculate weights from the principal eigenvector.

        Mathematically:
        A * w = lambda_max * w

        A = comparison matrix
        w = criteria weight vector
        lambda_max = largest eigenvalue
    */

    Eigen::EigenSolver<Matrix8> solver(comparisonMatrix_);

    if (solver.info() != Eigen::Success)
    {
        throw std::runtime_error("Eigen decomposition failed in AHP.");
    }

    auto eigenValues = solver.eigenvalues();
    auto eigenVectors = solver.eigenvectors();

    int maxIndex = 0;
    double maxEigenValue = eigenValues(0).real();

    for (int i = 1; i < CriteriaCount; ++i)
    {
        if (eigenValues(i).real() > maxEigenValue)
        {
            maxEigenValue = eigenValues(i).real();
            maxIndex = i;
        }
    }

    /*
        The principal eigenvector should be real and positive.
        Because of numerical calculation, Eigen stores it as complex.
        We take the real part and absolute values.
    */
    Vector8 weights = eigenVectors.col(maxIndex).real().cwiseAbs();

    double sum = weights.sum();

    if (sum <= 0.0)
    {
        throw std::runtime_error("AHP eigenvector weight sum is zero.");
    }

    return weights / sum;
}

void AHP_Class::CalculateWeights(WeightMethod method)
{
    ValidatePairwiseMatrix();

    currentMethod_ = method;

    if (method == WeightMethod::EigenVector)
    {
        weightVector_ = ComputeWeightsEigenVector();
    }
    else
    {
        weightVector_ = ComputeWeightsGeometricMean();
    }

    CopyWeightsToPublicArray();
}

double AHP_Class::CalculateLambdaMax(const Vector8& weights) const
{
    /*
        For a perfectly consistent AHP matrix:

        A * w = n * w

        In real cases, it becomes:

        A * w ≈ lambda_max * w

        lambda_max is used for consistency calculation.
    */

    Eigen::Matrix<double, CriteriaCount, 1> Aw = comparisonMatrix_ * weights;

    double lambdaSum = 0.0;

    for (int i = 0; i < CriteriaCount; ++i)
    {
        if (std::abs(weights(i)) < 1e-12)
        {
            throw std::runtime_error("AHP weight is too close to zero.");
        }

        lambdaSum += Aw(i) / weights(i);
    }

    return lambdaSum / CriteriaCount;
}

double AHP_Class::GetRandomIndex(int n)
{
    /*
        Saaty's Random Index table.

        For our project:
        n = 8 criteria
        RI = 1.41
    */

    switch (n)
    {
    case 1: return 0.00;
    case 2: return 0.00;
    case 3: return 0.58;
    case 4: return 0.90;
    case 5: return 1.12;
    case 6: return 1.24;
    case 7: return 1.32;
    case 8: return 1.41;
    case 9: return 1.45;
    case 10: return 1.49;
    default:
        throw std::runtime_error("Random Index is not defined for this number of criteria.");
    }
}

double AHP_Class::CalculateConsistencyRatio() const
{
    ValidatePairwiseMatrix();

    int n = CriteriaCount;

    if (n <= 2)
    {
        return 0.0;
    }

    double lambdaMax = CalculateLambdaMax(weightVector_);

    double consistencyIndex = (lambdaMax - n) / (n - 1);

    /*
        Very small negative values can happen due to floating-point precision.
        Example: -0.00000000001
        We clamp that to zero.
    */
    if (consistencyIndex < 0.0 && std::abs(consistencyIndex) < 1e-8)
    {
        consistencyIndex = 0.0;
    }

    double randomIndex = GetRandomIndex(n);

    if (randomIndex == 0.0)
    {
        return 0.0;
    }

    return consistencyIndex / randomIndex;
}

bool AHP_Class::IsConsistent(double threshold) const
{
    return CalculateConsistencyRatio() <= threshold;
}

AHP_Class::Vector8 AHP_Class::GetWeightsVector() const
{
    return weightVector_;
}

float AHP_Class::GetWeight(Criteria criterion) const
{
    return CriteriaWeights[ToIndex(criterion)];
}

AHP_Class::Matrix8 AHP_Class::GetComparisonMatrix() const
{
    return comparisonMatrix_;
}

const char* AHP_Class::GetCriteriaName(Criteria criterion)
{
    switch (criterion)
    {
    case Price:       return "Price";
    case Battery:     return "Battery";
    case Camera:      return "Camera";
    case Performance: return "Performance";
    case Storage:     return "Storage";
    case Weight:      return "Weight";
    case Charging:    return "Charging";
    case ScreenRatio: return "Screen Ratio";
    default:          return "Unknown";
    }
}

void AHP_Class::CopyWeightsToPublicArray()
{
    for (int i = 0; i < CriteriaCount; ++i)
    {
        CriteriaWeights[i] = static_cast<float>(weightVector_(i));
    }
}