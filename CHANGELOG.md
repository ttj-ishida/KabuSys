# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-18

初期リリース。日本株自動売買システム "KabuSys" の基礎的なモジュール群を実装しました。
主な追加点は以下のとおりです。

### Added
- パッケージメタ情報
  - kabusys.__init__ にバージョン情報 __version__ = "0.1.0" と、公開 API を定義する __all__ を追加。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート判定は .git / pyproject.toml）。
  - 自動ロードを無効にするための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env ファイルのパースロジックを実装（コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理などを考慮）。
  - .env 読み込みで OS 環境変数を保護する protected 機構を実装（.env.local は既存値を上書き可能）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境フラグ（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
  - 必須設定未提供時に ValueError を投げる _require ヘルパーを追加。

- Data 層: J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API から日足・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - レート制限（120 req/min）のための固定間隔スロットリング _RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大リトライ回数、429/408/5xx ハンドリング）を実装。
  - 401 応答時にリフレッシュトークンからの自動トークン再取得を1回だけ行う機構を実装（無限再帰対策あり）。
  - ページネーション対応（pagination_key）を実装した fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等的保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。INSERT ... ON CONFLICT で重複を更新。
  - 型変換ユーティリティ _to_float / _to_int を実装（空値や不正文字列の安全処理、"1.0" のような文字列を int として扱うロジックなど）。

- Data 層: ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュースを収集し raw_news / news_symbols に保存する処理を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキームとホスト検証、プライベート/ループバック/リンクローカル/マルチキャストアドレスをブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックと gzip 解凍後の再チェック（Gzip bomb 対策）。
  - URL 正規化機能（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）と、正規化 URL から SHA-256 を使って先頭32文字を記事ID として生成する仕組み。
  - テキスト前処理（URL 除去、空白正規化）を提供。
  - RSS 取得時の堅牢なフォールバック（channel/item の有無・content:encoded の優先）を実装。
  - DB 保存: チャンク分割・トランザクション・INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いた効率的な保存（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 記事中から銘柄コード（4桁数値）を抽出する extract_stock_codes を実装。known_codes によるフィルタと重複排除。

- Data 層: DuckDB スキーマ (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義モジュールを追加。
  - raw_prices, raw_financials, raw_news, raw_executions などのDDL定義を追加（NOT NULL 制約・チェック制約・主キー等を含む）。

- Research 層: ファクター計算・調査ユーティリティ (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1/5/21 営業日）までの将来リターンを一度のクエリで取得する実装。ホライズンの妥当性チェックあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（Information Coefficient）を計算。非有限値や None を除外し、有効データ数が少ない場合は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク化ユーティリティ（浮動小数の丸めによる ties 対策で round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m/ma200_dev を prices_daily 参照で計算。必要行数不足は None 処理。ウィンドウ・スキャン範囲の最適化（バッファ）を実装。
    - calc_volatility: ATR(20) / atr_pct / avg_turnover / volume_ratio を計算。true_range の NULL 伝播を正確に制御し、カウント閾値未満なら None を返す。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER/ROE を計算。price と財務を結合して返す。
  - いずれの関数も DuckDB 接続を受け取り SQL による集計を行い、本番 API にはアクセスしない方針を明記。

- Research パッケージの公開 API
  - kabusys.research.__init__ で主要関数（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をエクスポート。

### Changed
- （新規リリースのため該当なし）

### Fixed
- （新規リリースのため該当なし）

### Security
- news_collector の RSS 処理において以下の防御を追加:
  - defusedxml による安全な XML パース
  - SSRF 対策（スキーム/ホスト検査、リダイレクト時の検証）
  - レスポンスサイズ限界と gzip 解凍後のサイズチェック（DoS/Gzip bomb 対策）

### Notes / Implementation details
- DuckDB への保存はできるだけ冪等に実装（ON CONFLICT DO UPDATE / DO NOTHING を多用）。
- 外部依存をできるだけ限定（research の解析は標準ライブラリ + DuckDB のみ）し、実運用での安全性と再現性を重視した設計になっています。
- 設定周りは開発/ペーパー/ライブの環境区別とログレベルのバリデーションを備えています。
- J-Quants クライアントではトークンキャッシュをモジュールレベルで保持し、ページネーション間でのトークン共有と自動再取得を行います。

---

今後の予定（例）
- Execution 層の発注 API 実装（kabuステーション連携）
- Strategy 層のバックテスト・ポートフォリオ最適化機能の追加
- CI 用の .env テストカバレッジ拡充

（必要ならば、各モジュールごとの細かな変更点や API 使用例を追加で出力できます。）