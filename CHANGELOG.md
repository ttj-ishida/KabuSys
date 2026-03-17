CHANGELOG
=========

すべての履歴は Keep a Changelog の形式に準拠しています。
https://keepachangelog.com/ja/1.0.0/

未リリースの変更
----------------

（なし）

0.1.0 - 2026-03-17
-----------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）を追加。バージョンは 0.1.0。
  - サブパッケージのプレースホルダ: data, strategy, execution, monitoring。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml に基づくため、CWD に依存しない。
    - .env と .env.local の読み込み順（OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト用）。
    - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - .env パース機能を強化（コメント/export 対応、クォート内のエスケープ処理、インラインコメントの扱い等）。
  - Settings クラスを提供。主なプロパティ:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path, sqlite_path
    - env（development / paper_trading / live のバリデーション）
    - log_level（DEBUG/INFO/... のバリデーション）
    - ヘルパー: is_live / is_paper / is_dev
  - 必須環境変数未設定時に明確な ValueError を投げる _require() を実装。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限対応（120 req/min）: 固定間隔スロットリング RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大3回）を実装（408/429/5xx を対象）。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回だけリトライ。
    - ページネーション対応（pagination_key を用いた取得）。
    - Look-ahead bias 対策として fetched_at を UTC で記録。
    - 冪等性を担保する保存処理（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
  - 主要 API メソッド:
    - get_id_token(refresh_token: Optional[str]) -> str
    - fetch_daily_quotes(...)
    - fetch_financial_statements(...)
    - fetch_market_calendar(...)
    - save_daily_quotes(conn, records) -> int
    - save_financial_statements(conn, records) -> int
    - save_market_calendar(conn, records) -> int
  - 型変換ユーティリティ: _to_float, _to_int（不正値は None を返す安全設計）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し DuckDB に保存するモジュールを実装。
    - デフォルトソースとして Yahoo Finance のカテゴリ RSS を定義。
    - defusedxml を利用した XML パース（XML Bomb 対策）。
    - レスポンスサイズ上限（10MB）と Gzip 解凍後のサイズチェック（Gzip Bomb 対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler を実装。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストであれば拒否。
    - 記事 ID は URL 正規化（トラッキングパラメータ除去等）後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL除去、空白正規化）。
    - 銘柄コード抽出（4桁の候補から known_codes に含まれるもののみ採用）。
  - DB 保存:
    - save_raw_news(conn, articles) はチャンク挿入、トランザクションまとめ、INSERT ... ON CONFLICT DO NOTHING RETURNING id により新規挿入 ID を返却。
    - save_news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けをバルク保存（重複除去、トランザクション、一括 INSERT）。
  - 統合ジョブ run_news_collection(conn, sources, known_codes, timeout) を提供（各ソース独立したエラーハンドリング、部分的失敗の許容）。

- スキーマ管理（kabusys.data.schema）
  - DuckDB 用スキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの整合性制約（PRIMARY KEY, CHECK, FOREIGN KEY）を定義。
  - インデックス群を定義（頻出クエリに対する最適化を想定）。
  - init_schema(db_path) により DB ファイル親ディレクトリの自動作成と DDL 実行（冪等）。
  - get_connection(db_path) を提供（初回は init_schema を推奨）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL のフレームワーク・ユーティリティを実装。
    - ETLResult dataclass により実行結果・品質問題・エラーを集約。
    - テーブル存在チェック、最大日付取得ユーティリティ。
    - 市場カレンダーに基づく営業日調整ヘルパー。
    - 差分更新ロジック（最終取得日からの backfill を含む）。
    - run_prices_etl: 差分取得 -> 保存 -> 結果返却（fetch/save の分離、id_token 注入可能でテスト容易）。
  - 設計方針（ドキュメント化）:
    - 差分更新単位は営業日1日、backfill_days による後出しデータ吸収、品質チェックは Fail-Fast ではなく報告ベース。

Security
- セキュリティ対策を意識した実装を多数導入:
  - RSS 周りでは defusedxml, レスポンスサイズ制限, Gzip 解凍後の再チェック により XML/Gzip ボム対策。
  - SSRF 対策としてスキーム検証、リダイレクト時のホスト検査、プライベートアドレス拒否を実装。
  - 環境変数の取り扱いでは OS 環境変数を保護するための protected セットを導入。

Notes
- DuckDB に依存する関数群は DuckDB の SQL 実行に生のプレースホルダを使用している箇所があり（f-string によるテーブル名／DDL 組み立て等）、外部入力を直接埋め込む際は注意が必要（本コードでは定義済みDDLの実行に限定）。
- API クライアントのリトライ対象ステータスや最大試行回数、レート制限間隔は定数で定義されており必要に応じて調整可能。
- strategy、execution、monitoring の各パッケージはプレースホルダであり、個別戦略・発注ロジック・監視機能は今後実装予定。

Breaking Changes
- 初回リリースのため該当なし。

Deprecated
- なし。

Authors
- 実装はリポジトリのソースコードに基づく（コード内ドキュメントに設計方針と理由が明記されています）。

---

補足:
- 本 CHANGELOG はコードベースの内容（ドキュメンテーション文字列や実装）から推測して作成しています。実際のリリースノートとして公開する前に、プロジェクトの正式なリリース日や追加の変更点（テスト、CI、依存関係等）を反映してください。