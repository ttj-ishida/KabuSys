# Keep a Changelog — KabuSys

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
このリポジトリの初期リリースに相当する変更履歴をコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-17
初回公開リリース（推定）。以下の主要機能と設計上の決定を含みます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化情報を追加（kabusys.__version__ = "0.1.0"、主要サブモジュールを公開）。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml により決定）により、実行カレントディレクトリに依存しない自動 .env ロードを実装。
  - .env/.env.local の優先読み込み（OS 環境変数を保護、.env.local は上書き可能）。
  - .env パース対応：コメント行、export プレフィックス、クォート、エスケープ、インラインコメント処理を考慮。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - 必須環境変数取得ヘルパー _require() と Settings クラスを提供。主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本機能: 日足（OHLCV）、四半期財務データ、マーケットカレンダーを取得する fetch_... 関数を実装。
  - 認証: refresh token から id token を取得する get_id_token() を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装。
  - 再試行ロジック: 指数バックオフ、最大リトライ回数 3 回（408/429/5xx 対応）。429 の場合は Retry-After ヘッダを優先。
  - 401 応答時は id_token を自動リフレッシュして一度だけ再試行（無限再帰防止）。
  - ページネーション対応（pagination_key を追跡して重複防止）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT DO UPDATE を利用して上書き可能。
  - 型変換ユーティリティ _to_float / _to_int を実装（安全な parse を行い、不正値は None に）。
  - 取得時刻（fetched_at）を UTC ISO8601 で記録し、Look-ahead Bias のトレースを容易に。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news テーブルへ保存する機能を実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: URL スキーム検証 (http/https のみ)、リダイレクト先のスキーム/ホスト検査、プライベート IP 判定（DNS 解決含む）で内部ネットワークアクセスを拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 受信時の Content-Length 事前チェックと実際読み込みバイト数の検証。
  - トラッキングパラメータ除去と URL 正規化:
    - utm_*、fbclid、gclid などのパラメータを削除しクエリをソートして正規化。
    - 正規化 URL の SHA-256（先頭32文字）で記事 ID を生成し冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化、先頭末尾トリムを実施。
  - DB 保存:
    - raw_news へのバルク INSERT をチャンク化して実行し、INSERT ... RETURNING で新規挿入 ID を返す。
    - news_symbols に対する一括挿入（重複除去、ON CONFLICT DO NOTHING、チャンク）、および単独ニュースの紐付け関数を実装。
  - 銘柄抽出:
    - 正規表現ベースで 4 桁銘柄コードを抽出し、与えられた known_codes セットと照合して候補を返す。
  - デフォルト RSS ソースとして Yahoo Finance を登録。
- DuckDB スキーマ (kabusys.data.schema)
  - Data Platform の 3 層（Raw / Processed / Feature / Execution）に基づくテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約、型チェック、PRIMARY KEY、FOREIGN KEY、CHECK 制約を多用してデータ整合性を担保。
  - インデックス定義（頻出クエリ向け）を追加。
  - init_schema(db_path) によりディレクトリ自動作成→全DDL 実行→接続を返すユーティリティを提供。get_connection() で既存 DB へ接続可能。
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新戦略を採用した ETL ヘルパー群を提供:
    - DB 最終取得日取得関数（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 営業日調整ヘルパー (_adjust_to_trading_day)。
    - run_prices_etl: 差分取得、backfill（デフォルト 3 日）対応、取得→保存フローを実装（fetch_daily_quotes / save_daily_quotes を利用）。
  - ETL 結果を表す ETLResult データクラスを実装（品質チェック結果とエラー一覧を含む）。
  - 設計方針: 品質チェックは重大エラーを検出しても ETL 全体を止めず呼び出し元での判断を促す（Fail-Fast ではない）。
  - 配置可能な定数: 最小データ日付（2017-01-01）、カレンダー先読み日数 90 日など。

### セキュリティ (Security)
- XML パーシングに defusedxml を採用し XML 関連攻撃を軽減。
- RSS フェッチ時に SSRF 対策を組み込み（スキーム検査、プライベート IP 判定、リダイレクト先検査）。
- ネットワーク取得に対してタイムアウト・レスポンスサイズ制限・gzip 解凍後チェックを導入。
- 環境変数読み込みにおいて OS 環境変数を保護する仕組みを導入（.env が OS 環境を容易に上書きしない）。

### 変更 (Changed)
- 初期リリースにつき該当なし（初回実装を記載）。

### 修正 (Fixed)
- 初期リリースにつき該当なし（初回実装を記載）。

### 互換性と移行ノート (Notes / Migration)
- データベース:
  - 初回は init_schema(db_path) を実行して DuckDB スキーマを作成してください（":memory:" 可）。
  - 既存 DB がある場合、スキーマ変更のマイグレーションは本リリースに含まれません。
- 環境変数:
  - 必須の環境変数 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) を事前に設定してください。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- API 利用制限:
  - J-Quants API のレート制限 (120 req/min) をアプリケーション側で順守する実装がありますが、運用時には更なる制御（並列処理の抑制等）を検討してください。

### 既知の制限 (Known limitations)
- ETL の完全な品質チェックモジュール（quality）が別モジュールとして設計されているが、本リリースに含まれる関数は外部 quality モジュールとの統合を前提としています（詳細は実装参照）。
- ニュース記事の ID は正規化 URL ベースだが、サイト側の大幅な URL 変更や非 URL GUID に対しては挙動が限定されます。
- 一部ネットワーク/HTTP エラーに対する挙動は logging に依存しており、運用監視の設定が必要です。

---

開発・運用上の詳細は各モジュールの docstring とコードコメントを参照してください。リリース以降の修正・機能追加はこの CHANGELOG に追記してください。