#include "TOPSIS_Class.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

TOPSIS_Class::TOPSIS_Class()
{
    ClearPhones();

    weights_.setConstant(1.0 / CriteriaCount);

    idealBest_.setZero();
    idealWorst_.setZero();

    SetDefaultCriterionTypes();
}

void TOPSIS_Class::ClearPhones()
{
    phoneNames_.clear();

    decisionMatrix_.resize(0, CriteriaCount);
    normalizedMatrix_.resize(0, CriteriaCount);
    weightedNormalizedMatrix_.resize(0, CriteriaCount);

    lastResults_.clear();
}

void TOPSIS_Class::SetDefaultCriterionTypes()
{
    criterionTypes_.fill(CriterionType::Benefit);

    criterionTypes_[ToIndex(AHP_Class::Price)] = CriterionType::Cost;
    criterionTypes_[ToIndex(AHP_Class::Weight)] = CriterionType::Cost;
}

int TOPSIS_Class::ToIndex(AHP_Class::Criteria criterion)
{
    int index = static_cast<int>(criterion);

    if (index < 0 || index >= CriteriaCount)
    {
        throw std::out_of_range("Invalid TOPSIS criterion index.");
    }

    return index;
}

void TOPSIS_Class::AddPhone(
    const std::string& phoneName,
    double price,
    double battery,
    double camera,
    double performance,
    double storage,
    double weight,
    double charging,
    double screenRatio
)
{
    if (phoneName.empty())
    {
        throw std::invalid_argument("Phone name cannot be empty.");
    }

    std::array<double, CriteriaCount> values =
    {
        price,
        battery,
        camera,
        performance,
        storage,
        weight,
        charging,
        screenRatio
    };

    for (double value : values)
    {
        if (!std::isfinite(value))
        {
            throw std::invalid_argument("Phone criterion values must be finite.");
        }

        if (value < 0.0)
        {
            throw std::invalid_argument("Phone criterion values cannot be negative.");
        }
    }

    int oldRowCount = static_cast<int>(decisionMatrix_.rows());

    decisionMatrix_.conservativeResize(oldRowCount + 1, CriteriaCount);

    for (int j = 0; j < CriteriaCount; ++j)
    {
        decisionMatrix_(oldRowCount, j) = values[j];
    }

    phoneNames_.push_back(phoneName);

    lastResults_.clear();
}

void TOPSIS_Class::SetDecisionMatrix(
    const std::vector<std::string>& phoneNames,
    const Eigen::MatrixXd& matrix
)
{
    if (matrix.cols() != CriteriaCount)
    {
        throw std::invalid_argument("Decision matrix must have exactly 8 criteria columns.");
    }

    if (matrix.rows() != static_cast<int>(phoneNames.size()))
    {
        throw std::invalid_argument("Phone name count must match matrix row count.");
    }

    if (matrix.rows() < 2)
    {
        throw std::invalid_argument("TOPSIS requires at least two phone alternatives.");
    }

    if (!matrix.allFinite())
    {
        throw std::invalid_argument("Decision matrix contains invalid values.");
    }

    for (int i = 0; i < matrix.rows(); ++i)
    {
        if (phoneNames[i].empty())
        {
            throw std::invalid_argument("Phone names cannot be empty.");
        }

        for (int j = 0; j < matrix.cols(); ++j)
        {
            if (matrix(i, j) < 0.0)
            {
                throw std::invalid_argument("Decision matrix values cannot be negative.");
            }
        }
    }

    phoneNames_ = phoneNames;
    decisionMatrix_ = matrix;

    normalizedMatrix_.resize(0, CriteriaCount);
    weightedNormalizedMatrix_.resize(0, CriteriaCount);

    lastResults_.clear();
}

void TOPSIS_Class::SetWeights(const Vector8& weights)
{
    weights_ = NormalizeWeights(weights);
    lastResults_.clear();
}

void TOPSIS_Class::SetWeightsFromAHP(const AHP_Class& ahp)
{
    SetWeights(ahp.GetWeightsVector());
}

void TOPSIS_Class::SetCriterionType(
    AHP_Class::Criteria criterion,
    CriterionType type
)
{
    criterionTypes_[ToIndex(criterion)] = type;
    lastResults_.clear();
}

