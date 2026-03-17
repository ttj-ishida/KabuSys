# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在のリポジトリ状態は v0.1.0 として最初にリリース済みの内容を反映しています。今後の変更はここに追記してください。）

---

## [0.1.0] - 2026-03-17

初回リリース。本リリースでは日本株自動売買システムのコアとなる設定管理、データ収集・保存、スキーマ定義、ETLパイプライン、ニュース収集基盤などを実装しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージを追加。バージョンは `0.1.0`。
  - public API: `kabusys.{data, strategy, execution, monitoring}` を __all__ に定義（strategy/execution/monitoring は初期状態で空のパッケージ）。

- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env 読み込み:
    - プロジェクトルートを .git または pyproject.toml で検出して `.env` / `.env.local` を自動ロード。
    - OS 環境変数を保護しつつ `.env.local` で上書き可能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト向け）。
  - .env パーサー:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどを考慮した堅牢なパース。
  - 必須環境変数取得メソッド `_require` と、環境の検証（KABUSYS_ENV / LOG_LEVEL の検証）を追加。
  - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 株価日足・財務データ・市場カレンダーの取得（ページネーション対応）を実装。
  - レートリミッター（120 req/min）を実装して固定間隔スロットリングで API 呼び出しを制御。
  - リトライロジック:
    - 指数バックオフ、最大 3 回。対象ステータスコード（408/429/5xx）を想定。
    - 429 の場合は `Retry-After` ヘッダを優先。
  - 認証処理:
    - リフレッシュトークンから ID トークンを取得する `get_id_token`。
    - 401 受信時にトークンを自動リフレッシュして 1 回リトライする仕組み。
    - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - DuckDB へ保存するユーティリティ（冪等実装）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`：ON CONFLICT による更新で重複を排除。
    - 保存時に `fetched_at` を UTC ISO 8601 形式で記録し、取得時点をトレース可能に。
  - データ変換ユーティリティ `_to_float` / `_to_int` を実装し、入力の堅牢な正規化を行う。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を取得して raw_news に保存する実装。
  - セキュリティおよび堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等への耐性）。
    - HTTP/HTTPS スキームのみ許可し、SSRF 対策のためリダイレクト先やホストのプライベートアドレス判定を行うカスタムリダイレクトハンドラ。
    - レスポンス上限（MAX_RESPONSE_BYTES=10MB）を設定し、受信サイズ超過を防止。gzip 解凍後のサイズ検査も実施。
    - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）、記事IDは正規化URLの SHA-256 の先頭 32 文字で生成して冪等性を確保。
    - URL スキーマ検証やプライベートホスト検査で SSRF を防止。
  - テキスト前処理:
    - URL 除去、空白の正規化、先頭/末尾トリム（preprocess_text）。
  - DB 保存:
    - `save_raw_news` はチャンク分割 + トランザクション + `INSERT ... ON CONFLICT DO NOTHING RETURNING id` を利用し、実際に保存された新規 ID を返す。
    - `save_news_symbols` / `_save_news_symbols_bulk` により記事と銘柄コードの紐付けを一括で保存。
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字（日本株）を抽出し、既知の銘柄セットでフィルタリング（`extract_stock_codes`）。
  - 統合収集ジョブ `run_news_collection`:
    - 複数ソースを独立に処理し、1ソース失敗でも他ソースを継続。
    - 新規保存 ID に基づいて銘柄紐付けを行うフローを実装。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - Data Platform 設計に基づく多層スキーマを実装（Raw / Processed / Feature / Execution）。
  - 主なテーブル（抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - 利用頻度に応じたインデックスを作成（例: code×date、status、signal_id 等）。
  - `init_schema(db_path)`:
    - DB ファイルの親ディレクトリを自動作成し、DDL を順序に従って冪等的に作成して接続を返す。
    - `:memory:` のサポートあり。
  - `get_connection(db_path)` を提供（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計方針に従った差分更新の仕組みを実装。
  - ETLResult データクラス:
    - ETL 実行の集計（取得件数、保存件数、品質問題、エラー一覧）を保持。
    - 品質問題を辞書化して出力する `to_dict()` を提供。
  - 差分取得ユーティリティ:
    - テーブル存在確認、最大日付取得関数 `_table_exists`, `_get_max_date`。
    - 市場カレンダーを用いた直近営業日調整 `_adjust_to_trading_day`。
    - raw_prices / raw_financials / market_calendar の最終取得日を返すヘルパー `get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`。
  - 個別ジョブ `run_prices_etl`（差分更新、バックフィル対応）を実装（backfill_days デフォルト 3 日、最小データ日付を保護）。

### 変更 (Changed)
- なし（初回リリースのため、既存コードに対する変更履歴はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- ニュース収集処理で以下のセキュリティ対策を導入:
  - defusedxml による XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
  - レスポンスサイズ制限・gzip 解凍後検査によるメモリ DoS 対策。
  - DB 方面でも外部キー制約や CHECK 制約でデータ整合性を担保。

### パフォーマンス (Performance)
- API 呼び出しに対して固定間隔の RateLimiter を導入し、レート制限を順守。
- DuckDB へのバルク挿入をチャンク化してオーバーヘッドを低減（news_collector のチャンクサイズや schema のインデックス）。
- ニュースの銘柄紐付けは新規挿入記事のみを対象にバルクで一括保存。

### ドキュメント / その他
- 各モジュールにドキュメンテーション文字列（docstring）を豊富に追加し、設計方針・処理フロー・制約を明示。

---

注意:
- strategy / execution / monitoring パッケージは初期状態でプレースホルダ（__init__.py が存在）として用意されています。今後、注文ロジック、戦略実装、監視機能の追加が見込まれます。
- pipeline.run_prices_etl 等は ETL の一部実装を含みますが、品質チェックモジュール（kabusys.data.quality）など外部コンポーネントとの連携点は別途実装/統合が必要です。

もし CHANGELOG に追加したい「マイナーな実装詳細」や「リリース日付の変更」「パッケージのバージョニング規則」などの要望があれば教えてください。