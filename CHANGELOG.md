# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
初期リリースはバージョン `0.1.0` として公開されています。

## [Unreleased]

（現時点のコードベースは初期リリース相当のため、未リリース変更はありません。）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期構成を追加
  - パッケージメタ情報: `src/kabusys/__init__.py`（`__version__ = "0.1.0"`、公開 API の `__all__` を定義）。
- 環境変数 / 設定管理
  - `src/kabusys/config.py`
    - プロジェクトルート検出ロジックを実装（`.git` または `pyproject.toml` を基準に探索）。
    - `.env` / `.env.local` の自動読み込み機能を実装（読み込み順: OS > .env.local > .env）。
    - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `.env` のパース実装（`export KEY=val`、引用符内のエスケープ、インラインコメントの扱い等に対応）。
    - 上書き制御（`override`）と OS 環境変数保護（`protected`）に対応したロード処理。
    - 必須設定取得ヘルパー `_require`（未設定時は `ValueError` を送出）。
    - 設定オブジェクト `Settings` を提供（J-Quants / kabu / Slack / DB パス / 環境・ログレベル検証など）。
- Data 層: J-Quants API クライアント
  - `src/kabusys/data/jquants_client.py`
    - 固定間隔の RateLimiter（120 req/min）を実装。
    - 冪等性・ページネーション対応の取得関数（`fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`）。
    - リトライ（指数バックオフ、最大 3 回）・HTTP ステータス別処理（408/429/5xx）を実装。
    - 401 を受けた場合の ID トークン自動リフレッシュと再試行（トークンキャッシュも実装）。
    - DuckDB へ保存する冪等保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を提供（ON CONFLICT を使用して更新）。
    - ユーティリティ `_to_float` / `_to_int` による堅牢な型変換。
    - fetched_at を UTC ISO8601 で記録して Look-ahead バイアスの追跡を考慮。
- Data 層: ニュース収集
  - `src/kabusys/data/news_collector.py`
    - RSS フィード収集のフレームワーク（デフォルト RSS ソース、最大受信サイズ制限）。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - defusedxml を使った安全な XML パース（XML Bomb などを防止）。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - DB へのバルク保存（チャンク処理、トランザクション、ON CONFLICT/DO NOTHING を想定）と news—symbol 紐付けを考慮。
- Research 層（リサーチ用ファクター計算・解析）
  - `src/kabusys/research/factor_research.py`
    - Momentum ファクター計算（1m/3m/6m リターン、MA200 乖離）。
    - Volatility / Liquidity ファクター計算（20日 ATR、ATR/close、20日平均売買代金、出来高比率）。
    - Value ファクター計算（PER、ROE） — raw_financials と prices_daily を結合して算出。
    - 各関数は DuckDB の `prices_daily` / `raw_financials` テーブルを参照する純粋関数。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算ユーティリティ `calc_forward_returns`（任意ホライズン、単一 SQL クエリで取得）。
    - IC（Spearman の ρ）計算ユーティリティ `calc_ic`（ランク相関、サンプル不足時は None）。
    - 基本統計量集計 `factor_summary`（count/mean/std/min/max/median）。
    - ランク付けユーティリティ `rank`（同順位は平均ランク、丸めで ties 対策）。
  - `src/kabusys/research/__init__.py` で主要関数群を公開。
- Strategy 層（特徴量・シグナル生成）
  - `src/kabusys/strategy/feature_engineering.py`
    - 研究環境で計算した生ファクターを正規化・合成して `features` テーブルへ保存するワークフローを実装。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）と ±3 のクリップを実装。
    - 日付単位の置換（DELETE + bulk INSERT）で冪等性と原子性を担保（トランザクション使用）。
  - `src/kabusys/strategy/signal_generator.py`
    - `features` と `ai_scores` を統合して最終スコア（final_score）を計算し、BUY / SELL シグナルを生成。
    - デフォルト重み、閾値（デフォルト BUY=0.60）、スコア計算（モメンタム/バリュー/ボラティリティ/流動性/ニュース）を実装。
    - Sigmoid / 平均化等のユーティリティ、欠損コンポーネントの中立補完（0.5）を実装。
    - Bear レジーム判定（AI レジームスコア平均が負かどうか。最低サンプル数チェックあり）で BUY を抑制。
    - 保有ポジションのエグジット判定（ストップロス -8%、スコア低下）を実装。SELL を優先し BUY から除外。
    - 日付単位の置換で `signals` テーブルへ書き込み（トランザクション + bulk INSERT）。
  - `src/kabusys/strategy/__init__.py` で主要 API (`build_features`, `generate_signals`) を公開。
- その他
  - `src/kabusys/execution/__init__.py` を追加（実行層のパッケージプレースホルダ）。
  - ロギング利用（各モジュールで logger を使用、重要な警告や操作ログを出力）。

### Changed
- 初回リリースのため該当なし（初期追加のみ）。

### Fixed
- 初回リリースのため該当なし（初期追加のみ）。

### Security
- news_collector で defusedxml を利用するなど、外部入力（XML/URL）に対する安全対策を盛り込んでいる。
- J-Quants クライアントはトークン管理とネットワークエラー処理・リトライを実装し、401 の場合はトークンを更新して再試行することで認証漏れを低減。

### Notes
- このリリースは「研究・バックテスト環境」を主目的として機能実装されています。実際の注文発注や本番口座操作への直接的な依存は避ける設計です（execution 層は別実装を想定）。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などは `Settings` 経由で必須チェックされます。`.env.example` を参照して `.env` を作成してください。
- DuckDB（接続オブジェクト）を前提とする関数が多く含まれます。使用時は適切なスキーマ（`raw_prices`, `raw_financials`, `prices_daily`, `features`, `signals`, `ai_scores`, `positions`, `market_calendar` 等）を準備してください。

---

参考: バージョンポリシーや今後の変更履歴はこの CHANGELOG.md に追記してください。