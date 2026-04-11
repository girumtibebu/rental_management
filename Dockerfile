# Custom Frappe/ERPNext image with rental_management app included.
# Build argument lets you pin to a specific ERPNext release tag.
ARG ERPNEXT_VERSION=v15
FROM frappe/erpnext:${ERPNEXT_VERSION}

USER frappe
WORKDIR /home/frappe/frappe-bench

# Copy the rental_management app source into the bench apps directory.
COPY --chown=frappe:frappe . apps/rental_management/

# Install the app into the bench Python virtual environment so that
# Frappe can discover and import it at runtime.
RUN ./env/bin/pip install --no-cache-dir -e apps/rental_management
