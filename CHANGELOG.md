CHANGELOG
=========

この変更履歴は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測して作成しています（実装コメントや設計方針に基づく説明を含みます）。

目次
----
- [Unreleased](#unreleased)
- [0.1.0 - 2026-03-18](#010---2026-03-18)

Unreleased
----------
（今後の作業・既知の問題／TODO）
- run_prices_etl の戻り値の実装確認
  - ソースコード上で run_prices_etl の最後の return が未完（"return len(records)," のように見える）ため、正しいタプル (fetched, saved) を返すよう修正が必要。
- 単体テスト・統合テストの追加
  - ネットワーク I/O、DB 書き込み、リダイレクト/SSRF 対策、.env パーサーなどの辺縁ケースを網羅するテストを強化する予定。
- ドキュメント補完
  - DataPlatform.md / DataSchema.md など設計文書とのリンクやサンプル運用手順（初期化・認証トークンのセット方法等）を追加予定。

0.1.0 - 2026-03-18
------------------
Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
- 環境変数・設定管理
  - .env ファイルおよび環境変数を読み込む設定モジュールを追加（src/kabusys/config.py）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルート判定は .git または pyproject.toml を探索して決定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（テスト用途）をサポート。
  - 柔軟な .env パーサー実装:
    - コメント行・空行スキップ、export KEY=val 形式対応
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート無しの場合は # 前が空白/タブであればコメントとみなす）
  - Settings クラスで必須値チェックと型変換を提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, DUCKDB_PATH 等）。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジックと is_live / is_paper / is_dev のヘルパープロパティを追加。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大 3 回、対象: 408/429/5xx）を実装。
  - 401 Unauthorized 受信時には自動で ID トークンをリフレッシュして 1 回リトライする仕組みを実装（再帰防止のため allow_refresh フラグあり）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻の記録（fetched_at を UTC で保存）により Look-ahead Bias のトレースが可能。
  - 型変換ユーティリティ _to_float / _to_int を提供（不正値は None）。
- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py を実装。
  - RSS フィード取得と記事保存の ETL:
    - fetch_rss: RSS 取得、XML パース、記事前処理（URL 除去、空白正規化）
    - save_raw_news: DuckDB の raw_news にチャンク単位で INSERT ... RETURNING を使って保存（冪等性は id（SHA-256先頭32文字）で保証）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク保存（ON CONFLICT DO NOTHING, INSERT RETURNING）
    - run_news_collection: 複数ソースの総合収集ジョブ（各ソースは独立してエラーハンドリング）
  - セキュリティ・堅牢性対策:
    - defusedxml を使用して XML Bomb 等を防御
    - SSRF 対策: リダイレクト検査用ハンドラと初回ホスト検証（プライベートアドレス、ループバック等を拒否）
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）
    - トラッキングパラメータ除去（utm_* 等）のための URL 正規化と記事ID の SHA-256 ハッシュ化（先頭32文字）
  - 銘柄コード抽出ロジック（4桁数字パターン）と既知銘柄セットによるフィルタリングを実装。
- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py にて DataSchema.md に基づく多層スキーマを実装:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに制約（PRIMARY KEY / CHECK / FOREIGN KEY）を設定。
  - 頻出クエリに備えたインデックスを作成。
  - init_schema(db_path) でディレクトリ作成・DDL 実行・インデックス作成をまとめて行い、DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB 接続を取得（初期化は行わない）。
- ETL パイプライン（基礎）
  - src/kabusys/data/pipeline.py を実装（ETL 操作の骨格）。
  - 差分更新のためのユーティリティを実装:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _get_max_date, _table_exists による安全な存在チェック
  - 市場カレンダーに基づく trading day 調整ヘルパー _adjust_to_trading_day を実装（過去方向に最大 30 日遡る）。
  - run_prices_etl（株価差分 ETL）の骨組みを追加:
    - 最終取得日から backfill_days 分だけ遡って再取得する仕組みを提供（デフォルト backfill_days=3）
    - J-Quants クライアントの fetch_daily_quotes と save_daily_quotes を使用して差分取得→保存を行う
  - ETLResult dataclass を導入し、品質チェック結果やエラー情報を収集できるようにした（quality モジュール連携想定）。
- ロギング
  - 各主要処理に info/warning/error レベルのログを適切に埋め込み、運用時のトラブルシュートを支援。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- RSS フィード処理に関する複数のセキュリティ対策を導入:
  - defusedxml による XML パースの安全化
  - SSRF 対策（リダイレクト検査 + ホストのプライベートアドレス判定）
  - レスポンスサイズと gzip 解凍後サイズの上限チェック
  - URL スキームの制限（http/https のみ）
- .env パーサーのクォート内エスケープ処理により、注入リスクおよび誤読を低減。

Known issues / Notes
- run_prices_etl の戻り値についてソース上に未完な箇所が見られるため、実行時に例外や不正な戻り値になる可能性がある。リリース後の修正が推奨される。
- DuckDB への SQL 実行はプレースホルダ方式を使っているが、動的に SQL 文字列を組み立てる箇所（大量行のチャンク INSERT 等）では SQL インジェクションの注意が必要。現状は内部データ（RSS からの外部入力等）を扱うため、さらに検査・サニタイズが望ましい。
- run_news_collection は既知銘柄セット（known_codes）を渡さない場合は銘柄紐付けをスキップする設計。known_codes の取得・更新手順を運用ドキュメントに明記することを推奨。

補足
- 環境設定や DB 初期化手順の一般的な流れ（運用メモ）
  1. .env.example を参考に .env/.env.local を配置（JQUANTS_REFRESH_TOKEN 等を設定）
  2. init_schema(settings.duckdb_path) を実行して DB を初期化
  3. run_prices_etl / run_news_collection 等を定期実行（Cron / Airflow など）
- テスト用フック:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動 .env ロードを無効化可能（テスト時に環境を固定するために有用）。

以上。必要であれば各項目をより詳細に分割（例: モジュール別の細かい変更履歴、関数一覧、利用例）して展開します。どの程度の詳細が必要か教えてください。