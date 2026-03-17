# Changelog

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従ってバージョニングしています。  
現在のバージョンはパッケージ定義に基づく 0.1.0 です。

全般: 初期リリースとしての機能実装が含まれます。以下はコードベース（src/kabusys 以下）の実装内容から推測してまとめた変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-17

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"、公開サブパッケージ指定）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの自動読み込み実装
    - プロジェクトルート判定（.git または pyproject.toml に基づく）
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - .env パーサ実装（コメント、export プレフィックス、クォート・エスケープ処理対応）
    - 上書き制御（override / protected）対応
  - Settings クラスにアプリケーション設定をプロパティとして実装
    - J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）
    - env と log_level の値検証（許容値チェック）、必須キー未設定時は例外を投げるヘルパー `_require`
- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 基本クライアント実装（GET/POST、JSON デコード）
  - レートリミッタ実装（固定間隔スロットリング、デフォルト 120 req/min）
  - 再試行戦略（指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象）
  - 401 時の自動トークンリフレッシュ（1 回のリフレッシュ試行を保証）
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）
  - ページネーション対応のフェッチ関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する save_* 関数実装（ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ変換ユーティリティ（_to_float, _to_int）を実装し入力値の頑健な解釈を行う
- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードの取得・パース・正規化・DB 保存ワークフローを実装
  - セキュリティと健全性対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）
    - SSRF 対策: URL スキーム検証、ホストがプライベートアドレスかを判定、リダイレクト時も検証するカスタムリダイレクトハンドラ
    - HTTP レスポンス最大読み取りバイト数制限（MAX_RESPONSE_BYTES = 10 MB）
    - gzip 圧縮検出と安全な解凍（解凍後もサイズチェック）
    - 許可スキームは http/https のみ
  - URL 正規化（tracking パラメータ除去、クエリソート、フラグメント削除）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で一意化（冪等性確保）
  - テキスト前処理（URL 除去・空白正規化）
  - DuckDB への保存:
    - save_raw_news: チャンク INSERT、トランザクション、INSERT ... RETURNING により新規挿入 ID リストを返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク単位でトランザクション保存（RETURNING により実際に挿入された数を取得）
  - 銘柄コード抽出関数 extract_stock_codes（4桁数字パターン + known_codes フィルタ）
  - テスト容易性: _urlopen を差し替え可能（モック可能）
  - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の 3 層/4 層に対応するテーブル DDL を定義
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PK/FOREIGN KEY/CHECK）を含む厳格なスキーマ定義
  - よく使うクエリのためのインデックス定義
  - init_schema(db_path) によりディレクトリ作成→全DDL/インデックス実行（冪等）
  - get_connection(db_path) を提供（初期化は行わない）
- ETL パイプライン基盤（kabusys.data.pipeline）
  - ETLResult dataclass（処理統計・品質問題・エラー集約）
  - テーブル存在確認・最大日付取得などヘルパー実装
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）
  - 差分更新戦略を備えた個別 ETL ジョブ雛形:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
    - run_prices_etl の差分取得ロジック（バックフィル日数デフォルト 3 日、最短データ開始日は 2017-01-01）
  - 品質チェックを呼び出すためのフック（quality モジュール想定）
- その他
  - パッケージ内の execution / strategy モジュールのプレースホルダを追加（将来的な発注・戦略実装用）

### Security
- RSS パーシングで defusedxml を使用し XML に対する攻撃を軽減
- ニュース取得での SSRF 対策を実装（スキーム検証、ホストプライベートIPチェック、リダイレクト時の検証）
- .env 自動読み込みは環境変数で無効化可能（テストや CI の安全性向上）
- HTTP リクエストのタイムアウト・レスポンスサイズ制限を導入

### Performance & Reliability
- J-Quants API 用にレートリミッタ実装（120 req/min 固定）とリトライ（指数バックオフ）を導入し API レート制限と一時的障害に耐性を付与
- DuckDB へのバルク挿入はチャンク化してトランザクションで扱いオーバーヘッドを低減
- save_* API は冪等性を保証（ON CONFLICT DO UPDATE / DO NOTHING）

### Fixed
- データ型変換ユーティリティの実装で不正入力に対する安全な変換処理を追加
  - _to_float, _to_int: 空文字・None・不正な文字列を安全に扱う

### Notes / Known issues / TODO
- run_prices_etl の実装末尾がスニペット上で不完全に見える（最後の return が途中で終わっている）。実際のリポジトリでは fetched/saved の両方を返すべきだが、コード断片によりその点は要確認・修正が必要。
- strategy / execution パッケージは名前空間のみで具体的実装は未提供（今後の実装予定）。
- quality チェックの連携・実際のチェック実装は別モジュール（kabusys.data.quality）に依存しており、実装の有無に応じて ETL の挙動が変わる可能性あり。
- テスト用に置き換え可能な箇所（例: news_collector._urlopen）を提供しているため、ユニットテストで外部依存を差し替えて検証可能。

---

（補足）本 CHANGELOG は現コードベースの実装から推測して作成した概要です。実際のリリースノートとして用いる際は、コミット履歴やリリースノート用の差分情報を参照して日付・変更点を確定してください。