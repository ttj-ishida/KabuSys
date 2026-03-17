CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルはプロジェクトのリリース履歴を記録します。

Unreleased
----------

- （現時点の開発中の変更はここに記載）

0.1.0 - 2026-03-17
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本コアを実装。
  - パッケージ構成:
    - kabusys.config: 環境変数 / 設定管理（.env/.env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）
      - プロジェクトルートの自動検出（.git または pyproject.toml）に基づく .env 読み込み
      - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応
      - protected キー（既存 OS 環境変数）を上書きしない挙動、.env.local は .env を上書きする優先度
      - Settings クラス: 必須キー取得（_require）、env / log_level の入力値検証、各種設定プロパティ（J-Quants、kabu API、Slack、DBパスなど）
    - kabusys.data.jquants_client: J-Quants API クライアント
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）
      - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx をリトライ対象
      - 401 Unauthorized 受信時はリフレッシュトークンで id_token を自動再取得して 1 回リトライ（無限再帰防止）
      - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
      - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を抑制
      - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）で重複を排除
      - 入力値変換ユーティリティ（_to_float, _to_int）を提供（不正値は None）
    - kabusys.data.news_collector: RSS ニュース収集モジュール
      - RSS フィード取得、前処理、DuckDB への冪等保存ワークフローを実装
      - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト先のスキーム/プライベートアドレス検査）、受信サイズ上限（10 MB）および gzip 解凍後の再チェック（Gzip bomb 対策）
      - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）、正規化 URL の SHA-256（先頭32文字）で記事ID生成（冪等性を確保）
      - fetch_rss: 非 http/https スキームやプライベートホストを拒否、XML パース失敗時は空リストを返す
      - save_raw_news: バルク INSERT（チャンク化）と INSERT ... RETURNING を使って実際に挿入された記事 ID のリストを返す。トランザクションをまとめて実行
      - news_symbols 連携: extract_stock_codes（4桁銘柄抽出）と一括保存関数（_save_news_symbols_bulk）
      - run_news_collection: 複数ソースを順次収集し、各ソースごとにエラーハンドリングを行う（1ソース失敗でも他ソースを継続）
    - kabusys.data.schema: DuckDB スキーマ定義と初期化
      - Raw / Processed / Feature / Execution 層のテーブル定義を実装（詳細な制約・PRIMARY KEY・CHECK を含む）
      - news_articles / news_symbols 等を含むニュース関連テーブル
      - インデックス定義（頻出クエリパターンを想定）
      - init_schema(db_path): 親ディレクトリ自動作成、全DDLを実行して DB を初期化（冪等）
      - get_connection(db_path): 既存 DB への接続（スキーマ初期化は行わない）
    - kabusys.data.pipeline: ETL パイプライン（骨組み）
      - 差分更新戦略（最終取得日からの backfill、デフォルト backfill_days=3）
      - 市場カレンダーの先読み（lookahead 値）
      - ETLResult dataclass による結果集約（品質問題とエラーの集約、to_dict）
      - テーブル存在チェック、最終日取得ユーティリティ
      - run_prices_etl（差分取得 + 保存）の実装（取得→保存のフロー、ログ出力）
  - パッケージメタ: src/kabusys/__init__.py にバージョン __version__ = "0.1.0"

Security
- RSS / XML 処理での安全性強化:
  - defusedxml を採用して XML Bomb 等に対処
  - SSRF 対策: リダイレクト時の事前検証、ホスト/IP がプライベートかどうかのチェック（DNS 解決・IP 判定）
  - URL スキーム検証（http/https のみ許可）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の二重チェック

Performance / Reliability
- J-Quants API クライアントにレート制御とリトライロジックを実装（安定した長時間実行を想定）
- DuckDB へのバルク挿入をチャンク化して SQL 長やパラメータ数を制御
- INSERT ... RETURNING とトランザクションまとめにより正確な保存数計測とオーバーヘッド低減

Database / Schema
- DuckDB 用の詳細なスキーマを提供（データ整合性を保つため多数の CHECK 制約・外部キー・PRIMARY KEY を定義）
- init_schema によりローカルファイルの親ディレクトリを自動作成して DB を初期化可能
- raw レイヤーは取得元データをそのまま保存、processed/feature/execution 層は下流処理用に設計

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Migration
- 初回導入時は以下を推奨:
  - settings を利用するために .env/.env.local に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。未設定の必須キーは Settings のプロパティアクセス時に ValueError を発生させます。
  - DB の初期化は init_schema(settings.duckdb_path) を呼ぶことで行えます（":memory:" もサポート）。
  - テストや CI で自動 .env ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - news_collector.fetch_rss はネットワーク I/O を行うため、テスト時は kabusys.data.news_collector._urlopen をモックすることが可能です。
  - jquants_client の id_token は内部キャッシュされ、ページネーション間で共有されます。必要に応じて get_id_token(force_refresh) を利用してください。

Contributors
- 初回実装（コアモジュール一式）

以降のリリースでは、機能追加（戦略モジュール・実際の発注実装・監視連携等）、ユニットテストの整備、CI/CD やドキュメント強化、さらに品質チェックモジュール（quality）や監視用モジュールの拡充を予定しています。