# Local development image (production runs on Vercel).
# Nuxt 4 needs Node 22.22+ or 24, see .nvmrc
FROM node:24

WORKDIR /app

COPY package*.json ./
# Skip postinstall (`nuxt prepare`): nuxt.config.ts is not copied yet. `nuxt dev` runs it anyway.
RUN npm ci --ignore-scripts

COPY . .

# --host 0.0.0.0 so the dev server is reachable from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
