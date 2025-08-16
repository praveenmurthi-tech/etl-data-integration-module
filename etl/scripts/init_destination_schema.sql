-- Destination: Sales
CREATE TABLE IF NOT EXISTS public.sales (
  sale_id           UUID PRIMARY KEY,
  customer_id       UUID,
  product_id        UUID,
  sale_date         DATE,
  sale_amount       DECIMAL(12,2),
  sale_currency     VARCHAR(3),
  quantity_sold     INT,
  salesperson_name  VARCHAR(100),
  region            VARCHAR(50),
  payment_mode      VARCHAR(50),
  tax_amount        DECIMAL(12,2),
  discount_amount   DECIMAL(12,2),
  net_amount        DECIMAL(12,2),
  created_at        TIMESTAMP,
  updated_at        TIMESTAMP
);

-- Destination: Services
CREATE TABLE IF NOT EXISTS public.services (
  service_id         UUID PRIMARY KEY,
  customer_id        UUID,
  service_date       DATE,
  service_type       VARCHAR(50),
  service_amount     DECIMAL(12,2),
  service_currency   VARCHAR(3),
  technician_name    VARCHAR(100),
  service_status     VARCHAR(50),
  service_duration   INT,
  parts_used         TEXT,
  warranty_applied   BOOLEAN,
  follow_up_required BOOLEAN,
  remarks            TEXT,
  created_at         TIMESTAMP,
  updated_at         TIMESTAMP
);
