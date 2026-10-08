import {sqliteTable,text,integer,index} from 'drizzle-orm/sqlite-core';
export const mediaAssets=sqliteTable('media_assets',{id:text('id').primaryKey(),actor:text('actor').notNull(),name:text('name').notNull(),kind:text('kind').notNull(),mime:text('mime').notNull(),bytes:integer('bytes').notNull(),objectKey:text('object_key').notNull(),sha256:text('sha256').notNull(),createdAt:text('created_at').notNull(),document:text('document').notNull()});
export const mediaEdits=sqliteTable('media_edits',{id:text('id').primaryKey(),assetId:text('asset_id').notNull(),createdAt:text('created_at').notNull(),document:text('document').notNull()});
export const mediaJobs=sqliteTable('media_jobs',{id:text('id').primaryKey(),kind:text('kind').notNull(),status:text('status').notNull(),dueAt:text('due_at').notNull(),lease:text('lease'),createdAt:text('created_at').notNull(),updatedAt:text('updated_at').notNull(),document:text('document').notNull()},t=>[index('idx_media_jobs_status_due').on(t.status,t.dueAt)]);
export const mediaConnections=sqliteTable('media_connections',{id:text('id').primaryKey(),document:text('document').notNull(),updatedAt:text('updated_at').notNull()});
export const mediaOAuthStates=sqliteTable('media_oauth_states',{id:text('id').primaryKey(),actor:text('actor').notNull(),expiresAt:text('expires_at').notNull()});

export const mediaUploads=sqliteTable('media_uploads',{id:text('id').primaryKey(),actor:text('actor').notNull(),document:text('document').notNull(),updatedAt:text('updated_at').notNull()});

export const mediaScripts=sqliteTable('media_scripts',{id:text('id').primaryKey(),assetId:text('asset_id'),createdAt:text('created_at').notNull(),document:text('document').notNull()});
