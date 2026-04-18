# Keep a Changelog — CHANGELOG.md（日本語）
すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このプロジェクトでは Semantic Versioning を想定しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。自動売買システムのコアユーティリティと起動スクリプト、ポートフォリオ構築・リスク管理・検証ツール類をまとめて追加。

### Added
- 全体
  - パッケージ初版を追加（__version__ = 0.1.0）。
  - プロジェクトルート探索ロジックを実装し、.env / .env.local の自動読み込み機構を導入（kabusys.config）。
  - .env ファイルの対話式作成・更新ウィザードを追加（kabusys.config_setup）。
  - 設定検証 CLI を追加（kabusys.validate_config）。必須環境変数のチェック、DB パス・YAML 設定ファイルの存在確認、本番環境向けのガードを実装。
- 起動スクリプト
  - 実際の発注エンジン起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（data/paper_trading.db をデフォルト）。
    - BrokerClientFactory によるブローカークライアントの切替を行う仕組みを導入。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全な起動/停止制御。
    - ExecutionEngine をバックグラウンドスレッドで起動し、停止フラグ検知で安全に停止する制御ループ。
  - 監視ポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループを終了する安全な終了処理。
- データベース / 監視
  - 監視用 DB 初期化ヘルパーの呼び出しを追加（init_monitoring_db）。監視テーブルの存在を保証（冪等）。
- ロギング・プロセス制御
  - ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR 指定・自動作成、ログレベル解決ロジックを実装。ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX の差分を吸収して優先度を設定。アクセス権限や未対応環境はワーニングを出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定: select_candidates を追加（スコア降順・signal_rank によるタイブレーク）。
  - 重み計算: calc_equal_weights（等分配）、calc_score_weights（スコア正規化、全スコア0時は等分配にフォールバック）。
  - セクター制限・レジーム乗数: apply_sector_cap（既存保有のセクター比率が上限を超える場合に新規候補を除外）、calc_regime_multiplier（bull/neutral/bear に対する乗数）。
  - 株数算出・リスク制限: calc_position_sizes（risk_based / equal / score の配分方式に対応）。
    - 単元（lot_size）丸め、ポジション上限、aggregate cap によるスケーリング、コストバッファ (cost_buffer) の考慮、残差（fractional remainder）に基づく追加配分ロジックを実装。
- 研究（Research）
  - ファクター計算モジュールの追加（kabusys.research.factor_research）。
    - モメンタム等のファクター計算（モジュール設計・定数定義、momentum 計算の骨組み）を提供。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を計算して PASS/FAIL 判定を出力。
    - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - P95 計算、期間フィルタ、SQL の保護（テーブルがない場合の fallback）を実装。
- 設定パースの堅牢化
  - .env パーサー（_parse_env_line）を改善し、export プレフィックス、引用符付き値のエスケープ処理、インラインコメントの扱いを正しく処理するように実装。
  - .env の自動読み込みはプロジェクトルート検出に依存（.git or pyproject.toml）。OS 環境変数は保護され、.env.local は上書き可能。
- 設定モデル
  - Settings クラスを導入し、環境変数アクセスを集中管理（プロパティ経由）。値検証（有効な KABUSYS_ENV / LOG_LEVEL チェック、PAPER_FILL_MODE の検証 等）を行う。

### Changed
- 監視・実行フロー
  - 監視（run_monitoring）は環境に依らず production の sqlite_path を参照して監視データを一元化。
  - 実行（run_execution）は KABUSYS_ENV=paper_trading 時に paper_sqlite_path を使用して発注履歴を本番と分離。
- ログ出力
  - StreamHandler は stderr ではなく stdout に出力するように変更（cron/tmux 等で stdout/stderr をまとめて扱う運用を想定）。

### Fixed
- 設定検証（validate_config）
  - PyYAML 未インストール環境でも YAML 内容検証をスキップし、警告を出すようにして起動時のクラッシュを回避。
  - DB パスや親ディレクトリが存在しない場合でも明確な警告を出すように改善。
- ポートフォリオ
  - calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックして危険なゼロ除算を回避。

### Security
- 環境変数の取り扱いについて注意喚起を README/.env テンプレートに明記（.env を絶対にコミットしない等、config_setup が同様の警告を出力）。

### Notes / Operational
- 停止制御
  - 停止フラグ（data/stop_requested.flag）や kill flag などファイルベースの Kill Switch を採用。validate_config による KILL_FLAG_CLEAR_ON_START の本番ガードも導入。
- 設定必須項目
  - J-Quants と kabuステーション API に必要な必須環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）を Settings で必須化。validate_config で未設定やプレースホルダ値を検出して警告/エラーを出力。
- DuckDB/SQLite
  - DuckDB は分析用途、SQLite は監視・発注履歴用途で使い分け。デフォルトパスは .env / デフォルト値で管理。

---

今後の予定（例）
- factor_research の完全実装（Momentum/Value/Volatility/Liquidity の全実装）。
- strategy 周り（シグナル生成・バックテスト）モジュールの追加。
- 単体テスト・CI の整備、型チェック・lint の強化。
- broker 周りの抽象化強化とモックの追加。

お問い合わせや誤りの指摘は Issue を立ててください。