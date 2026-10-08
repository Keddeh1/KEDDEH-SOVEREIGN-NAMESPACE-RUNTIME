CREATE TABLE IF NOT EXISTS `experience_records` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text,
	`user_id` text,
	`created_at` text,
	`digest` text,
	`document` text
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS `experience_transport_probes` (
	`id` text PRIMARY KEY NOT NULL,
	`digest` text
);
--> statement-breakpoint
CREATE TABLE `media_assets` (
	`id` text PRIMARY KEY NOT NULL,
	`actor` text NOT NULL,
	`name` text NOT NULL,
	`kind` text NOT NULL,
	`mime` text NOT NULL,
	`bytes` integer NOT NULL,
	`object_key` text NOT NULL,
	`sha256` text NOT NULL,
	`created_at` text NOT NULL,
	`document` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `media_connections` (
	`id` text PRIMARY KEY NOT NULL,
	`document` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `media_edits` (
	`id` text PRIMARY KEY NOT NULL,
	`asset_id` text NOT NULL,
	`created_at` text NOT NULL,
	`document` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `media_jobs` (
	`id` text PRIMARY KEY NOT NULL,
	`kind` text NOT NULL,
	`status` text NOT NULL,
	`due_at` text NOT NULL,
	`lease` text,
	`created_at` text NOT NULL,
	`updated_at` text NOT NULL,
	`document` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_media_jobs_status_due` ON `media_jobs` (`status`,`due_at`);--> statement-breakpoint
CREATE TABLE `media_oauth_states` (
	`id` text PRIMARY KEY NOT NULL,
	`actor` text NOT NULL,
	`expires_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `media_uploads` (
	`id` text PRIMARY KEY NOT NULL,
	`actor` text NOT NULL,
	`document` text NOT NULL,
	`updated_at` text NOT NULL
);
