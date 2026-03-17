# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。  

---

## [Unreleased]

### Added
- ドキュメント・コードベースの初期設計に基づく主要モジュールを追加（初期実装）。
  - パッケージ名: `kabusys`（バージョン 0.1.0 を package 情報に反映）。
- 環境変数・設定管理 (`kabusys.config`)
  - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - `.env` パーサーの強化:
    - `export KEY=val` 形式対応、シングル／ダブルクォート内のエスケープ対応、インラインコメント処理、空行・コメント行のスキップ。
  - 必須設定取得 `_require` と各種プロパティ（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル検証など）。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティ（JSON デコード、エラーハンドリング）。
  - レート制限（固定間隔スロットリング、120 req/min）を実装する内部 RateLimiter。
  - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 優先化、ネットワークエラーの再試行。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有（モジュールレベル）。
  - ページネーション対応のデータ取得関数:
    - 日足データ: fetch_daily_quotes
    - 財務データ: fetch_financial_statements
    - 市場カレンダー: fetch_market_calendar
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）で fetched_at を UTC ISO8601 で記録:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 値変換ユーティリティ（_to_float, _to_int）で入力のロバスト性を改善。
- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得 → 前処理 → DuckDB へ保存までのフルワークフローを実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML-Bomb 等への対策。
    - SSRF 対策: スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト時の事前検査用ハンドラ `_SSRFBlockRedirectHandler`。
    - レスポンス最大読み取りサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）と記事 ID 生成（正規化 URL の SHA-256 先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 抽出した記事を DuckDB にチャンク挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING）して実際に挿入された ID を返す（save_raw_news）。
  - 記事と銘柄コードの紐付け保存（save_news_symbols, _save_news_symbols_bulk）もチャンク・トランザクションで実装。
  - 銘柄コード抽出ロジック（4桁数字、既知コードセットフィルタ）を搭載。
  - RSS フェッチのフォールバック処理（channel/item の有無による探索）。
- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - 3層（Raw / Processed / Feature / Execution）を想定したDDLを定義。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance などを定義。
  - インデックス群を定義（頻出クエリ用）。
  - init_schema(db_path) により親ディレクトリ自動作成・テーブル作成を行い、冪等に初期化。
  - get_connection() による既存 DB 接続取得。
- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL 結果を保持する ETLResult dataclass（品質問題リスト、エラーリスト、有無判定ヘルパー、dict 化）を実装。
  - 差分更新ヘルパー（テーブル存在確認、最大日付取得）。
  - 市場カレンダーを参照して非営業日調整するヘルパー（_adjust_to_trading_day）。
  - 差分更新ロジック（最終取得日から backfill 日数分の再取得）を備えた run_prices_etl（fetch → save の流れ）を実装。
  - 品質チェックのための品質モジュール呼び出しの想定（quality モジュールとの連携設計）。
- パッケージ構成の最小エントリ（__init__.py）を配置し、サブモジュールを __all__ に指定。

### Security
- ニュース取得での複数のセキュリティ強化を導入:
  - defusedxml を用いた XML パース（安全化）。
  - SSRF 対策（スキームチェック、プライベートアドレス拒否、リダイレクト検査）。
  - 受信サイズ上限と gzip 解凍後再検査による DoS 緩和。

### Changed
- （初期リリース相当の実装）型注釈、ロギング、詳細な docstring を多くの関数に追加して保守性を向上。

### Known issues / TODO
- run_prices_etl の戻り値がソース内で途中で切れている（提示されたコード末尾が `return len(records),` のまま終了）。実運用前に ETL の戻り値整合性（取得数と保存数のタプル）を確認・修正する必要あり。
- その他モジュール（execution, strategy, monitoring）の実装は空のパッケージ/プレースホルダのまま。この部分は今後の実装予定。

---

## [0.1.0] - 2026-03-17

初期リリース（上記 Unreleased の内容をパッケージ初期実装としてリリース相当）。

### Added
- 環境設定読み込みと検証（kabusys.config）。
- J-Quants API クライアント（取得・保存・リトライ・レート制御・トークン管理）。
- RSS ニュース収集と DuckDB への保存ロジック（セキュリティ対策・ID生成・銘柄紐付け）。
- DuckDB スキーマ定義と初期化ユーティリティ。
- ETL パイプライン補助（差分更新、カレンダー調整、ETL 結果管理）。
- 各所に詳細な docstring と型注釈、ロギングを実装。

### Security
- XML パースの安全化（defusedxml）、SSRF 対策、応答サイズ制限を導入。

### Fixed
- （該当なし：初回リリース）

### Known issues
- run_prices_etl の戻り値不整合（上記参照）。
- execution / strategy / monitoring サブパッケージは未実装（プレースホルダ）。

---

注記:
- ここに記載した変更点は提供されたソースコードから推測した実装・設計意図に基づくまとめです。リリース日付はコード解析時点の日付を仮定しています（必要に応じて調整してください）。
- 実運用へ移行する前に Known issues を確認し、未実装箇所や戻り値整合性の修正を行ってください。