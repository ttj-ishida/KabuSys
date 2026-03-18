# Changelog

すべての変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点ではリリース版は 0.1.0 のみ。今後の変更はここに追記します。）

---

## [0.1.0] - Initial release

最初の公開リリース。日本株自動売買システム (KabuSys) の基盤機能を実装。

### Added

- パッケージ骨格
  - パッケージエントリポイント src/kabusys/__init__.py にバージョン情報と公開モジュールリストを追加（__version__ = "0.1.0"）。
  - 空のサブパッケージインターフェースを用意（execution, strategy, data 等）。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local からの自動読み込み機能を実装（読み込み優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。
  - 読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途等）。
  - .env パーサー: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント扱い、コメント・空行スキップ等に対応。
  - Settings クラスを導入し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトを data/ 以下に設定）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev のブールヘルパー

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - データ取得対象:
    - 株価日足 (OHLCV)
    - 財務データ（四半期 BS/PL）
    - JPX マーケットカレンダー
  - 実装の主な特徴:
    - API レート制限を守る固定間隔スロットリング（120 req/min、_RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 発生時の自動トークンリフレッシュ（1 回だけ）とトークンキャッシュ共有（ページネーション対応）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
    - データ整形ユーティリティ: _to_float / _to_int、fetched_at の UTC 記録など。
    - 詳細なログ出力を実装（取得件数・スキップ行の警告等）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news / news_symbols へ保存する実装。
  - セキュリティ・堅牢性設計:
    - defusedxml を利用して XML Bomb 等の攻撃を防止。
    - SSRF 対策: URL スキームチェック（http/https 限定）、ホストがプライベート/ループバック等でないか検査、リダイレクト時も検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）を除去した URL 正規化、SHA-256（先頭32文字）による記事 ID 生成で冪等性を確保。
    - URL の検証・前処理（_validate_url_scheme, _is_private_host, preprocess_text）。
  - 機能:
    - fetch_rss: RSS の取得とパース（名前空間や非標準レイアウトへのフォールバック対応）。
    - save_raw_news: DuckDB へのバルク挿入（チャンク分割、トランザクション、ON CONFLICT DO NOTHING、INSERT ... RETURNING で新規挿入 ID を返す）。
    - save_news_symbols / _save_news_symbols_bulk: 記事 - 銘柄コード紐付けの保存（重複排除、チャンク挿入、トランザクション）。
    - extract_stock_codes: テキスト中の 4 桁銘柄コード抽出（既知コードセットによるフィルタ、重複除去）。
    - run_news_collection: 複数 RSS ソースからの収集ジョブ、ソース毎に個別エラーハンドリング、既知銘柄での紐付け処理。

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md に基づいた 3 層（Raw / Processed / Feature）＋Execution レイヤーのテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約・チェック (PRIMARY KEY, CHECK 句、外部キー) を含む DDL を定義。
  - 頻出クエリ向けのインデックス定義を追加。
  - init_schema(db_path) でディレクトリ作成（必要時）→ DuckDB 接続 → DDL/インデックスを実行して初期化（冪等）。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETL の設計方針に基づいた差分更新ワークフローの基礎を実装。
  - ETLResult dataclass を導入し、各 ETL 実行の集計（取得件数・保存件数・品質問題・エラー）を保持。has_errors / has_quality_errors / to_dict を提供。
  - テーブル存在確認や最大日付取得のユーティリティ (_table_exists, _get_max_date) を実装。
  - 市場カレンダーに基づく営業日調整ヘルパー (_adjust_to_trading_day) を実装（最大 30 日遡りのフォールバック）。
  - 差分更新ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - 個別 ETL ジョブの実装例: run_prices_etl
    - 最終取得日ベースの差分計算（backfill_days による再取得）、J-Quants からの取得→保存の流れ。
    - J-Quants クライアント (jq) との連携を考慮し、id_token を注入可能に設計。
  - 品質チェックは quality モジュールを参照する設計（quality モジュールのインターフェースを想定）。

### Security

- ニュース収集において SSRF や XML 攻撃、Gzip Bomb に対する複数の防御を実装。
- .env 読み込みでは OS 環境変数を保護するための protected set を考慮して上書き制御を行う。

### Other

- 型ヒント（PEP 484 / 604 等）や詳細なドキュメンテーション文字列（docstring）を広範囲に追加し、テストや保守性を考慮した設計。
- ロガーを各モジュールに導入し、重要なイベント（取得件数・スキップ・例外）を出力する設計。

---

メモ / 今後の課題（実装から推測）
- pipeline モジュールは品質チェック（quality）や他の ETL ジョブ（financials, calendar）の統合部分が想定されているが、全機能の実装が未完または別モジュールに分かれている可能性がある。
- execution / strategy サブパッケージは現状インターフェースのみで、具体的な発注ロジック・戦略実装は今後追加予定。
- 単体テスト・統合テスト用のテストケースや CI 設定はコードからは確認できないため、テスト整備が必要。