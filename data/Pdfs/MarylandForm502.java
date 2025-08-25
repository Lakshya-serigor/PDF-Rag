import java.util.Date;
import java.util.List;

public class MarylandForm502 {
    public String taxYear;
    public Filer filer;
    public Spouse spouse;
    public int filingStatus;
    public Addresses addresses;
    public PartYear partYear;
    public Income income;
    public Additions additions;
    public Subtractions subtractions;
    public Deductions deductions;
    public Exemptions exemptions;
    public Credits credits;
    public WithholdingAndPayments withholdingAndPayments;
    public FinalAmounts finalAmounts;
    public BankInfo bankInfo;
    public Preparer preparer;

    public double line6TotalAdditions;
    public double line15TotalSubtractions;
    public double line16MarylandAdjustedGrossIncome;
    public double line18NetIncome;
    public double line19ExemptionAmount;
    public double line20TaxableNetIncome;
    public double line26TotalCredits;
    public double line27MdTaxAfterCredits;
    public double line34TotalMdAndLocalTax;
    public double line39TotalTaxPlusContributions;
    public double line44TotalPaymentsAndCredits;
    public double line50TotalAmountDue;

    public static class Filer {
        public String firstName;
        public String middleInitial;
        public String lastName;
        public String ssn;
        public Date dob;
        public boolean isBlind;
        public boolean is65OrOver;
        public boolean isDependentTaxpayer;
    }

    public static class Spouse {
        public String firstName;
        public String middleInitial;
        public String lastName;
        public String ssn;
        public Date dob;
        public boolean isBlind;
        public boolean is65OrOver;
    }

    public static class Addresses {
        public Mailing mailing;
        public MarylandPhysical marylandPhysical;

        public static class Mailing {
            public String line1;
            public String line2;
            public String city;
            public String state;
            public String zip;
            public String foreignCountry;
        }

        public static class MarylandPhysical {
            public String line1;
            public String line2;
            public String city;
            public String county;
            public String zip;
            public String subdivisionCode;
            public String politicalSubdivision;
        }
    }

    public static class PartYear {
        public Date fromDate;
        public Date toDate;
        public double militaryIncome;
    }

    public static class Income {
        public double line1FederalAdjustedGrossIncome;
        public double wages;
        public double earnedIncome;
        public double capitalGain;
        public double pensionsIrAs;
        public boolean highInvestmentIncome;
    }

    public static class Additions {
        public double line2StateBondInterest;
        public double line3RetirementPickup;
        public double line4LumpSumDistributions;
        public double line5OtherAdditions;
    }

    public static class Subtractions {
        public double stateRefunds;
        public double childCare;
        public double pensionExclusion;
        public double socialSecurity;
        public double nonresidentIncome;
        public double twoIncomeSubtraction;
        public double form502SUTotal;
    }

    public static class Deductions {
        public String method; // "standard" or "itemized"
        public double line17StandardDeduction;
        public Line17Itemized line17ItemizedDeductions;

        public static class Line17Itemized {
            public double line17aTotal;
            public double line17bStateLocalTax;
        }
    }

    public static class Exemptions {
        public boolean self;
        public boolean spouse;
        public boolean over65Self;
        public boolean over65Spouse;
        public boolean blindSelf;
        public boolean blindSpouse;
        public List<Dependent> dependents;

        public static class Dependent {
            public String firstName;
            public String lastName;
            public String ssn;
            public Date dob;
            public String relationship;
        }
    }

    public static class Credits {
        public double line22EarnedIncomeCredit;
        public double line23PovertyLevelCredit;
        public double line24Form502CRCreditTotal;
        public double line25BusinessCredits;
    }

    public static class WithholdingAndPayments {
        public double line40W2MdWithholding;
        public double line41EstimatedPayments;
        public double line43Form502CRRefundable;
        public double line42OverpaymentFromLastYear;
    }

    public static class FinalAmounts {
        public double line45BalanceDue;
        public double line46Overpayment;
        public double line48RefundToYou;
        public double line47ApplyToNextYear;
    }

    public static class BankInfo {
        public boolean useDirectDeposit;
        public String accountType;
        public String routingNumber;
        public String accountNumber;
        public String accountHolderNames;
        public boolean outsideUs;
    }

    public static class Preparer {
        public String name;
        public String ptin;
        public String signature;
        public Date date;
        public boolean authorizationToDiscuss;
        public boolean electronicFilingExemption;
    }
}
