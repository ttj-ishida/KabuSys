# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本リリース内容はソースコードから推測して作成した要約です（実装意図・設計注釈を含む）。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を提供します。
主に以下のサブパッケージ・モジュールを実装しました。

### 追加 (Added)

- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン（0.1.0）および公開モジュール一覧を追加。

- 設定/環境変数管理 (src/kabusys/config.py)
  - .env 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から特定し、.env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パース処理の実装（コメント、export プレフィックス、クォート取り扱い、インラインコメント等対応）。
    - .env 読み込み時の上書き制御（override）と保護キー（protected）機構。
  - Settings クラス:
    - J-Quants / kabuAPI / Slack / DB パス等の環境変数アクセスラッパーを提供（必須項目は _require により ValueError を送出）。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証ロジックを実装（許容値を限定）。
    - is_live / is_paper / is_dev のヘルパーを追加。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - レート制限対応（120 req/min 固定間隔スロットリング _RateLimiter）。
    - リトライ/指数バックオフ（最大3回、408/429/5xx に対応）、429 の Retry-After 優先処理。
    - 401 受信時のトークン自動リフレッシュ（1回のみ）とトークンキャッシュ化。
    - ページネーション対応で全件取得（pagination_key を利用）。
  - データフェッチ関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (財務四半期データ)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を用いた冪等性、fetched_at の記録
  - 型変換ユーティリティ:
    - _to_float / _to_int（安全な変換ロジック）

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS 収集パイプライン:
    - フィード取得（gzip 対応）、XML パース（defusedxml を使用して XML 攻撃対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム&ホスト検査、プライベートIPチェック。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再検査（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化、記事ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク INSERT + INSERT ... RETURNING id、1 トランザクションでの処理、トランザクション失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄紐付けの一括保存（重複排除、チャンク、RETURNING による実挿入数取得）。
  - 銘柄コード抽出:
    - 日本株の4桁コード抽出ロジック（正規表現による候補抽出と known_codes フィルタリング）。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースからの収集、個別ソースのエラーハンドリング、新規保存数の集計、銘柄紐付けの一括処理。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用 DDL を定義（Raw / Processed / Feature / Execution 層の設計に準拠）。
  - Raw 層テーブル定義の追加（raw_prices, raw_financials, raw_news, raw_executions など）。
  - スキーマ初期化のためのモジュール基盤を用意。

- リサーチ / 特徴量計算 (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily テーブル参照で一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。データ不足/ゼロ分散時は None を返す。
    - rank: 同順位は平均ランクとするランク付け実装（浮動小数の丸めで ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median 計算。
    - 設計方針: duckdb 接続を受け取り prices_daily のみ参照、外部ライブラリに依存しない実装。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m および 200 日移動平均乖離 ma200_dev（データ不足時は None）。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金・出来高比（avg_turnover, volume_ratio）。
    - calc_value: raw_financials の最新財務を参照して PER（eps が 0 または欠損なら None）と ROE を計算。
    - 設計方針: DuckDB の SQL ウィンドウ関数を多用し、prices_daily / raw_financials のみ参照、発注 API へのアクセスなし。

- パッケージ再エクスポート (src/kabusys/research/__init__.py)
  - 研究用ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。

### 変更 (Changed)

- （初期リリースのため該当なし）

### 修正 (Fixed)

- （初期リリースのため該当なし）

### セキュリティ (Security)

- XML パーサに defusedxml を利用し XXE 等の攻撃を緩和。
- RSS フェッチ時に SSRF 対策（スキーム検証、プライベート/ループバックアドレスの拒否、リダイレクト検査）を実装。
- レスポンスサイズ上限や Gzip 解凍後のチェックにより DoS（大容量レスポンス）対策を追加。

### 補足 / 注意事項 (Notes)

- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須プロパティとして Settings からアクセスすると ValueError を投げます。 .env.example を参考に .env を用意してください。
- デフォルト DB パス:
  - duckdb: data/kabusys.duckdb
  - sqlite (monitoring 用): data/monitoring.db
- KABUSYS_ENV の有効値: development / paper_trading / live
- LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
- research モジュールは標準ライブラリのみで実装されているため、pandas 等に比べて処理や記述が低レベルです。将来的に高速化や機能拡張（PBR, 配当利回り等）を検討してください。
- news_collector は defusedxml などの依存が必要です。パッケージ化時に依存関係に含めてください。
- jquants_client は API レート制限・リトライ・認証リフレッシュなどを組み込んでいますが、大量取得時の実行時間/スループットは運用環境での確認を推奨します。

### 既知の制限 / 今後の TODO (Known issues / TODO)

- factor_research の一部指標（PBR、配当利回り）は未実装（コメントに明記）。
- research 側は外部ライブラリに依存しない設計だが、将来的には pandas 等を optional 依存にして機能拡張する余地あり。
- schema.py の Execution 層等は今後の発注・約定管理ロジックと連動して拡張予定。

---

以上が本コードベースの初回公開（0.1.0）における主な変更点・設計意図の要約です。必要であれば各モジュール別により詳細な変更点や使用例、マイグレーション手順（DB 初期化 SQL 例、環境変数の設定例など）を追加で作成します。どの情報が必要か教えてください。