# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  
リリースはセマンティックバージョニングに従います。

現在日付: 2026-03-19

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-19
最初の公開リリース。日本株自動売買システムのコアライブラリを実装しました。以下の主要なモジュール・機能を含みます。

### Added
- パッケージエントリポイント
  - `kabusys` パッケージを追加。`__version__ = "0.1.0"`、公開 API として `data`, `strategy`, `execution`, `monitoring` を公開。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルの自動読み込み機構（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local（上書き） > .env（未設定時のみセット）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 1行パーサ（コメント、export プレフィックス、クォート、エスケープ、インラインコメントの取り扱い）を実装。
  - 必須チェック用の `Settings` クラスを提供。主なプロパティ:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - 環境: `env`（許可値: `development`, `paper_trading`, `live`）、`log_level`（許可値: DEBUG/INFO/WARNING/ERROR/CRITICAL）、および `is_live`, `is_paper`, `is_dev` ヘルパー。

- Data 層（kabusys.data）
  - J-Quants クライアント（kabusys.data.jquants_client）
    - API 呼び出しユーティリティ `_request` を実装（JSON デコード検証、再試行・指数バックオフ、429 の Retry-After 対応、401 時の自動トークンリフレッシュ）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - ページネーション対応のデータ取得関数:
      - `fetch_daily_quotes`
      - `fetch_financial_statements`
      - `fetch_market_calendar`
    - DuckDB へ冪等に保存する関数:
      - `save_daily_quotes` → `raw_prices` テーブルへ（ON CONFLICT DO UPDATE）
      - `save_financial_statements` → `raw_financials` テーブルへ（ON CONFLICT DO UPDATE）
      - `save_market_calendar` → `market_calendar` テーブルへ（ON CONFLICT DO UPDATE）
    - 入力変換ユーティリティ `_to_float` / `_to_int`（型安全な変換・失敗時は None）。

  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードから記事取得・正規化を行う下地を実装（デフォルトソースに Yahoo Finance を含む）。
    - セキュリティ対策: defusedxml の利用、受信サイズ制限（10MB）、HTTP スキーム検証、URL 正規化（トラッキングパラメータ削除、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）を生成して冪等性を確保。
    - バルク挿入チャンク／トランザクションを意識した設計。

- Research 層（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - Volatility（atr_20、atr_pct、avg_turnover、volume_ratio）
    - Value（per、roe） — raw_financials から最新財務データを参照
    - DuckDB の SQL＋ウィンドウ関数を用いた実装（営業日欠損・窓サイズチェックあり）
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（rank, ties は平均ランクで処理）
    - ファクター統計サマリー（count/mean/std/min/max/median）
  - zscore 正規化ユーティリティをエクスポート（kabusys.data.stats から利用可能）

- Strategy 層（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。
    - DuckDB の `features` テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
    - 冪等性を担保。
  - シグナル生成（kabusys.strategy.signal_generator）
    - `features` と `ai_scores` を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントの欠損は中立 0.5 で補完。
    - デフォルト重み（momentum 0.4, value 0.2, volatility 0.15, liquidity 0.15, news 0.1）を提供。引数で一部重み変更可（検証・正規化あり）。
    - final_score が閾値（デフォルト 0.60）以上で BUY シグナルを生成。ただし Bear レジーム（ai_scores の regime_score 平均が負、かつサンプル数 >= 3）時は BUY を抑制。
    - 保有ポジションに対する SELL 条件を実装:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
    - `signals` テーブルへ日付単位で置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
    - SELL シグナル優先ポリシー（SELL 対象は BUY から除外しランク再付与）。
    - ロギングによる診断情報を出力。

- その他
  - 研究・戦略設計ドキュメント（StrategyModel.md / DataPlatform.md 等）を参照する設計方針に従った実装コメントを多数追加。
  - 多くの箇所で不正データや欠損に対する堅牢化（None / NaN / 非有限値の扱い、ログ出力、スキップ処理など）を行った。

### Changed
- N/A（初回リリースのため変更履歴なし）

### Fixed
- N/A（初回リリース）

### Known limitations / Notes
- ニュース記事と銘柄の紐付け（news_symbols）や記事テキスト解析の上流処理は骨格を用意しているが、完全な紐付けロジックや NLP 処理は追加実装が必要。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済 - 保有 60 営業日超過）は未実装（comments に明記）。positions テーブルに peak_price / entry_date が必要。
- 一部 SQL は DuckDB の機能（ウィンドウ関数、ROW_NUMBER 等）に依存。利用時は対応するテーブルスキーマを用意すること。
- J-Quants クライアントは HTTP 経路の例外処理・リトライを備えるが、実際の API 仕様変更やスキーマ差分に対しては堅牢性テストが必要。
- auto .env ロードはプロジェクトルート検出に __file__ を用いるため、特殊なパッケージ配置では想定通り動作しない可能性あり。必要なら `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用して手動ロードすること。

### Migration notes
- なし（初回リリース）。

### Security
- XML パースに defusedxml を使用。
- RSS 受信にサイズ制限を課すなど DoS/BOM/SSRF に配慮した実装を行っている。ただし外部入力は常に注意して取り扱うこと。

---

作成・保守: kabusys 開発チーム（実装コメントより推定）