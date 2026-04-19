# Changelog

すべての重要な変更点をこのファイルに記録します。形式は「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。

### Added
- 基本パッケージ構成を追加
  - モジュール群: execution, monitoring, portfolio, research, utils, tools, config 等を実装。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。プロセス優先度を設定し、スレッドでエンジンを実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による制御。
    - 環境変数 KABUSYS_ENV に応じて paper_trading モードをサポートし、paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず設定された本番 sqlite_path を使用して監視テーブルを初期化。

- 設定・環境管理
  - config.py
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml ベース）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - 高度な .env パーサを実装（export 対応、クォートとエスケープ、インラインコメント処理）。
    - Settings クラスで各種環境変数をラップ（J-Quants, kabuAPI, DB パス, モード判定, しきい値等）。
    - Paper Trading / 本番 / 開発モードの判定プロパティ（is_paper / is_live / is_dev）。
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, KILL_FLAG_CLEAR_ON_START などの環境変数サポート。

  - config_setup.py
    - 対話式 .env 作成ウィザードを実装（項目定義と .env 書き込み機能）。
    - Secret 項目のマスク表示、既存 .env の読み込みと編集をサポート。

  - validate_config.py
    - 起動前設定検証 CLI を提供。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML があれば詳細検証）。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング / プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーを統一設定する setup_logging を実装。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/）をセットアップ。
    - LOG_DIR / LOG_LEVEL に基づく解決ロジック、既存ハンドラのクリア等を実装。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（set_process_priority）と CPU affinity（set_cpu_affinity）を実装。Windows / POSIX を考慮し、例外時は警告でスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap と市場レジームに応じた calc_regime_multiplier を実装。
    - 未知レジーム・セクターに対するフォールバック挙動を定義。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装。allocation_method として "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）単位で丸め、Per-stock 上限・aggregate cap（利用可能現金に基づくスケーリング）を実装。
    - cost_buffer による手数料/スリッページ考慮と残余キャッシュを用いた再配分ロジックを実装。
    - 内部で max_position_pct / max_utilization 等のリスク制限パラメータを扱う。

- モニタリング / 監査 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。

- 実行・発注関連（骨組み）
  - execution パッケージ内に BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の呼び出し用インターフェースを使用する起動フローを実装（実動ロジックは各モジュールに依存）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用の SQLite（デフォルト data/paper_trading.db）からレポートを生成する CLI を実装。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg / max / P95）などを計算し、しきい値（稼働率 99% 等）で PASS/FAIL 判定する。
    - P95 計算、日付フィルタ、ファイル存在チェックをサポート。

- 研究用ファクタ計算（スケルトン）
  - research/factor_research.py
    - DuckDB 接続を受けてモメンタムや ATR、流動性等のファクターを計算する設計を追加（関数 calc_momentum 等の骨組みを実装）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし

### Known issues / Notes / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる注記があり、将来的に前日終値や取得原価でのフォールバック実装が必要。
- research/factor_research.py は実装途中の箇所がある（ファクター計算の完成が今後の作業）。
- ログディレクトリ作成やプロセス優先度設定は権限や環境に依存するため、失敗時は警告出力してフォールバックする設計。
- .env 自動読み込みはプロジェクトルートが検出できない場合スキップされる（CI / 配布環境では明示的な設定が必要）。

---

参照:
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定関連: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ポートフォリオ: src/kabusys/portfolio/*
- ユーティリティ: src/kabusys/utils/*
- ツール: src/kabusys/tools/paper_verification_report.py
- 研究: src/kabusys/research/factor_research.py

（必要であれば個別モジュールの変更履歴を詳細に分割して追記します。）