TOPSIS_Class::CriterionType TOPSIS_Class::GetCriterionType(
    AHP_Class::Criteria criterion
) const
{
    return criterionTypes_[ToIndex(criterion)];
}

TOPSIS_Class::Vector8 TOPSIS_Class::NormalizeWeights(
    const Vector8& weights
)
{
    if (!weights.allFinite())
    {
        throw std::invalid_argument("TOPSIS weights contain invalid values.");
    }

    for (int i = 0; i < CriteriaCount; ++i)
    {
        if (weights(i) < 0.0)
        {
            throw std::invalid_argument("TOPSIS weights cannot be negative.");
        }
    }

    double sum = weights.sum();

    if (sum <= 0.0)
    {
        throw std::invalid_argument("TOPSIS weight sum must be greater than zero.");
    }

    return weights / sum;
}

void TOPSIS_Class::ValidateBeforeRanking() const
{
    if (decisionMatrix_.rows() < 2)
    {
        throw std::runtime_error("TOPSIS requires at least two phone alternatives.");
    }

    if (decisionMatrix_.cols() != CriteriaCount)
    {
        throw std::runtime_error("Decision matrix column count is invalid.");
    }

    if (phoneNames_.size() != static_cast<size_t>(decisionMatrix_.rows()))
    {
        throw std::runtime_error("Phone names and decision matrix rows do not match.");
    }

    if (!decisionMatrix_.allFinite())
    {
        throw std::runtime_error("Decision matrix contains invalid values.");
    }

    if (!weights_.allFinite())
    {
        throw std::runtime_error("TOPSIS weights contain invalid values.");
    }

    double weightSum = weights_.sum();

    if (std::abs(weightSum - 1.0) > 1e-6)
    {
        throw std::runtime_error("TOPSIS weights must sum to 1.");
    }

    for (int j = 0; j < CriteriaCount; ++j)
    {
        double columnNorm = decisionMatrix_.col(j).norm();

        if (columnNorm <= 1e-12)
        {
            throw std::runtime_error("A criterion column has zero norm and cannot be normalized.");
        }
    }
}

TOPSIS_Class::DecisionMatrix TOPSIS_Class::NormalizeDecisionMatrix() const
{
    /*
        Vector normalization removes unit differences between criteria.
        Price, battery, camera score, and weight cannot be compared directly
        unless they are converted to unit-free values.
    */

    DecisionMatrix normalized = decisionMatrix_;

    for (int j = 0; j < CriteriaCount; ++j)
    {
        double columnNorm = decisionMatrix_.col(j).norm();

        normalized.col(j) = decisionMatrix_.col(j) / columnNorm;
    }

    return normalized;
}

TOPSIS_Class::DecisionMatrix TOPSIS_Class::ApplyWeights(
    const DecisionMatrix& normalizedMatrix
) const
{
    /*
        Each criterion column is multiplied by its AHP weight.
        A higher AHP weight makes that criterion more influential in distance calculation.
    */

    return normalizedMatrix * weights_.asDiagonal();
}

void TOPSIS_Class::CalculateIdealSolutions()
{
    /*
        Benefit criterion:
            ideal best  = maximum value
            ideal worst = minimum value

        Cost criterion:
            ideal best  = minimum value
            ideal worst = maximum value
    */

    for (int j = 0; j < CriteriaCount; ++j)
    {
        double columnMax = weightedNormalizedMatrix_.col(j).maxCoeff();
        double columnMin = weightedNormalizedMatrix_.col(j).minCoeff();

        if (criterionTypes_[j] == CriterionType::Benefit)
        {
            idealBest_(j) = columnMax;
            idealWorst_(j) = columnMin;
        }
        else
        {
            idealBest_(j) = columnMin;
            idealWorst_(j) = columnMax;
        }
    }
}

Eigen::VectorXd TOPSIS_Class::CalculateDistancesTo(
    const Vector8& referenceVector
) const
{
    /*
        Each phone is treated as an 8-dimensional vector.
        The Euclidean distance measures how far the phone is from
        either the ideal best vector or the ideal worst vector.
    */

    int phoneCount = static_cast<int>(weightedNormalizedMatrix_.rows());

    Eigen::VectorXd distances(phoneCount);

    for (int i = 0; i < phoneCount; ++i)
    {
        Vector8 phoneVector = weightedNormalizedMatrix_.row(i).transpose();

        distances(i) = (phoneVector - referenceVector).norm();
    }

    return distances;
}

