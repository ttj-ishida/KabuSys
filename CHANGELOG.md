Keep a Changelog
すべての注目すべき変更点をこのファイルに記録します。セマンティックバージョニングに従います。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-17

初回公開リリース。日本株自動売買システム「KabuSys」の基盤モジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージメタ情報（kabusys.__init__）を追加。バージョンは 0.1.0。
  - モジュール構成を定義: data, strategy, execution, monitoring（strategy/execution/monitoring は初期はパッケージ空実装）。
- 環境設定管理 (kabusys.config)
  - .env ファイルと環境変数を統合して読み込む自動ローダーを実装（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により、CWD 非依存で .env を検出。
  - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得用ヘルパー _require と Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パスなどのプロパティを定義（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - KABUSYS_ENV（development / paper_trading / live）の検証。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - Path 型での duckdb/sqlite パス解決。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。401 受信時は自動リフレッシュして 1 回リトライ。
  - レート制御: 固定間隔スロットリングに基づく RateLimiter を実装し、J-Quants の制限（120 req/min）を尊重。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx 対象。429 の場合は Retry-After ヘッダを優先。
  - ページネーション間で ID トークンを共有するモジュールレベルのトークンキャッシュ機能。
  - DuckDB への永続化ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。全て冪等（ON CONFLICT DO UPDATE）。
  - データ保存時に取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias のトレーサビリティを確保。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装（不正な値や空値は None）。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュースを取得し raw_news に保存する fetch_rss / save_raw_news を実装。
  - 防御設計:
    - defusedxml を使った XML パース（XMLBomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト時のスキーム・ホスト検査、プライベートアドレス拒否、_SSRFBlockRedirectHandler を用いた安全なリダイレクト処理。
    - レスポンス最大読み取りサイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後もサイズを検査（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）を除去する URL 正規化、記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - HTTP ヘッダでの gzip 受け入れ対応。
  - DB 保存はチャンク化して一括挿入し、INSERT ... RETURNING を使って実際に挿入されたレコードのみを返す（トランザクションで一括処理、失敗時はロールバック）。
  - 銘柄コード抽出ロジック（4桁数字、known_codes に基づくフィルタ）と、news_symbols テーブルへの紐付け用バルク保存機能。
  - デフォルト RSS ソースに Yahoo Finance ビジネス RSS を設定。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマ DDL を定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed Layer。
  - features, ai_scores を含む Feature Layer。
  - signals, signal_queue, orders, trades, positions, portfolio_* など実行関連テーブルを含む Execution Layer。
  - 各種 CHECK 制約、外部キー、インデックス定義を含む（クエリパターンを考慮したインデックスを作成）。
  - init_schema(db_path) によりディレクトリ作成（必要時）→ 全 DDL / インデックスを実行する初期化関数を提供。get_connection() で既存 DB への接続を返す。
- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行結果を格納する ETLResult データクラス（品質問題・エラー集約、辞書化メソッド付）。
  - 差分更新ヘルパー（テーブル存在チェック、最大日付取得）を実装。
  - 市場カレンダーに基づく営業日補正ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl の骨子を実装（差分計算、バックフィル日数指定、jquants_client を用いた取得→保存の流れ）。
  - 設計方針として、品質チェックは致命的問題を検出しても ETL を継続する（呼び出し元で対処）。

### Security
- ニュース収集での SSRF 対策を実装（スキーム検証、プライベートIP拒否、リダイレクトチェック）。
- XML パースに defusedxml を使用し XML 関連攻撃を軽減。
- .env 自動ロード時に OS 環境変数を保護する protected キーセットの考慮。
- HTTP クライアントにタイムアウトやレスポンスサイズ制限を適用。

### Known issues / Notes
- run_prices_etl の戻り値シグネチャと実装が不整合:
  - ドキュメント上は (取得数, 保存数) のタプルを返す設計だが、実装の末尾で "return len(records)," のように単一要素のタプル（または意図しない戻り方）になっています。実際の呼び出し側で期待される 2 要素タプルを返すよう修正が必要です。
- strategy, execution, monitoring パッケージは初期ステブ（空パッケージ）。具体的な戦略ロジックや発注ロジックは今後実装予定。
- news_collector の既定の RSS ソースは限定的（現状は Yahoo のカテゴリー RSS のみ）。追加ソースの設定は可能。
- 一部の関数はテスト用に外部差し替え（モック）を想定（例: _urlopen の差し替え）。

### Dependencies（主要）
- duckdb: データ格納と SQL 処理
- defusedxml: RSS/XML パースの安全化
- 標準ライブラリのみで実装されている部分あり（urllib, gzip, hashlib, ipaddress, socket など）

---

今後の予定（例）
- run_prices_etl の戻り値バグ修正と単体テスト追加
- ETL ワークフローの品質チェック（quality モジュール）の統合テスト
- execution レイヤの kabu API 連携（発注・約定取得）実装
- strategy のサンプル戦略実装・バックテスト基盤整備
- monitoring（Slack 通知等）の実装

（注）この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴や issue に基づく差分とは異なる場合があります。