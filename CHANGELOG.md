Keep a Changelog に準拠した変更履歴（日本語）

すべての変更はコードベースの内容から推測して作成しています。リリースバージョンはパッケージの __version__ に基づきます。

フォーマット:
- 変更はカテゴリ（Added, Changed, Fixed, Security, Documentation, etc.）に分けています。
- 各項目は実装された主な機能や設計方針、注意点を簡潔に記載しています。

Unreleased
---------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------
Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env /.env.local ファイルおよび環境変数から自動で設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml を探索）により、作業ディレクトリに依存せず自動ロードを行う。
  - .env のパースは export 形式、クォート内のエスケープ、インラインコメント処理などに対応。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数の保護（.env.local による上書き時に既存キーを保護）を実装。
  - 必須環境変数チェック（_require）とアプリ設定ラッパー Settings を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と便宜プロパティ（is_live, is_paper, is_dev）を追加。
- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得のための fetch_* 関数を実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - 再試行（指数バックオフ、最大3回）と 401 時のトークン自動リフレッシュ処理を実装。429 の Retry-After ヘッダーを優先して待機。
  - id_token のモジュールレベルキャッシュを導入してページネーション中のトークン共有を実現。
  - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar を追加。ON CONFLICT を使った冪等（重複更新）を実装。
  - レスポンス JSON デコードエラーや HTTP エラー時の詳細ログ化と例外ラップ。
  - 値変換ユーティリティ（_to_float, _to_int）を提供し、不正値や小数部のある数値の扱いを明確化。
- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する一連の処理を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 設計上のポイント:
    - 記事ID は URL を正規化（トラッキングパラメータ除去、ソート、フラグメント削除）した上で SHA-256 の先頭32文字を利用し冪等性を確保。
    - defusedxml を利用して XML ベースの攻撃（XML Bomb 等）を防止。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト時の検査（カスタム RedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検査でメモリ DoS を防止。
    - トラッキングパラメータ（utm_ 等）の除去、URL の正規化、タイトル/本文の前処理（URL 除去・空白正規化）。
    - DuckDB へはバルク INSERT（チャンクサイズ制御）＋INSERT ... RETURNING を用いて実際に挿入された件数を取得。トランザクションで処理、エラー時はロールバック。
    - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタリングを提供し、news_symbols テーブルへ一括保存するユーティリティを実装。
  - デフォルトの RSS ソース（例: Yahoo Finance のビジネス RSS）を定義。
- DuckDB スキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル定義を網羅的に実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 各テーブルに適切な CHECK・PRIMARY KEY・FOREIGN KEY 制約を定義。
  - よく使われるクエリパターン向けにインデックスも作成（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) でディレクトリ自動作成（必要なら）と DDL 実行を行い、接続オブジェクトを返す。get_connection() も提供。
- ETL パイプライン基盤を追加（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（取得数、保存数、品質問題リスト、エラーリストなど）を実装。品質問題の辞書化変換を提供。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）を実装。
  - 市場カレンダー補正ヘルパー（_adjust_to_trading_day）を実装。カレンダーがない場合のフォールバックを考慮。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl を実装（差分更新ロジック、backfill_days による再取得、fetch/save の呼び出し）。（ETL 設計方針に基づき差分＋backfill を行う実装）
  - テスト容易性のため id_token 注入や _urlopen のモック差し替えを想定した設計。
- モジュール間のロギング情報を適切に追加（取得・保存件数や警告など）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- RSS 処理で defusedxml を利用し XML 関連攻撃を緩和。
- RSS/HTTP クライアントで SSRF 対策を実装（スキーム検証、プライベートIP判定、リダイレクト検査）。
- .env 自動読み込みで既存の OS 環境変数を保護する機構を導入（.env.local による上書き時も同様）。
- HTTP レスポンスサイズ制限と gzip 解凍後の検査でメモリ DoS に対処。

Documentation
- 各モジュール冒頭に設計原則や処理フロー、想定外ケースの扱い（ロギング/再試行/冪等性など）を記載するドキュメンテーション文字列（docstring）を豊富に追加。

Notes / Migration
- 初回利用時は schema.init_schema(db_path) を呼んでデータベースとテーブルを初期化してください。db_path がファイルパスの場合、親ディレクトリは自動生成されます。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - （不足時は Settings のプロパティアクセス時に ValueError が発生します）
- .env の自動ロードはプロジェクトルートを基準に行われます。プロジェクトルートに .git や pyproject.toml がない場合は自動ロードをスキップします。
- ニュース収集で記事IDは URL 正規化に依存するため、外部システムと ID を照合する場合は同じ正規化ロジックを使ってください。
- run_news_collection は既知銘柄セット（known_codes）を与えることで自動的に news_symbols を作成します（既存の銘柄リストを事前に用意してください）。
- J-Quants クライアントはレート制限とリトライを厳守するため、短時間に多数のリクエストを投げる用途ではスループットに注意してください。

Known issues / Limitations
- ETL パイプラインの品質チェック（quality モジュール）自体は参照されていますが、quality モジュールの実装内容やチェックの詳細はこのコードベースからは推測できません。品質チェックの挙動や重大度定義は quality モジュールに依存します。
- run_prices_etl の戻り値や追加の ETL ジョブ（financials, calendar の個別ジョブなど）のフルワークフローは本稿で示した範囲に基づく実装です。運用時は ETL のスケジューリングや詳細なエラーハンドリングを追加してください。
- news_collector のネットワーク呼び出し部分はテスト容易性のためモック可能ですが、実際の運用では RSS ソース側の挙動（非標準フィード等）に注意が必要です。

お問い合わせ・貢献
- 初期実装のため改善点（追加の品質チェック、より詳細な監査ログ、異常検知ルールなど）は今後のイテレーション候補です。コードの各 docstring に設計意図が記載されているので、拡張・修正の際は設計方針に従ってください。

以上