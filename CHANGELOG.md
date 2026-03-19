# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-19

初回リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期化（バージョン: 0.1.0）。公開 API: data, strategy, execution, monitoring。
- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを提供。
  - プロジェクトルート検出機能：.git または pyproject.toml を基準にルートを特定（CWD非依存）。
  - .env と .env.local の読み込み順序（OS環境変数 > .env.local > .env）。.env.local は上書き（override）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env の行解析は export プレフィックス、クォート（エスケープ対応）、インラインコメントなどに対応。
  - Settings クラスを提供し、必要な環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）を管理。
  - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証機構。
- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。日足（OHLCV）・財務データ・マーケットカレンダー等の取得をサポート。
  - レート制限実装（120 req/min、固定間隔スロットリング）。
  - 再試行ロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx に対してリトライ）。
  - 401 応答時はリフレッシュトークンで ID トークンを自動更新して 1 回リトライ。
  - ページネーション対応。id_token のモジュールレベルキャッシュを保持してページ間で共有。
  - 取得データを DuckDB に冪等的に保存する関数を提供（ON CONFLICT DO UPDATE を利用）: save_daily_quotes, save_financial_statements, save_market_calendar。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に処理。
  - fetched_at を UTC で記録し、Look-ahead バイアス回避に配慮。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能を実装（デフォルト: Yahoo Finance のビジネス RSS を含む）。
  - セキュリティ対策: defusedxml を利用した XML パース、SSRF 防止（リダイレクト事前検証、プライベートIPチェック）、HTTP スキーム検証、読み取りサイズ上限（10MB）や Gzip 解凍後サイズ検査。
  - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント除去）、記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理（URL除去、空白正規化）と銘柄コード抽出（4桁数字、known_codes フィルタ）。
  - DB 保存はチャンク化してトランザクションで実行、INSERT ... RETURNING により新規挿入IDを正確に取得（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - run_news_collection により複数ソースを独立して処理し、ソース単位の障害を他に波及させない設計。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義の基礎を実装。
  - raw_prices, raw_financials, raw_news, raw_executions 等の DDL を含む（初期化用モジュール）。
- 研究・特徴量探索 (kabusys.research)
  - feature_exploration モジュール
    - calc_forward_returns: 指定日に対する将来リターン（複数ホライズン）を DuckDB の prices_daily テーブルから計算。
    - calc_ic: スピアマンランク相関（IC）計算。欠損/非有限値を除去。レコード数不足（<3）で None を返す。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとするランク化関数（丸めで ties 検出の安定化）。
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。過去データ不足時は None。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range 計算では NULL 伝播を正確に制御。
    - calc_value: raw_financials の最新報告を用いて PER（EPS 非ゼロ時）、ROE を計算。prices_daily と結合。
  - 研究モジュール群は DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照。実行時に外部発注APIなどへアクセスしない設計。
  - kabusys.research パッケージの __all__ に主要関数を公開。
- 依存関係
  - defusedxml を利用して XML の安全なパースを行う（news_collector）。

### 変更 (Changed)
- -（初回リリースのため該当なし）

### 修正 (Fixed)
- -（初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集で以下のセキュリティ対策を導入:
  - XML 外部実行攻撃対策に defusedxml を使用。
  - SSRF 対策: リダイレクト先のスキームおよびホスト検証、IP のプライベートレンジ判定、初回ホスト検査。
  - URL スキームは http/https のみ許可。
- J-Quants クライアントは 401 応答時にトークンを自動リフレッシュするが、リフレッシュ処理は allow_refresh フラグで無限ループを防止。

### 注意事項 / 既知の制約 (Notes)
- DuckDB に依存するため、実行環境に duckdb パッケージが必要です。
- research モジュールは外部ライブラリに依存しない（標準ライブラリのみ）ことを目指していますが、実運用では pandas 等と組み合わせることが想定されます。
- NewsCollector の URL 正規化・ID 生成はトラッキングパラメータのプレフィックス固定リストに依存しています。必要に応じて追加が必要です。
- save_* 系関数は DuckDB のテーブルスキーマに依存します。スキーマ変更時は保存ロジックの更新が必要です。
- .env のパースは多くのケースを扱いますが、極端なエッジケースのカバーは限定的です（必要に応じて追加テスト推奨）。
- calc_forward_returns / factor 計算は営業日ベース（連続レコード数）での計算を前提としているため、休日を含むカレンダー日ベースの扱いに注意してください。

---

開発者・貢献者へ: 実装の意図や設計上の考慮点（例: Look-ahead バイアスの回避、冪等性、SSRF 対策、レート制限ポリシー等）は各モジュールの docstring に記載しています。追加の説明や変更履歴の補足が必要であればお知らせください。