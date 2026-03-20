Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

[0.1.0] - 2026-03-20
--------------------

Added
- 基本パッケージ初期リリース。
  - パッケージバージョン: 0.1.0
  - パッケージトップ: kabusys.__init__ にて data, strategy, execution, monitoring を公開。

- 環境設定
  - kabusys.config: .env ファイルまたは環境変数から設定を読み込む機能を追加。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により作業ディレクトリに依存しない自動読み込みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パース実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応）。
    - 環境変数取得のユーティリティ _require と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / システム設定など）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許可値に対する検証とエラー報告）。

- Data 層（J-Quants クライアント等）
  - kabusys.data.jquants_client:
    - J-Quants API クライアント実装（HTTP リクエスト、ページネーション対応）。
    - レート制限制御: 固定間隔スロットリング（120 req/min、モジュールレベルの RateLimiter）。
    - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx のリトライをサポート。
    - 401 応答時の自動トークンリフレッシュ（1 回のみ実施）とモジュールレベルの ID トークンキャッシュ。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE による冪等保存）。
    - 入出力変換ユーティリティ _to_float / _to_int を実装（安全な型変換と不正値処理）。
    - fetched_at を UTC ISO 形式で記録し、look-ahead bias のトレーサビリティを確保。

  - kabusys.data.news_collector:
    - RSS フィードからのニュース収集機能を実装（defusedxml による安全な XML パース）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリソート）と記事 ID（正規化 URL の SHA-256 先頭）による冪等性確保。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）、SSRF 対策の設計指針、挿入バルクサイズ制御などを導入。
    - raw_news / news_symbols 連携を想定した設計。

- Research 層
  - kabusys.research.factor_research:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（per, roe）等のファクター計算関数を実装（prices_daily / raw_financials を参照）。
    - 各ファクターはデータ不足や条件不成立の場合に None を返すよう安全設計。
    - 日付スキャン範囲や窓サイズ等の定数を定義（例: MA200, ATR20, 20/63/126 日等）。

  - kabusys.research.feature_exploration:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日がデフォルト）。
    - IC（Spearman の ρ）計算 calc_ic とランク化ユーティリティ rank（同順位は平均ランク）を提供。
    - factor_summary による列ごとの基本統計量（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を用いず、標準ライブラリ + duckdb で動作。

  - kabusys.research.__init__ による研究 API の再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- Strategy 層
  - kabusys.strategy.feature_engineering:
    - 研究側の raw factor を読み取り、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化: zscore_normalize を利用し指定カラムを Z スコア化、±3 でクリップ。
    - features テーブルへの日付単位 UPSERT（削除→挿入、トランザクションで原子性確保）を実装。
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用する設計。

  - kabusys.strategy.signal_generator:
    - features と ai_scores を統合して最終スコア final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ保存（冪等）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を計算し、重みづけ合算（デフォルト重みを提供）。
    - 重みは入力で上書き可能だが検証（数値チェック、負値無視、合計が 1.0 に正規化）を行う。
    - Sigmoid 変換や None を中立値 0.5 で補完するロジックにより欠損銘柄の過度な降格を防止。
    - Bear レジーム判断: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル不足時は抑制しない）。
    - SELL 条件（実装済み）: ストップロス（-8%）および final_score の閾値未満でのエグジット。保有銘柄の価格欠損時は判定スキップする安全措置。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で原子性を保証。

Changed
- 研究／戦略モジュールの設計方針を明確化（ルックアヘッドバイアス対策、外部 API 非依存、DuckDB ベース設計）。

Fixed
- N/A（初回リリースのため該当なし）。

Documentation
- 各モジュールに docstring ベースの処理フロー、設計方針、引数・戻り値を充実させ、コードリーディングのみで挙動が理解できるように改善。

Known issues / Not implemented
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は positions テーブルの拡張（peak_price / entry_date 等）が必要で現時点では未実装。該当箇所に TODO コメントあり。
- news_collector の細かいフィード設定や重複判定ポリシーは運用に応じた微調整が必要。
- 一部の SQL は DuckDB 固有機能を利用しており、他の SQL ランタイムではそのまま動作しない可能性がある。

Migration / Upgrade notes
- 環境変数を .env にまとめる場合、.env.example を参照して必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。未設定時は Settings のプロパティアクセスで ValueError が発生します。
- 自動 .env 読み込みをテスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar 等）が必要です。初期スキーマは別途用意してください。

Authors
- 初回実装（内部ドキュメントとモジュール設計に沿って実装）。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0