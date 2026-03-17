# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]


## [0.1.0] - 2026-03-17
初回公開リリース。日本株の自動売買プラットフォーム「KabuSys」のコア機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージ構成プレースホルダ: data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む。
    - OS 環境変数を保護しつつ .env.local で上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env ファイルパーサを実装（export プレフィックス、クォート内エスケープ、インラインコメント等に対応）。
  - 必須設定取得用の _require()、環境名（development/paper_trading/live）・ログレベルの検証、DBパス（DUCKDB_PATH/SQLITE_PATH）などのプロパティを提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ:
    - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - リトライロジック（指数バックオフ、最大3回）を実装。408/429/5xx をリトライ対象。
    - 401 受信時はリフレッシュトークンで id_token を自動取得して 1 回だけ再試行。
    - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いた冪等性確保
  - データ変換ユーティリティ _to_float / _to_int を実装（不正値や小数切り捨て回避に配慮）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集/前処理/保存ワークフローを実装。
    - デフォルトソース: Yahoo ビジネス RSS を設定。
    - fetch_rss: RSS 取得 → XML パース → 記事抽出（title, description/content:encoded, pubDate）。
    - preprocess_text: URL 除去、空白正規化。
    - _normalize_url: トラッキングパラメータ（utm_* 等）除去・クエリソート・スキーム/ホスト小文字化。
    - _make_article_id: 正規化URL から SHA-256 の先頭32文字を記事IDとして生成（冪等性保証）。
  - セキュリティ・堅牢性向上機能:
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト時と最終 URL のスキーム/ホスト検証、プライベートIP 判定（DNS 解決含む）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査。
    - HTTP ヘッダでの Content-Length チェックと読み込みバイト数制限。
  - DuckDB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入IDを返却。チャンク処理でトランザクションを最適化。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存。INSERT ... RETURNING により実際に挿入された数を返す。
  - 銘柄コード抽出:
    - 4桁の数値パターン（例: 7203）から候補を抽出し、known_codes セットでフィルタ。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の 4 層データベーススキーマを定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各種制約（PRIMARY KEY、CHECK 等）と外部キーを定義。
  - インデックスを作成（頻出クエリ向けの code/date, status 等）。
  - init_schema(db_path) によりファイルパスの親ディレクトリ作成～DDL 実行を行い、接続を返す。get_connection は既存 DB への接続を返す。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult dataclass により ETL 実行結果 / 品質チェック結果 / エラーを集約。
  - 市場カレンダー参照による非営業日の調整ヘルパー _adjust_to_trading_day。
  - raw_* テーブルの最終取得日取得ユーティリティ（get_last_price_date 等）。
  - run_prices_etl の差分更新ロジック（最終取得日からの backfill をサポート、_MIN_DATA_DATE の初回ロード対応）、jq.fetch_daily_quotes と jq.save_daily_quotes を組み合わせて差分取得・保存を行う。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を採用し、XML 関連攻撃を軽減。
- RSS/HTTP取得に対して SSRF 対策を追加（スキーム検証、プライベートIP判定、リダイレクト検査）。
- .env の読み込みはプロジェクトルートベースで行い、OS 環境変数を上書きしない安全なデフォルトを採用。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の末尾が不完全（ソース断片で return が途中で終わっているように見える）。現在のソースは (len(records), ) のようにタプルが不完全に返される可能性があるため、呼び出し側での扱いに注意が必要（将来的に修正予定）。
- strategy/execution サブパッケージの __init__.py は現状プレースホルダで、戦略実装・発注ロジックは未実装。
- DuckDB に依存する箇所は実行環境に duckdb がインストールされている必要があります。
- J-Quants の API レートやエラー挙動は外部要因に依存するため、運用時にログとモニタリングを行ってください。

### マイグレーション / 初期セットアップ (Migration / Setup)
- 初回 DB 初期化: from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらは settings.<property> を参照すると _require により検証されます。
- 自動 .env ロードが不要なテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

今後の予定:
- run_prices_etl の返り値/エラーハンドリング修正、strategy/execution の実装、品質チェックモジュール（quality）の統合強化、監視/アラート機能の追加を予定しています。必要であれば優先度を検討して対応します。