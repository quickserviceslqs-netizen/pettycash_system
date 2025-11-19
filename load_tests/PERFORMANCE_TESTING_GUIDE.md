# Performance Testing Guide

## Overview
Comprehensive load testing scenarios for the Petty Cash Management System using Locust.

## Installation

```powershell
pip install locust
```

## Running Load Tests

### 1. Local Development Testing

```powershell
# Start your Django dev server first
python manage.py runserver

# In another terminal, run Locust
locust -f load_tests\locustfile.py --host=http://localhost:8000
```

Open browser: http://localhost:8089

### 2. Staging Environment Testing

```powershell
locust -f load_tests\locustfile.py --host=https://staging.yourcompany.com
```

### 3. Command-Line Testing (No Web UI)

```powershell
# 100 users, spawn 10 per second, run for 5 minutes
locust -f load_tests\locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Test Scenarios

### User Types

1. **TreasuryUser** (Weight: 3)
   - Dashboard monitoring
   - Payment execution
   - Alert management
   - High activity, 1-3s wait time

2. **FinanceUser** (Weight: 2)
   - Report generation
   - Analytics
   - Medium activity, 2-5s wait time

3. **BranchUser** (Weight: 5)
   - Requisition creation
   - Workflow tracking
   - Most common user type, 2-4s wait time

4. **GeneralUser** (Weight: 3)
   - Mixed activities
   - Dashboard viewing
   - Moderate usage, 1-5s wait time

### Task Categories

#### Dashboard Tasks (Weight: 10)
- View dashboard metrics
- Pending payments list
- Recent payments
- Active alerts

#### Requisition Workflow (Sequential)
1. Create requisition
2. Apply threshold
3. Resolve workflow
4. Check status

#### Payment Execution
- List pending payments
- Request OTP
- Check payment status

#### Alert Management
- List by severity
- Acknowledge alerts
- Resolve alerts

#### Reporting
- Payment summary reports
- Fund health reports
- Variance analysis

## Performance Targets

### Response Time SLAs

| Endpoint | Target (95th percentile) | Max Acceptable |
|----------|--------------------------|----------------|
| Dashboard Metrics | < 500ms | 1s |
| Pending Payments | < 1s | 2s |
| Create Requisition | < 800ms | 1.5s |
| Payment Execution | < 2s | 3s |
| Reports | < 3s | 5s |

### Throughput Targets

- **Dashboard**: Support 500 concurrent users
- **Requisition Creation**: 50 requests/second
- **Payment Execution**: 20 requests/second
- **Reports**: 10 requests/second

### Reliability Targets

- Error rate < 1%
- No timeouts under normal load
- Graceful degradation under peak load

## Test Execution Examples

### Smoke Test (Light Load)
```powershell
locust -f load_tests\locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 2m --headless
```

### Load Test (Expected Peak)
```powershell
locust -f load_tests\locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 10m --headless
```

### Stress Test (Beyond Capacity)
```powershell
locust -f load_tests\locustfile.py --host=http://localhost:8000 --users 500 --spawn-rate 25 --run-time 5m --headless
```

### Endurance Test (Sustained Load)
```powershell
locust -f load_tests\locustfile.py --host=http://localhost:8000 --users 50 --spawn-rate 5 --run-time 30m --headless
```

## Analyzing Results

### Key Metrics to Monitor

1. **Response Times**
   - Median
   - 95th percentile
   - 99th percentile
   - Max

2. **Request Rates**
   - Requests per second (RPS)
   - Failures per second

3. **Error Rates**
   - Total failures
   - Failure types
   - Error messages

4. **Resource Utilization**
   - CPU usage
   - Memory usage
   - Database connections
   - Network bandwidth

### Expected Output

```
Type     Name                           # reqs      # fails |    Avg     Min     Max    Med |   req/s
--------|-----------------------------|-----------|---------|-------|-------|-------|-------|--------
GET      Dashboard: Metrics                1000     0(0.00%) |    245      89     876    220 |   16.67
GET      Dashboard: Pending Payments        500     0(0.00%) |    567     234    1234    520 |    8.33
POST     Workflow: Create Requisition       200     2(1.00%) |    432     198     987    410 |    3.33
GET      Alerts: Critical                   300     0(0.00%) |    189      76     543    180 |    5.00
--------|-----------------------------|-----------|---------|-------|-------|-------|-------|--------
         Aggregated                        2000     2(0.10%) |    358      76    1234    310 |   33.33
```

## Troubleshooting

### High Error Rates
- Check database connection pool size
- Review application logs
- Monitor database slow queries
- Check API rate limiting

### Slow Response Times
- Enable query profiling
- Check for N+1 queries
- Review database indexes
- Consider caching strategy

### Connection Errors
- Increase server worker processes
- Check firewall/load balancer settings
- Review connection timeouts
- Monitor network latency

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Load Tests
  run: |
    pip install locust
    locust -f load_tests/locustfile.py --host=${{ secrets.STAGING_URL }} --users 50 --spawn-rate 5 --run-time 3m --headless --csv=load_test_results
```

## Best Practices

1. **Start Small**: Begin with 10-20 users and gradually increase
2. **Monitor Resources**: Watch CPU, memory, database during tests
3. **Test Realistic Scenarios**: Match actual user behavior patterns
4. **Run Regularly**: Include in CI/CD pipeline
5. **Document Baselines**: Track performance over time
6. **Test Before Deploy**: Run load tests on staging before production releases

## Next Steps

After load testing:
1. Review results against SLAs
2. Identify performance bottlenecks
3. Optimize slow endpoints
4. Add database indexes where needed
5. Implement caching for hot paths
6. Re-test after optimizations
