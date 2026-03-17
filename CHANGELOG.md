Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
---------

（現在未リリースの変更はありません）

0.1.0 - 2026-03-17
-----------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、公開サブパッケージ一覧を __all__ で定義。

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local または環境変数から設定を読み込む自動ロードを実装。
    - プロジェクトルートは __file__ を基準に .git または pyproject.toml を探索して判定するため、CWD に依存しない挙動。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数を保護するための protected 上書きロジックをサポート。
  - .env パースの強化:
    - export 形式対応、クォート中のエスケープ、インラインコメントの取り扱い、コメント判定などを考慮した robust な行パースロジックを実装。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベルなどの設定取得と検証（許容値チェック、必須キーチェック）を提供。
  - デフォルト値や Path 型変換（DuckDB/SQLite パスの展開）を実装。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得用の fetch_* 関数を実装（ページネーション対応）。
  - ID トークン取得（get_id_token）とモジュールレベルのトークンキャッシュを実装。401 受信時は自動リフレッシュして 1 回リトライする仕組みを導入。
  - レート制御（固定間隔スロットリング）を実装してデフォルトで 120 req/min を厳守。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）を実装。429 の Retry-After を優先。
  - DuckDB への保存関数 save_* を実装。ON CONFLICT DO UPDATE により冪等性を担保し、fetched_at を UTC で記録してデータの取得時刻をトレース可能に。
  - 型変換ヘルパー（_to_float, _to_int）を用意し、不正なフォーマットや空値に対して安全に None を返す。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集機能を実装（DEFAULT_RSS_SOURCES を含む）。
  - セキュリティ対策・堅牢化:
    - defusedxml を利用して XML 関連の攻撃を軽減。
    - SSRF 対策: URL スキーム検証（http/https 限定）、ホストがプライベート/ループバック/リンクローカルの場合は拒否、リダイレクト時も検査するカスタムリダイレクトハンドラを実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込み時と gzip 解凍後のサイズチェックでメモリ DoS を防止。
    - gzip レスポンス対応および解凍失敗ハンドリング。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_*, fbclid 等）を除去、クエリソート、フラグメント除去などを行う _normalize_url を実装し、正規化 URL から SHA-256 の先頭32文字を用いて記事 ID を生成。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB への保存:
    - save_raw_news: チャンク化＋トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事 ID を正確に返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク化して一括保存（ON CONFLICT DO NOTHING RETURNING 1）し、挿入件数を返す。
  - 銘柄抽出ロジック（extract_stock_codes）を実装し、正規表現で 4 桁数字候補を抽出して known_codes によるフィルタリング、重複除去を行う。
  - run_news_collection: 全ソースに対する収集ワークフローを実装。各ソースは独立してエラーハンドリングされ、1 ソースの失敗が他に影響しない設計。新規記事に対する銘柄紐付けもまとめて保存。

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル群を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を含む DDL を提供。
  - 頻出クエリに対するインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ作成→接続→DDL/INDEX 実行を行い、冪等に初期化する API を提供。get_connection() で既存 DB へ接続可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー）を集約して出力できるようにした。
  - 差分更新支援関数:
    - 最終取得日の取得（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
    - 営業日調整ヘルパー（_adjust_to_trading_day）を実装し、market_calendar を参照して非営業日を直近の営業日に調整。
  - run_prices_etl を実装（差分更新、backfill_days、取得→保存、ログ出力）。ETL の設計方針として backfill により API の後出し修正を吸収、品質チェックは外部 quality モジュールに委譲する前提。

Security / Robustness
- 全体を通して冪等性（DB の ON CONFLICT 処理・ID生成）と堅牢なエラーハンドリングを重視。
- 外部接続部分（HTTP・XML・ファイル読み込み）での例外や不正入力に対する防御コード（サイズ制限、スキームチェック、defusedxml、SSRF 検査、ファイル読み込みの警告）を追加。
- ロギングを適切に配置し、操作やエラーのトレースを容易に。

Notes
- 本リリースは基盤となるデータ収集・保存・スキーマ・ETL の核となる機能群の初期実装に注力しています。  
- 実際の運用では環境変数（JQUANTS_REFRESH_TOKEN 等）を .env か実環境変数で適切に設定してください。  
- 将来的なリリースでは品質チェック・戦略・実行モジュールの拡充やテストの追加、API の安定化（エラーハンドリングの微調整等）を予定しています。