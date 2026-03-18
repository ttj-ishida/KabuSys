# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。  
このパッケージはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用します。

[Unreleased]

## [0.1.0] - 2026-03-18

初回リリース。本リリースでは日本株自動売買システムの基盤となる設定管理、データ取得/保存、ニュース収集、ファクター計算（リサーチ）等のコア機能を実装しています。以下は主な追加点の要約です。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。バージョン: 0.1.0。
  - strategy、execution パッケージのスケルトンを用意（今後の戦略／発注ロジック格納用）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を安全に読み込む自動ロード機能を実装。
  - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない。
  - export プレフィックスやクォート付き値、インラインコメント等に対応した堅牢な .env パーサを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須変数取得用の _require と Settings クラスを提供。主な必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルト値や検証ロジック（KABUSYS_ENV の許容値、LOG_LEVEL の検証など）を実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 日足 / 財務データ / マーケットカレンダー取得関数(fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar) を実装（ページネーション対応）。
  - レート制御: 120 req/min を満たす固定間隔スロットリング _RateLimiter を実装。
  - リトライ: ネットワーク/サーバエラーに対する指数バックオフリトライ（最大 3 回）。429 の場合は Retry-After を尊重。
  - 401 エラー時はリフレッシュトークンから id_token を再取得して1回だけリトライする仕組みを実装。
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) は冪等（ON CONFLICT DO UPDATE）となる実装。
  - データ型安全な変換ユーティリティ (_to_float, _to_int) を提供。
  - fetched_at を UTC で記録し、データ取得時点のトレーサビリティを確保。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS 取得・パース機能を実装（デフォルトに Yahoo Finance のカテゴリRSSを用意）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb などに対処）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム/ホスト検査、プライベートIP拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）を実装し、SHA-256 のハッシュ（先頭32文字）で記事IDを生成。
  - テキスト前処理（URL除去・空白正規化）。
  - raw_news への冪等保存（save_raw_news）はチャンク分割・トランザクション管理・INSERT ... RETURNING を用いて実際に挿入された記事IDを返す実装。
  - 記事と銘柄コードの紐付け処理（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）を実装。銘柄抽出は正規表現（4桁数字）と known_codes フィルタによる。

- Data スキーマ定義 (src/kabusys/data/schema.py)
  - DuckDB 用のスキーマ（Raw / Processed / Feature / Execution 層）の定義（raw_prices, raw_financials, raw_news, raw_executions などの DDL を含む）。
  - 各テーブルに適切な制約（PRIMARY KEY、CHECK 等）を設定。

- Research / 特徴量計算 (src/kabusys/research/)
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）への将来リターンを DuckDB 上で一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（同順位は平均ランク、データ不足時は None を返す）。
    - rank, factor_summary: ランキング関数と基本統計量サマリーを実装（外部依存なし、標準ライブラリのみ）。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - calc_value: raw_financials と prices_daily を結合して PER（EPS が有効な場合）・ROE を計算。最新の財務レコードを target_date 以前から取得。
  - すべてのリサーチ関数は DuckDB 接続を引数に取り、prices_daily / raw_financials のみを参照。外部 API にはアクセスしない設計。

### 変更 (Changed)
- 該当なし（初回リリースのため既存コードの変更履歴はなし）。

### 修正 (Fixed)
- 該当なし（初回リリースのためバグ修正履歴はなし）。

### セキュリティ (Security)
- ニュース収集での SSRF/XML 攻撃対策を導入（defusedxml / ホスト/IP 検証 / リダイレクト検査 / レスポンスサイズ制限）。
- 外部 API クライアントは認証トークンの安全な再取得と再試行ロジックを実装。

### 注意事項 / マイグレーション
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須扱い。未設定時は ValueError が発生します。
- .env 自動ロード:
  - OS 環境変数が優先され、.env.local は .env の上書き（override=True）で適用されます。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - raw_ で始まるテーブル群（raw_prices, raw_financials, raw_news, raw_executions 等）を使用します。初期化やマイグレーションは schema モジュールを参照してください。
- J-Quants API のレート制限・再試行ポリシーにより、短時間に大量のリクエストを行う用途ではスループットが制限されます（設計は API 制限順守を優先）。

フィードバックやバグ報告があれば issue を作成してください。今後、strategy / execution の具体的な発注ロジック、Processed/Feature 層の生成処理、テストカバレッジ強化等を追加予定です。