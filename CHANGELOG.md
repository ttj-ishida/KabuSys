# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 今後のリリースでの改善候補や未実装機能（README / ドキュメント化、銘柄別単元対応、トレーリングストップ等）。

## [0.1.0] - 2026-03-26
初回公開リリース。日本株自動売買システムのコアライブラリを提供します。以下は主な追加点・仕様の要約です。

### Added
- パッケージ基本情報
  - パッケージバージョンを __version__ = "0.1.0" として定義（src/kabusys/__init__.py）。
  - 主要サブパッケージを __all__ でエクスポート（data, strategy, execution, monitoring）。

- 環境設定管理
  - 環境変数/ .env ファイルの自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export 構文・クォート／エスケープ処理・インラインコメントに対応する堅牢な .env パーサを実装。
    - OS 環境変数を保護する protected 上書き制御をサポート。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）やデフォルト値（KABU_API_BASE_URL、DB パス等）を取得・バリデーション可能に。
  - 環境（development / paper_trading / live）とログレベルの検証ロジックを実装。

- ポートフォリオ構築 (Portfolio)
  - 銘柄選定と配分ロジック（pure functions、DB参照なし）
    - select_candidates: スコア降順＋タイブレークで上位 N を選定（src/kabusys/portfolio/portfolio_builder.py）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の重み計算。全スコアが0の場合は等配分へフォールバック。
  - リスク調整
    - apply_sector_cap: セクター別エクスポージャーを計算し、指定上限を超えるセクターの新規候補を除外（当日売却予定銘柄は除外可能）。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear)に基づく投下資金乗数を返す（未定義レジームはフォールバックして1.0）。Bear に対する注意喚起（主に BUY シグナルの生成は別設計で抑制）。
  - ポジションサイジング
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて発注株数を算出（単元丸め、最大ポジション比率、aggregate cap、cost_buffer を考慮）。スケールダウン時の残差配分ロジック（lot 単位での再配分）を実装。

- 戦略（Strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価、最低売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップして features テーブルへ日付単位の置換（UPSERT）で書き込み。
    - DuckDB 接続を受け取り原子性のあるトランザクションで処理。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し、重み付き合算で final_score を算出。
    - AI スコアはシグモイド変換、未登録は中立で補完。
    - Bear レジーム検知時には BUY シグナルを抑制（ai_scores の regime_score を集計して判定）。
    - BUY は閾値（デフォルト 0.60）超で生成、SELL はストップロス（-8%）とスコア低下で判定。SELL を優先して BUY から除外。
    - signals テーブルへの日付単位置換で冪等性を保証。

- 研究ツール（Research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日ATR/相対ATR、平均売買代金、出来高比率）、Value（PER/ROE）を DuckDB 上で算出。データ不足時は None を返す設計。
  - 特徴量探索/統計（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（任意ホライズン、複数ホライズンを1クエリで取得）。
    - IC（Spearman の ρ）計算 calc_ic（ランク処理に平均ランク、3サンプル未満は None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティを提供。
  - research パッケージは zscore_normalize を再エクスポート。

- バックテスト（Backtest）
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades を計算するユーティリティを追加。
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator クラス: メモリ内でポートフォリオ状態管理、約定処理（SELL 先行、BUY 後処理）、スリッページ／手数料の適用、TradeRecord / DailySnapshot の履歴保持。
    - TradeRecord と DailySnapshot のデータクラスを定義。

- パッケージ API 整備
  - strategy, portfolio, research など主要機能を __init__ でエクスポートして利用しやすく整理。

### Changed
- 初回リリースのため、後方互換や既存 API からの変更は無し（初版）。

### Fixed
- 初期実装リリースのため bug fix 履歴はなし。ただし各モジュールに警告ロギングやデータ欠損時の安全策（例: 価格欠損時に SELL 判定をスキップ）を組み込んでいる。

### Known issues / TODO（設計上の注意）
- .env 読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- portfolio.position_sizing:
  - 銘柄別の lot_size を将来的にサポート予定（現状は全銘柄共通の lot_size 引数）。
  - price が欠損（0.0）の場合、apply_sector_cap のエクスポージャーが過少見積もられる可能性がある（将来的にフォールバック価格を検討）。
- signal_generator:
  - トレーリングストップや保有日数による時間決済は未実装（positions に peak_price / entry_date 情報が必要）。
- research.calc_ic:
  - 有効レコードが少ない場合は None を返す仕様（3件未満）。
- ドキュメント化:
  - 各設計ドキュメントへの参照（PortfolioConstruction.md、StrategyModel.md 等）はコード内コメントで明示しているが、パッケージ外部の詳細ドキュメント整備は今後の課題。

### Security
- 環境変数内の機密情報は Settings 経由で取得する実装。ログ出力等で秘匿情報が出力されないよう注意すること。

---

今後の予定:
- 銘柄別単元対応、トレーリングストップ等のエグジット条件追加、より詳細なコストモデル・取引所ルール対応、ドキュメントの拡充を予定しています。