CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（現在のリリースは 0.1.0 のため Unreleased は空です）

[0.1.0] - 2026-03-17
-------------------

### Added
- 新規パッケージ "KabuSys" を初版として追加。
  - パッケージバージョン: 0.1.0
  - パッケージ概要: 日本株自動売買システムの基盤ライブラリ（データ収集、ETL、スキーマ、ニュース収集、設定管理など）。

- 環境設定管理モジュール（kabusys.config）を追加。
  - .env ファイルと環境変数からの設定読み込みをサポート。
  - 自動ロード戦略: OS 環境変数 > .env.local > .env（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 読み込み時の上書き制御（override / protected）を実装。
  - 必須変数取得用 _require と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と is_live/is_paper/is_dev のヘルパー。

- J-Quants API クライアント（kabusys.data.jquants_client）を追加。
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得機能。
  - レート制限遵守: 固定間隔スロットリングで 120 req/min を保証（内部 RateLimiter）。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。
  - 401 応答時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
  - ページネーション対応（pagination_key の追跡）。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で実装。
  - 型変換ユーティリティ (_to_float / _to_int) を実装し不正値に対処。

- ニュース収集モジュール（kabusys.data.news_collector）を追加。
  - RSS フィードから記事を収集し raw_news テーブルへ保存する機能。
  - 記事ID はトラッキングパラメータ除去後の正規化 URL を SHA-256（先頭32 chars）でハッシュ化して生成し冪等性を確保。
  - defusedxml を用いた XML パース（XML Bomb 対策）。
  - SSRF 対策:
    - URL スキーム検証（http / https のみ許可）。
    - リダイレクトハンドラでリダイレクト先のスキームとホスト/IP を検査。
    - プライベート/ループバック/リンクローカル/マルチキャストのホストをブロック。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去とクエリパラメータソートによる URL 正規化。
  - テキスト前処理（URL 除去・空白正規化）のユーティリティ。
  - 銘柄コード抽出（4桁数字パターン）と既知コードフィルタリング。
  - DB 保存はチャンク化とトランザクションでまとめて行い、INSERT ... RETURNING を使用して実際に挿入された件数を返却。
  - news_symbols の一括保存機能（重複除去・チャンク挿入）。

- DuckDB スキーマ定義と初期化モジュール（kabusys.data.schema）を追加。
  - Raw / Processed / Feature / Execution の多層スキーマを定義：
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの整合性制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - 頻出クエリ向けインデックスを用意（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) により親ディレクトリ自動作成＋DDL/インデックスを順序に従って冪等で実行。get_connection() も提供。

- ETL パイプライン基盤（kabusys.data.pipeline）を追加（初期実装）。
  - 差分更新の方針（最小取得日、backfill_days による再取得、カレンダー先読み）。
  - ETLResult dataclass により ETL 結果・品質問題・エラーを集約して返却。
  - DB の最終取得日取得ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 市場カレンダーを用いた営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl を含む差分 ETL ジョブ（差分算出、J-Quants からの取得、保存、ログ出力）。（設計: id_token を注入可能でテスト容易性を確保）

### Security
- RSS/ネットワーク部分のセキュリティ強化:
  - defusedxml による XML パース（XML パース攻撃対策）。
  - SSRF 対策（スキーム検証、リダイレクト検査、プライベート IP 検出）。
  - レスポンス最大バイト数制限と gzip 解凍後のサイズ検査。
- 環境変数ロード時の保護（OS 環境変数を protected として .env による上書きを制限）。

### Notes
- 多くの保存処理は冪等性を保証する（ON CONFLICT DO UPDATE / DO NOTHING）ため、再実行・リトライに耐性がある設計です。
- J-Quants API クライアントは 120 req/min に対するスロットリングとリトライを組み合わせ、401 時の自動トークン刷新を行います。
- ETL ジョブは品質チェックモジュール（kabusys.data.quality）との連携を想定しており、品質問題を収集して ETLResult に格納します（品質チェック自体は別モジュール実装）。
- run_news_collection 等の収集ジョブは個々のソースで独立したエラーハンドリングを行い、1 ソースの失敗が他に波及しないように設計されています。

### Fixed
- 初版のため該当なし。

### Changed / Deprecated / Removed
- 初版のため該当なし。

既知の制限 / TODO
- ETL パイプラインは基本的な差分取得と保存を実装しているが、品質チェック（quality モジュール）や上位のスケジューラ／監視連携は別実装。
- 一部のユーティリティやジョブは将来的に細かなパラメータの公開やログ改善、メトリクス収集を追加予定。

作者
----
（リポジトリのコミット履歴に基づく初回リリース）