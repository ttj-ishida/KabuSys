# CHANGELOG

すべての変更は Keep a Changelog に準拠し、セマンティック バージョニングを使用します。
  
## [Unreleased]
- 今後の変更や修正をここに記載します。

## [0.1.0] - 2026-03-18
初期リリース。

### 追加 (Added)
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、モジュール群: data, strategy, execution, monitoring（__all__ に公開）。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート判定: .git / pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を対応。
  - .env 行パーサーを実装（export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理）。
  - 必須環境変数取得ヘルパー (_require) と各種プロパティ:
    - J-Quants / kabu API / Slack / DB パス (DuckDB/SQLite) / KABUSYS_ENV（検証: development/paper_trading/live）/ LOG_LEVEL（検証）/ is_live/is_paper/is_dev

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API ベース実装: ベース URL, レート制限（120 req/min）、固定間隔スロットリング実装 (_RateLimiter)。
  - リトライ戦略: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象、429 の場合 Retry-After 優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と ID トークンキャッシュ機構。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 取得時刻の記録（fetched_at を UTC ISO8601 形式で保存）や PK 欠損行をスキップする挙動。
  - 型変換ユーティリティ: _to_float, _to_int（違和感のある文字列を安全に None にするロジック）。
  - 詳細なログ出力を多用して監査とデバッグを支援。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからニュース収集、前処理、DuckDB への保存を行う一連の実装。
  - セキュアな XML パーシングに defusedxml を利用。
  - SSRF 対策:
    - リダイレクト時のスキーム/ホスト検証用ハンドラ (_SSRFBlockRedirectHandler)
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないか検査する _is_private_host
    - URL スキーム検証（http/https のみ受け入れ）
  - サイズ制限・DoS対策:
    - 最大受信サイズ MAX_RESPONSE_BYTES（デフォルト 10MB）で超過時はスキップ
    - gzip 解凍後もサイズ検証（Gzip bomb 対策）
  - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証
  - テキスト前処理: URL 除去・空白正規化（preprocess_text）
  - 銘柄コード抽出ロジック（4桁数字候補を known_codes でフィルタ）
  - DB 書き込み:
    - save_raw_news: INSERT ... RETURNING を用いたチャンク挿入とトランザクション保護（ON CONFLICT DO NOTHING）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括で保存、重複排除、トランザクション管理
  - デフォルト RSS ソースを設定（例: Yahoo Finance ビジネス RSS）

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution レイヤーをカバーするテーブル群を定義。
  - 制約（NOT NULL、CHECK、PRIMARY/FOREIGN KEY）や適切な型を設定。
  - インデックスを定義して頻出クエリに対応。
  - init_schema(db_path) でファイル作成（親ディレクトリ自動作成）＋全 DDL 実行、get_connection() を提供。
  - テーブル作成・初期化は冪等性を保持。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult データクラスを実装し、実行結果の集約（品質問題・エラーの追跡）を提供。
  - 差分更新のためのヘルパー:
    - テーブル存在チェック、最大日付取得 (_table_exists, _get_max_date)
    - 市場営業日の調整 (_adjust_to_trading_day)
    - 最終取得日の取得用関数 (get_last_price_date, get_last_financial_date, get_last_calendar_date)
  - run_prices_etl の下流実装（差分取得、バックフィル、jquants_client を使った取得と保存の流れ）を追加。
  - 設計方針として差分更新・backfill（デフォルト3日）・品質チェックを想定。

### 改善 (Changed)
- ロギングと監査を強化
  - 各主要関数で info/warning/exception ログを追加し運用時の追跡性を向上。

- 可観測性 / テストしやすさのための設計改善
  - ネットワーク操作の抽象化（_urlopen をモック可能にする等）。
  - id_token の注入を可能にしてテスト容易性を確保。

### セキュリティ (Security)
- RSS/XML 関連:
  - defusedxml を使用して XML ベースの攻撃（XML Bomb 等）を軽減。
  - SSRF 対策としてリダイレクト先のスキーム・ホスト検証、プライベートアドレスの拒否を実装。
  - レスポンスサイズの上限を設け、圧縮後サイズも検証（Gzip bomb 対策）。

- .env 読み込み:
  - OS 環境変数を保護する protected 機構を導入し、意図しない上書きを防止。

### 既知の制限 / 注意点
- 一部処理はログ出力や例外伝播に依存しており、呼び出し側でのエラーハンドリングが必要。
- run_prices_etl 等の ETL 関数は id_token の注入や外部設定に依存するため、運用時は settings の設定が必須（未設定時は ValueError）。
- news_collector の URL 検証は DNS 解決失敗時に安全側（非プライベート）とみなして通過させる設計。環境によってはさらに厳格化が必要な場合あり。

### 割愛 / 今後の予定
- strategy / execution / monitoring の具体的な戦略・発注ロジックは今後実装予定。
- ETL の品質チェックモジュール (quality) の詳細実装・連携（現状は参照のみ）。

---

（注）この CHANGELOG はソースコードからの機能・設計の読み取りに基づく推測的な記述を含みます。実運用時は実際の仕様と照合してください。