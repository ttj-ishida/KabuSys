# CHANGELOG

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています（簡略化した日本語版）。

注: この履歴は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤機能群を追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py にてバージョン 0.1.0 を設定。
    - pakage の公開モジュール: data, strategy, execution, monitoring を列挙。

- 環境設定管理（src/kabusys/config.py）を追加:
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env/.env.local の読み込み順と上書きルールを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート）。
  - export KEY=val 形式やシングル/ダブルクォート、インラインコメント、エスケープ処理に対応した .env パーサーを実装。
  - OS 環境変数の上書き保護（protected keys）をサポート。
  - 設定オブジェクト Settings を提供（J-Quants トークン、kabu API、Slack、DBパス、環境名、ログレベルなど）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）と環境判定ユーティリティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）を追加:
  - API ベース URL、レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）。
  - 401 受信時の自動 id_token リフレッシュ処理（1 回のみ）とモジュールレベルの id_token キャッシュ共有。
  - JSON デコードエラー時の明示的エラー報告。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足・OHLCV）
    - fetch_financial_statements（四半期 BS/PL）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等性）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE により重複を排除し更新を可能に。
  - データ変換ユーティリティ（_to_float, _to_int）により不正値を安全に扱う。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias 対策設計。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加:
  - RSS フィードからのニュース収集（デフォルト: Yahoo Finance の business RSS）。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 等を防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査（DNS 解決と IP チェック）、リダイレクト時の事前検証用ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 受信ヘッダ Content-Length の事前チェック。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理（URL除去・空白正規化）。
  - DB への保存はトランザクションでまとめ、チャンク単位で INSERT RETURNING を使って実際に挿入されたレコードを返す:
    - save_raw_news, save_news_symbols, _save_news_symbols_bulk
  - 銘柄コード抽出（4桁数字パターン）と既知コードフィルタリング（extract_stock_codes）。
  - 全体収集ジョブ run_news_collection を提供（個々のソースで例外処理し続行する設計）。

- スキーマ定義と初期化（src/kabusys/data/schema.py）を追加:
  - DuckDB 用 DDL を包括的に定義（Raw / Processed / Feature / Execution 層）:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY、CHECK、外部キー）や型、安全性を考慮したカラム定義を反映。
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を提供し、親ディレクトリ自動作成と冪等的テーブル作成を実装。
  - get_connection(db_path) で既存 DB への接続を返すユーティリティを提供。

- ETL パイプライン基盤（src/kabusys/data/pipeline.py）を追加:
  - 差分更新ロジックと ETL の流れを実装（取得 → 保存 → 品質チェックの呼び出し想定）。
  - 定数: 最小データ開始日（2017-01-01）、カレンダー先読み日数、デフォルトバックフィル日数（3日）等。
  - ETL 実行結果を表す ETLResult dataclass（品質問題・エラーの集約、シリアライズ用 to_dict）。
  - テーブル存在確認・最大日付取得のヘルパー（_table_exists、_get_max_date）。
  - 市場カレンダー参照による営業日調整ヘルパー（_adjust_to_trading_day）。
  - 差分ETL の個別ジョブ雛形（例: run_prices_etl の骨子）を実装し、最終取得日からの差分取得や backfill を扱う。

Changed
- （初期リリースにつき該当なし。将来的な 0.1.x での改善を予定。）

Fixed
- （初期リリースにつき該当なし。）

Security
- XML パースに defusedxml を使用し安全性を強化。
- RSS フェッチでの SSRF 防止（スキーム検証、プライベートIP検査、リダイレクト検査）。
- ネットワーク受信・解凍サイズ制限（MAX_RESPONSE_BYTES）による DoS 耐性。

Notes / Implementation details
- 多くの DB 操作は DuckDB のプレースホルダ付き SQL を使用しており、ON CONFLICT / RETURNING を活用して冪等性と正確な変更数計測を行う設計。
- jquants_client の _request は urllib を使用した同期実装で、テスト容易性を考慮して id_token の注入や allow_refresh フラグを提供。
- news_collector は _urlopen をラップしており、テスト時にモック差し替えが可能。
- 日時は UTC に揃えて記録（fetched_at 等）、RSS pubDate は UTC naive に変換して保存する方針。

Deprecated
- なし

---

将来的な改善候補（コードから推測）
- 非同期 I/O（aiohttp 等）への移行による並列フェッチ性能改善。
- 詳細な品質チェックモジュール（quality）の実装と ETL パイプライン内での自動対処オプション。
- 単体テスト・統合テストのサンプルと CI ワークフロー定義。
- kabu ステーション API 統合（execution パッケージ内の実装拡充）と監視/通知用モジュールの完成。

以上。