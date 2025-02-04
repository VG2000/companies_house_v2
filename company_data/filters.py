import django_filters
from company_data.models import FinancialStatement

class FinancialStatementFilter(django_filters.FilterSet):
    turnover_revenue = django_filters.NumberFilter(field_name="turnover_revenue", lookup_expr="gt")
    profit_before_tax = django_filters.NumberFilter(field_name="profit_before_tax", lookup_expr="gt")
    operating_profit_loss = django_filters.NumberFilter(field_name="operating_profit_loss", lookup_expr="gt")

    class Meta:
        model = FinancialStatement
        fields = ["turnover_revenue", "profit_before_tax", "operating_profit_loss"]