Eigen::VectorXd TOPSIS_Class::CalculateClosenessScores(
    const Eigen::VectorXd& distancesToIdeal,
    const Eigen::VectorXd& distancesToWorst
) const
{
    /*
        TOPSIS score:
            score = distance_to_worst / (distance_to_ideal + distance_to_worst)

        Score close to 1 means the phone is close to ideal best and far from ideal worst.
        Score close to 0 means the phone is close to ideal worst.
    */

    if (distancesToIdeal.size() != distancesToWorst.size())
    {
        throw std::runtime_error("TOPSIS distance vector sizes do not match.");
    }

    Eigen::VectorXd scores(distancesToIdeal.size());

    for (int i = 0; i < distancesToIdeal.size(); ++i)
    {
        double denominator = distancesToIdeal(i) + distancesToWorst(i);

        if (denominator <= 1e-12)
        {
            scores(i) = 0.5;
        }
        else
        {
            scores(i) = distancesToWorst(i) / denominator;
        }
    }

    return scores;
}

std::vector<TOPSIS_Class::TopsisResult> TOPSIS_Class::BuildSortedResults(
    const Eigen::VectorXd& scores,
    const Eigen::VectorXd& distancesToIdeal,
    const Eigen::VectorXd& distancesToWorst
) const
{
    std::vector<TopsisResult> results;

    int phoneCount = static_cast<int>(decisionMatrix_.rows());

    results.reserve(phoneCount);

    for (int i = 0; i < phoneCount; ++i)
    {
        TopsisResult result;

        result.Rank = 0;
        result.OriginalIndex = i;
        result.PhoneName = phoneNames_[i];
        result.Score = scores(i);
        result.DistanceToIdeal = distancesToIdeal(i);
        result.DistanceToWorst = distancesToWorst(i);
        result.WeightedNormalizedValues =
            weightedNormalizedMatrix_.row(i).transpose();

        results.push_back(result);
    }

    std::sort(
        results.begin(),
        results.end(),
        [](const TopsisResult& left, const TopsisResult& right)
        {
            const double epsilon = 1e-12;

            if (std::abs(left.Score - right.Score) > epsilon)
            {
                return left.Score > right.Score;
            }

            return left.DistanceToIdeal < right.DistanceToIdeal;
        }
    );

    for (int i = 0; i < static_cast<int>(results.size()); ++i)
    {
        results[i].Rank = i + 1;
    }

    return results;
}

std::vector<TOPSIS_Class::TopsisResult> TOPSIS_Class::Rank()
{
    ValidateBeforeRanking();

    normalizedMatrix_ = NormalizeDecisionMatrix();

    weightedNormalizedMatrix_ = ApplyWeights(normalizedMatrix_);

    CalculateIdealSolutions();

    Eigen::VectorXd distancesToIdeal =
        CalculateDistancesTo(idealBest_);

    Eigen::VectorXd distancesToWorst =
        CalculateDistancesTo(idealWorst_);

    Eigen::VectorXd scores =
        CalculateClosenessScores(distancesToIdeal, distancesToWorst);

    lastResults_ =
        BuildSortedResults(scores, distancesToIdeal, distancesToWorst);

    return lastResults_;
}

const std::vector<TOPSIS_Class::TopsisResult>& TOPSIS_Class::GetLastResults() const
{
    return lastResults_;
}

const TOPSIS_Class::DecisionMatrix& TOPSIS_Class::GetDecisionMatrix() const
{
    return decisionMatrix_;
}

const TOPSIS_Class::DecisionMatrix& TOPSIS_Class::GetNormalizedMatrix() const
{
    return normalizedMatrix_;
}

const TOPSIS_Class::DecisionMatrix& TOPSIS_Class::GetWeightedNormalizedMatrix() const
{
    return weightedNormalizedMatrix_;
}

TOPSIS_Class::Vector8 TOPSIS_Class::GetWeights() const
{
    return weights_;
}

TOPSIS_Class::Vector8 TOPSIS_Class::GetIdealBest() const
{
    return idealBest_;
}

TOPSIS_Class::Vector8 TOPSIS_Class::GetIdealWorst() const
{
    return idealWorst_;
}