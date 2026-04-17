# CHANGELOG

すべての notable な変更は、このファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリース日はコード内の日付/コメントや現在の状態から推測して付与しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-17
初回公開リリース。以下の主要機能・ユーティリティを含みます。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - DuckDB と SQLite を併用するローカル分析／監視基盤を実装（設定可能なパスを環境変数で指定可能）。
  - 環境変数・設定管理を行う `kabusys.config.Settings` を追加。.env 自動読み込み（.env, .env.local）と、読み込み抑止用のフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境変数読み書き用の対話式ウィザード `kabusys.config_setup` を追加（.env の初期作成/更新を支援）。
  - 起動前設定検証 CLI `kabusys.validate_config` を追加（必須環境変数や config/*.yaml の存在・パース確認、複数レベルの警告/エラー表示）。
  - 実行系／監視系の起動スクリプトを提供:
    - `kabusys.run_execution` — ExecutionEngine を起動するスクリプト。KABUSYS_ENV に応じて paper_trading 用 DB 分離、MockBroker の利用をサポート。停止フラグ/PID 管理とデーモンスレッドでの実行停止を実装。
    - `kabusys.run_monitoring` — SystemMonitor のポーリングループ起動スクリプト。ポーリング間隔を `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（デフォルト 60 秒）。監視は環境に依らず本番の sqlite_path を使用。
  - Paper Trading 検証レポート生成ツール `kabusys.tools.paper_verification_report` を追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計・判定し PASS/FAIL を出力。
  - ポートフォリオ構築モジュール (`kabusys.portfolio`) を追加:
    - 候補選定: `select_candidates`（スコア降順・タイブレークロジック有り）
    - 重み算出: `calc_equal_weights`, `calc_score_weights`（スコアが全て 0 の場合は等配分にフォールバック）
    - リスク調整: `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合に新規候補を除外）、`calc_regime_multiplier`（レジームに応じた資金乗数: bull/neutral/bear をサポート。未知レジームはフォールバック）
    - 口数算出: `calc_position_sizes`（allocation_method により "risk_based"/"equal"/"score" をサポート。単元株丸め、aggregate cap スケーリング、cost_buffer を考慮した調整を実装）
  - 研究用ファクター計算モジュール `kabusys.research.factor_research` を追加。DuckDB 接続を受け取り:
    - momentum ファクター（1M/3M/6M リターン、MA200 乖離）
    - volatility / liquidity 指標（ATR20、20日平均売買代金、出来高比など）
    - データ不足時は適切に None を返す設計
  - プロセス優先度・CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加。Windows と POSIX 系を吸収し、`set_process_priority` / `set_cpu_affinity` を提供。権限不足や未対応プラットフォーム時は警告を出して安全にスキップ。

### Changed
- N/A（初回リリースのため無し）

### Fixed
- N/A（初回リリースのため無し）

### Documentation
- 各モジュールに docstring／使用例を付与。主要 CLI の使い方や注意点（.env を Git にコミットしない等）を明記。

### Design / Implementation Notes（補足）
- DB 分離:
  - paper_trading 環境時は paper 用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離する設計。
  - Monitoring コンポーネントは意図的に本番 monitoring DB（`SQLITE_PATH`）を参照する仕様。
- .env パーサ:
  - `export KEY=val` 形式、シングル/ダブルクォートでの値、バックスラッシュによるエスケープ、インラインコメントの扱いなどに対応した堅牢なパーサ実装。
- Safety / Operational Controls:
  - 停止フラグファイル（data/stop_requested.flag 等）を用いた安全な終了制御、PID ファイル管理、`KILL_FLAG_CLEAR_ON_START` の注意喚起（validate_config での警告）を備える。
- Risk Management:
  - デフォルトの RiskManager 設定例を提供（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。initial_portfolio_value は broker の利用可能現金から取得。
- Position Sizing:
  - 単元株（lot_size）での丸め、利用可能現金を超える場合のスケーリングと残余分配ロジックを実装。価格欠損時はスキップして安全に動作。
- Research SQL:
  - DuckDB 上で完結する SQL ベースの計算を採用。営業日ベースの窓計算や欠損値の扱いに注意している（CNT 条件や NULL 伝播制御）。

### Security
- 機密情報（API トークン・パスワード）は .env に保持する設計だが、`config_setup.py` の出力では「.env を絶対に Git にコミットしないこと」を明記。

### Breaking Changes
- なし（初回リリース）

---

今後のリリースでは、テストカバレッジの追加、external broker の追加実装、銘柄ごとの lot_size 対応、より高度なポジションサイズ最適化や backtest 連携機能などを予定しています。