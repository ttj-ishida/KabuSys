# CHANGELOG

すべての注記は Keep a Changelog の慣習に準拠します。  
このファイルはソースコードから推測できる実装内容に基づいて作成しています。

全般の前提:
- 初期リリース v0.1.0 として実装された主要機能・設計上の配慮を記載しています。
- 実際のリリース日をリポジトリの状況に合わせて調整してください（ここではコード確認日を使用しています）。

## [Unreleased]

## [0.1.0] - 2026-03-18
### Added
- パッケージ基盤
  - 基本パッケージ定義を追加（kabusys.__init__ に version=0.1.0、公開モジュールリスト）。
- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準にルートを探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーを実装:
    - コメント・空行の無視、`export KEY=val` 形式のサポート。
    - シングル／ダブルクォート対応（バックスラッシュによるエスケープ処理含む）。
    - インラインコメントの取り扱い（クォート有無で挙動を区別）。
  - 環境変数読み込みの上書き制御（override）と保護（protected = OS 環境変数の保護）をサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能：
    - J-Quants / kabu API / Slack / DB パス（duckdb/sqlite） / 環境（development/paper_trading/live） / ログレベル判定 など。
    - 必須変数未設定時に ValueError を送出する _require() を備える。
    - env 値と log_level のバリデーション。

- Data 層（kabusys.data）
  - J-Quants API クライアント（kabusys.data.jquants_client）を実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter。
    - HTTP リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を再取得して 1 回リトライする仕組み。
    - ページネーション対応で /prices/daily_quotes, /fins/statements, /markets/trading_calendar の取得関数を実装。
    - JSON デコードエラーやネットワークエラーの取り扱いを実装。
    - DuckDB への保存関数を用意（冪等性を考慮し ON CONFLICT を使った upsert）:
      - save_daily_quotes: raw_prices への保存（fetched_at を UTC ISO 形式で記録）。
      - save_financial_statements: raw_financials への保存。
      - save_market_calendar: market_calendar への保存（holidayDivision を解釈して is_trading_day / is_half_day / is_sq_day を格納）。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し堅牢なパースを行う。
  - ニュース収集モジュール（kabusys.data.news_collector）を実装:
    - RSS フィードの取得と記事抽出を実装（デフォルトソース: Yahoo Finance のカテゴリRSS）。
    - defusedxml を使った安全な XML パース（XML Bomb 等への対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定しアクセス拒否。
      - リダイレクト時も検査するカスタム RedirectHandler を利用。
    - 受信バイト数制限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズチェックを追加（メモリ DoS 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリパラメータソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭32文字）を実装し冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）と RSS pubDate の安全なパース。
    - raw_news テーブルへのバルク保存（チャンク挿入、INSERT ... RETURNING により実際に挿入された ID を返す）。トランザクションでロールバックを保証。
    - news_symbols テーブルへの銘柄紐付けのための一括保存ユーティリティ（重複除去、チャンク挿入）。
    - 銘柄コード抽出ロジック（正規表現で 4 桁数字を抽出し、既知コードセットによるフィルタリング）。
    - 集約ジョブ run_news_collection を実装（ソース単位で独立してエラーハンドリング、既知銘柄が与えられた場合は紐付けを実行）。
- Research 層（kabusys.research）
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト: 1,5,21 営業日）における将来リターンを DuckDB の prices_daily から一度のクエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。欠損や ties を適切に処理し、有効データ点が 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを与えるランク付け実装（比較前に round(..., 12) して浮動小数誤差対策）。
    - factor_summary: count/mean/std/min/max/median を算出（None と非有限値を除外）。
    - これらは外部ライブラリに依存せず、標準ライブラリと duckdb を用いる設計。
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。過去データが不足する場合は None を返す。
    - calc_volatility: atr_20（20日平均 true range）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio（当日/20日平均）を計算。true_range の NULL 伝播を明示的に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを結合し PER（EPS が 0 または欠損なら None）と ROE を計算。
    - DuckDB のウィンドウ関数を活用して効率的に計算（LAG, AVG OVER, COUNT OVER, ROW_NUMBER を使用）。
    - 計算範囲は週末/祝日を吸収するためにカレンダーバッファ（日数 × バッファ）を設定。
  - research パッケージ __init__ で主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize を含む想定）。
- スキーマ / 初期化（kabusys.data.schema）
  - DuckDB 用の DDL 定義を追加（Raw Layer を中心に raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む）。
  - 各テーブルに対する CHECK 制約や PRIMARY KEY を定義し、データ品質を担保する設計。

### Changed
- （初期リリースのため「変更」はなし。将来のリリースで差分を記載予定。）

### Fixed
- （初期リリースのため「修正」はなし）

### Security
- ニュース収集において複数のセキュリティ対策を実装:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム制限、プライベートホスト検出、リダイレクト時の検証）。
  - レスポンスサイズ制限と gzip 解凍後サイズチェック（DoS 緩和）。
- J-Quants クライアントは 401 発生時にトークン自動リフレッシュを行うが、無限再帰を避けるため allow_refresh フラグを導入。

### Deprecated
- （初期リリースのためなし）

### Removed
- （初期リリースのためなし）

### Notes / TODO（ソースコードから推測される今後の改善候補）
- Execution 層のテーブル定義（raw_executions 等）はスニペットで途中まで実装されており、発注/約定/ポジション管理周りの実装が続く想定。
- zscore_normalize 等の統計ユーティリティは kabusys.data.stats に実装されている前提だが、その内容は本差分に含まれていないため、ドキュメント整備や統合テストが必要。
- J-Quants の保存処理で DuckDB のスキーマ（raw_prices, raw_financials 列型等）がコードと一致するかを検証するための schema migration / バリデーションの追加を推奨。
- NewsCollector の外部依存（defusedxml）はセキュリティに重要なため、依存バージョン管理と定期的な監査が望ましい。

---

（必要に応じて日付・バージョン・詳細を調整してください）