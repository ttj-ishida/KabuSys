CHANGELOG
=========

すべての重要な変更点を文書化します。フォーマットは Keep a Changelog に準拠しています。
リリース方針: SemVer を想定。初期リリースは v0.1.0 として記載しています。

なお、本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際のコミット履歴に基づくものではありません。

テンプレート
-----------
- [Unreleased] - 未リリースの変更
- [0.1.0] - 初回リリース

[Unreleased]
------------
（現状、未リリースの変更はありません）

0.1.0 - 2026-03-18
-----------------

Added
- 基本パッケージ構成を導入
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py にて __version__ を定義)
  - サブパッケージ/モジュールのスケルトン: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
    - OS 環境変数を保護する protected ロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサを実装（コメント、export 句、クォートおよびエスケープ対応、インラインコメントの取り扱いなど）。
  - 必須設定取得ヘルパー _require と、よく使う設定プロパティを提供:
    - J-Quants 関連: jquants_refresh_token
    - kabuステーション API: kabu_api_password, kabu_api_base_url
    - Slack: slack_bot_token, slack_channel_id
    - DB: duckdb_path, sqlite_path
    - システム: env (development/paper_trading/live の検証), log_level（検証）、is_live/is_paper/is_dev フラグ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API の基本操作を実装:
    - ID トークン取得 (get_id_token)
    - 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、市場カレンダー（fetch_market_calendar）の取得（ページネーション対応）
  - 設計上の特徴:
    - 固定間隔スロットリングによるレート制限（120 req/min）を厳守する RateLimiter を実装
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
    - 401 受信時はトークン自動リフレッシュを 1 回行いリトライ（無限再帰防止のフラグあり）
    - fetched_at を UTC ISO 形式で記録し Look-ahead Bias を軽減
    - DuckDB への保存は冪等性を保つ（INSERT ... ON CONFLICT DO UPDATE）

  - DuckDB 保存ユーティリティ:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装（PK 欠損行のスキップ・ログ出力、保存件数ログあり）
    - 型変換ユーティリティ _to_float / _to_int を提供（安全な変換、空値や不正値の扱い）

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを収集して DuckDB に保存するフローを実装
  - 主要な機能:
    - RSS 取得と XML パース（defusedxml を用いて XML Bomb 等に対処）
    - URL 正規化 (トラッキングパラメータ除去、スキーム・ホスト小文字化、クエリのソート、フラグメント除去)
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - リダイレクト時のスキーム・ホスト検査（_SSRFBlockRedirectHandler）
      - ホストがプライベート/ループバック/リンクローカルかを判定し拒否
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）
    - 前処理: URL 除去、空白正規化（preprocess_text）
    - DB 書き込み:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて実際に挿入された記事IDを返す（チャンク/トランザクション化）
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク保存（重複排除、チャンク、トランザクション）
    - 銘柄コード抽出（extract_stock_codes）: 4桁の数字パターンを検出し known_codes に存在するもののみ採用

  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを定義（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataPlatform.md に基づく 3 層（Raw / Processed / Feature）＋Execution のテーブル定義を実装
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・型・チェック（CHECK、PRIMARY KEY、外部キー）を明示
  - 頻出クエリに備えたインデックス定義を追加
  - init_schema(db_path) で初期化（:memory: をサポート、親ディレクトリ自動作成、冪等性）
  - get_connection(db_path) で既存 DB へ接続（スキーマ初期化は行わない）

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL 基盤を実装（設計: 差分取得、保存、品質チェック）
  - ETLResult データクラスを導入（ターゲット日付、取得/保存件数、品質問題、エラーリストを保持）
  - 差分取得ユーティリティ:
    - テーブル存在チェック、最大日付取得ヘルパー
    - 市場カレンダーを参照して非営業日を直近営業日へ調整する _adjust_to_trading_day
    - raw_prices / raw_financials / market_calendar の最終取得日取得関数
  - run_prices_etl の骨組みを実装:
    - date_from 自動算出（最終取得日 - backfill_days、未取得時は _MIN_DATA_DATE）
    - J-Quants から差分取得し、jq.save_daily_quotes による保存
    - （品質チェックモジュール quality と連携する設計を想定）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- RSS パーサに defusedxml を採用し XML 実行攻撃系へ対処
- SSRF 対策（スキームチェック、プライベートIP/ホスト検出、リダイレクト検査）
- .env 読み込み時に OS 環境変数を保護（protected set）

Notes / Migration
- DB 初期化:
  - init_schema() は親ディレクトリを自動生成します。既存 DB がある場合は上書きせず既存テーブルは維持されます。
  - テスト目的でインメモリ DB を使用する際は db_path に ":memory:" を渡してください。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の _require で未設定時に ValueError）
  - 自動 .env 読み込みを避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ETL:
  - run_prices_etl の date_from/backfill_days の挙動により後出し修正を吸収できます（デフォルト backfill_days=3）。

Known issues / Warnings
- run_prices_etl の戻り値に関する潜在的な不整合:
  - 提供されたコード中の run_prices_etl の末尾に "return len(records)," のように見える箇所があり、保存件数(saved) を返すべき箇所が不完全に見えます。実運用前に戻り値が (fetched_count, saved_count) の形で正しく返ることを確認してください。
- strategy, execution, monitoring サブパッケージは現状ほぼ空のイニシャライザのみで、対応ロジックは未実装です。
- quality モジュールは参照されているが、提供コード内に実装が含まれていない可能性があります（ETL の品質チェック機能を利用する場合は quality モジュール実装を確認してください）。

開発者向けメモ
- テスト容易性:
  - news_collector._urlopen をモックしてネットワーク依存を切り離せます。
  - jquants_client の _get_cached_token はトークン注入に対応しており、id_token を引数で与えてテストしやすく設計されています。
- ロギング:
  - 各主要関数は情報/警告ログを出力するため、運用時の可観測性を確保しています。
- トランザクション:
  - news_collector の DB 書き込みはトランザクションでまとめており、失敗時にはロールバックします。

クレジット
- この CHANGELOG は提供されたコードベースの内容から推測して作成しました。実際の変更履歴やコミットメッセージと異なる点がある場合があります。必要であれば実コミット履歴を渡してください。