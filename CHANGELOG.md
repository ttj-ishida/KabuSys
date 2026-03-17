# CHANGELOG

すべての重要な変更をこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。  

リリースの種類は以下を使用します: Added, Changed, Fixed, Security。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-17
初回公開リリース。

### Added
- 基本パッケージとエントリポイントを追加
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = 0.1.0）と公開サブパッケージを定義（data, strategy, execution, monitoring）。

- 環境設定・ロード機能を追加（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装（.git または pyproject.toml を基準に探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env の行パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の環境変数取得とバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - Path オブジェクトでの DB パス取得（duckdb/sqlite）をサポート。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得のための fetch_* 関数を実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライロジック（指数バックオフ、最大3回）を実装。408/429/5xx を対象に再試行し、429 の場合は Retry-After を考慮。
  - 401 受信時はリフレッシュトークンから id_token を再取得して1回リトライ（無限再帰防止のため allow_refresh 制御）。
  - データ取得時に fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias を抑制。
  - DuckDB へ冪等に保存する save_* 関数を提供（ON CONFLICT DO UPDATE による重複更新）。
  - 型変換ユーティリティ（_to_float / _to_int）を導入し、不正値の扱いを明確化。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news, news_symbols へ保存する処理を実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ及び頑健性設計を多数導入:
    - defusedxml による XML パース（XML Bomb 等への対策）。
    - SSRF 対応: HTTP リダイレクト時のスキーム検証、ホストがプライベートアドレスでないか検査（DNS 解決及び IP 判定）。
    - URL スキームの制限（http/https のみ）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去（utm_ 等）と URL 正規化による記事ID（SHA-256 の先頭32文字）生成で冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）、タイトル優先・content:encoded 優先の抽出。
  - DB への保存はチャンク化してトランザクション内で一括 INSERT（INSERT ... RETURNING を利用）し、実際に挿入された ID / 件数を返す。
  - 銘柄コード抽出ロジック（4桁数字の抽出、既知銘柄セットでフィルタ、重複除去）。
  - run_news_collection により複数ソースを順次処理し、個別ソースの失敗は他ソースに影響しない設計。

- DuckDB スキーマ定義と初期化を追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義を全面実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義してデータ整合性を担保。
  - 頻出クエリ向けのインデックスを追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ作成 → 接続 → DDL 実行 → インデックス作成を行い、冪等に初期化を行う API を提供。
  - get_connection(db_path) で既存 DB への接続を取得。

- ETL パイプラインの基盤を追加（src/kabusys/data/pipeline.py）
  - 差分更新（差分ETL）メカニズムを実装するためのユーティリティ（最終取得日の取得、テーブル存在確認、取引日の調整ロジック）。
  - run_prices_etl 等の個別 ETL ジョブを開始（差分更新、backfill_days による再取得、_MIN_DATA_DATE の扱い、jquants_client と連携して保存）。
  - ETLResult データクラスを実装し、ETL 結果（フェッチ数・保存数・品質問題リスト・エラーリスト）を管理。品質チェックの出力（quality_issues）を辞書化する to_dict を提供。
  - 品質チェック連携ポイントを確保（quality モジュール呼び出しを想定）。

- パッケージ構造のプレースホルダを追加
  - src/kabusys/execution, src/kabusys/strategy, src/kabusys/data/__init__.py を作成（将来の実装用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector において SSRF 対策、defusedxml による安全な XML パース、最大受信バイト数チェック、gzip 解凍後のサイズ検証など、外部フィード処理に伴う攻撃ベクトルを軽減する対策を実装。
- .env 読み込み時に OS 環境を保護するため protected キー群を扱い、既存 OS 環境変数を上書きしないデフォルト挙動を採用。

---

注記:
- 本 CHANGELOG はソースコードから推測して作成しています。内部実装の詳細や未公開の仕様・依存モジュール（例: quality モジュールの具体実装など）により、実際のリリースノートとは差異が生じる可能性があります。必要に応じて追記・修正してください。