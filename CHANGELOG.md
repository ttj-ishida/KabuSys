# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※ 本リリースはソースコードから推測して作成した初期リリースノートです。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース。自動売買フレームワーク「KabuSys」の基礎機能を多数追加。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV による paper_trading モード対応（MockBrokerClient を使用、paper_trading.db に記録して本番 DB と完全に分離）。
    - スレッドでエンジンをデーモン実行し、data/stop_requested.flag による外部停止制御を実装。
    - プロセス PID ファイル管理（data/execution.pid）。
    - RiskManager / Reconciler / OrderManager / OrderRepository の組み立てと既定パラメータ（RiskConfig）を導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず監視用（本番）sqlite_path を使用する実装。
    - data/stop_requested.flag による停止検知を実装。

- 設定・環境関連
  - config.py: Settings クラスを導入。.env の自動読み込み（.env、.env.local の順、OS 環境変数保護）を実装。
    - 自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパース強化（export プレフィックス、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
    - 多数の設定プロパティを提供（J-Quants / kabuAPI / LINE / DB パス / PID / kill flag / モニタ閾値 / env/log level 判定など）。
    - PAPER_FILL_MODE の値検証（instant|partial|never|reject）。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（シークレットマスク表示、既存 .env 読み込み、.env 書き込み）。
  - validate_config.py: 起動前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config/*.yaml の存在チェック、live 環境向けガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START など）。--strict オプションで警告も失敗扱いにできる。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db の呼び出し（起動時に監視テーブルが存在することを保証、冪等）。

- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を吸収する実装。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - 権限不足や未対応環境での安全なフォールバックと警告ログ出力。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア順で候補抽出（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存ポジションのセクター別エクスポージャー算出と候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定。
    - 単元株（lot_size）、max_position_pct、max_utilization、stop_loss_pct、risk_pct、cost_buffer を考慮した計算。
    - aggregate cap によるスケーリングと残差処理（lot 単位での再配分アルゴリズム）。

- 研究・ファクター計算
  - research/factor_research.py: DuckDB を用いたファクター計算モジュール（Momentum / Volatility / Liquidity 等）。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: ATR(20)、相対ATR、20日平均売買代金、出来高比率 等の計算（TR の NULL 伝播に注意した実装）。
    - DuckDB SQL を用いることでローカル DB 内で高速に処理。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH を参照（または --db 指定）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し、閾値（稼働率 >=99%, fill >=90%, send >=95%, P95 <=200ms）で PASS/FAIL 判定。
    - P95 計算、日付フィルタ、DB の存在チェック、欠損テーブルに対する安全なハンドリングを実装。

### Changed
- （初期リリースに伴い）アプリケーション構成と設定管理を明確化。
  - .env 自動ロードの優先順位を OS 環境 > .env.local > .env と定義し、OS 環境変数の保護を実装。
  - run_monitoring / run_execution 起動時にプロセス優先度を最初に設定。

### Fixed
- なし（初期リリース）

### Security / Notes
- .env に機密情報（API トークン等）を保存するため、.env を絶対に Git にコミットしない旨が config_setup に記載されています。
- process_priority や CPU affinity の設定は権限により失敗する場合があるため、その場合は警告ログを出して処理を継続します。
- Paper Trading は本番データベースと完全分離されるよう設計されています（paper_sqlite_path）。

### Breaking Changes
- なし（初期リリース）

---

今後の改善候補（ソースからの推測）
- position_sizing の lot_size を銘柄別に指定できるよう拡張。
- apply_sector_cap の価格欠損（price==0）のフォールバック実装（前日終値や取得原価の使用）。
- factor_research の追加ファクター実装・単体テスト整備。
- run_monitoring/run_execution のユニットテストおよびプロセス管理の強化（systemd 等の統合）。

---