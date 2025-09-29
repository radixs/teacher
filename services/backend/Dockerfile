# syntax=docker/dockerfile:1.6

FROM php:8.3-cli as base

# Install system dependencies required by Laravel
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        unzip \
        libzip-dev \
        libicu-dev \
        libpq-dev \
        libpng-dev \
        libonig-dev \
        libxml2-dev \
        libcurl4-openssl-dev \
    && docker-php-ext-install \
        intl \
        zip \
        pcntl \
        pdo \
        pdo_mysql \
        pdo_pgsql \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

WORKDIR /var/www/html

COPY app/composer.json app/composer.lock* ./

# Allow build-time dependency download (optional; fallback to runtime install in entrypoint)
RUN composer install --no-interaction --prefer-dist || true

COPY app ./

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV BACKEND_INTERNAL_PORT=8080

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
