# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現時点なし）

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージのエントリポイントを定義（src/kabusys/__init__.py）。version = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring。

- 設定・環境変数読み込み (src/kabusys/config.py)
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env 読み込み時の上書き挙動制御（override / protected）。
  - .env ファイルの行パーサーを実装（export 形式、クォート処理、インラインコメント対応）。
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require()、Settings クラスを提供。
  - サポートする設定例:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- データ取得/永続化（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装（/prices/daily_quotes, /fins/statements, /markets/trading_calendar）。
  - レート制限（120 req/min）のための固定間隔スロットリング実装（内部 _RateLimiter）。
  - リトライ（指数バックオフ、最大3回）とステータス判定（408/429/5xx をリトライ対象）。
  - 401 受信時の自動トークンリフレッシュロジック（1回のみリフレッシュして再試行）。
  - ページネーション対応（pagination_key を継続取得）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。冪等性確保のため ON CONFLICT DO UPDATE を使用。
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead bias のトレースを可能に。
  - 型変換ユーティリティ (_to_float, _to_int) による堅牢なデータ正規化。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得 → テキスト前処理 → raw_news 保存 → 銘柄紐付け のワークフローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 防止: URL スキーム検証（http/https のみ）、リダイレクト時のホスト検査、プライベートIP/ループバック/リンクローカルのブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と Gzip 解凍後の再チェック。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去・空白正規化）。
  - RSS の pubDate を UTC naive datetime に正規化するヘルパー。
  - DB 保存はチャンク化してトランザクション内で一括挿入、INSERT ... RETURNING を用いて実際に挿入された記事IDを返す実装（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出ユーティリティ（4桁数字パターン + known_codes フィルタ）。
  - デフォルト RSS ソースに Yahoo Finance（businessカテゴリ）を設定。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw レイヤーの DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。
  - DataSchema に基づく3層（Raw / Processed / Feature / Execution）の方針を明記。

- リサーチ（特徴量・ファクター計算）モジュール
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算 calc_forward_returns（複数ホライズン同時取得、SQL で一括取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ、ランク計算 rank を内部実装）。
    - ファクター統計サマリー factor_summary（count/mean/std/min/max/median）。
    - 標準ライブラリのみで実装（pandas などに依存しない設計）。
  - factor_research (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を DuckDB のウィンドウ関数で計算。
    - calc_volatility: 20日 ATR / atr_pct、20日平均売買代金、出来高比率 を計算（true_range の NULL 伝播に配慮）。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS や欠損時は None）。
    - 各関数は prices_daily / raw_financials のみを参照し、本番 API にはアクセスしない方針。
  - research パッケージ初期化で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### セキュリティ / 信頼性 (Security / Reliability)
- ニュース収集での SSRF 対策、XML パースの安全化、レスポンスサイズ制限、gzip ボム対策を導入。
- J-Quants クライアントでのリトライ/バックオフとトークン自動リフレッシュにより一時的なネットワーク障害や認証切れに耐性を持たせた。
- DuckDB への書き込みは冪等化（ON CONFLICT）・トランザクション制御を行いデータ一貫性を確保。

### 実装上の注意 / 既知の制限 (Notes / Known limitations)
- feature_exploration および factor_research はパフォーマンス配慮で SQL のウィンドウ関数を多用しています。大規模データでは DuckDB の設定やクエリ最適化に注意してください。
- news_collector の銘柄抽出は単純な 4 桁数字マッチに依存しており、文脈誤検出を完全には排除できません。known_codes を渡してフィルタリングすることを推奨します。
- _to_int は "1.9" のような非整数文字列を None に変換する保守的な実装です。外部データの形式に応じて調整してください。
- research モジュールは pandas 等に依存せず標準ライブラリで実装されています。既存のデータ分析ツールとの連携や高度な統計処理が必要な場合は拡張を検討してください。
- DDL の定義は一部（raw_executions の続きなど）がこの差分で断片的に提示されています。完全なスキーマはリポジトリ内の DataSchema.md / schema モジュール全体を参照してください。

### 変更点 (Changed)
- 初回公開のため該当なし。

### 修正 (Fixed)
- 初回公開のため該当なし。

### 削除 / 非推奨 (Removed / Deprecated)
- 初回公開のため該当なし。

---

今後のリリースでは、strategy / execution / monitoring の具体的な発注ロジック、バックテスト機能、CI テストケース、ドキュメントの追加などを予定しています。質問や補足が必要であればお知らせください。