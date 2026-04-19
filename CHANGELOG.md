# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  
バージョン番号は package の __version__（src/kabusys/__init__.py）を参照しています。

---

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース — コア機能一式を実装しました。

### Added
- 基本パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 設定管理
  - 環境変数・.env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に自動検出して `.env` / `.env.local` を読み込む。
    - OS 環境変数を保護する仕組み、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
    - 各種環境設定を `Settings` クラスのプロパティとして提供（J-Quants、kabu API、DB パス、Paper Trading 設定、閾値など）。
    - `PAPER_FILL_MODE` や `KABUSYS_ENV`, `LOG_LEVEL` の値検証を実施。

- 環境設定支援 CLI
  - 対話式ウィザードで `.env` を生成/更新する `config_setup` CLI を実装（src/kabusys/config_setup.py）。
    - 質問・選択肢ベースでの入力、既存 `.env` の読み込み、シークレットマスク表示、保存確認をサポート。

- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml の妥当性を検証する `validate_config` CLI を実装（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスや config ファイル存在チェック、`--strict` モードをサポート。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。

- ロギングユーティリティ
  - 統一的に使用できる `setup_logging` を実装（src/kabusys/utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテート（30日保持）を行う TimedRotatingFileHandler をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして継続。

- プロセス優先度・CPU 固定ユーティリティ
  - `set_process_priority` / `set_cpu_affinity` を実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップするフェールセーフを実装（psutil に依存）。

- 実行系ランチャー
  - ExecutionEngine を起動するスクリプトを実装（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を「high」に設定。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 DB（`data/paper_trading.db` をデフォルト）を使用し、ブローカーは Mock を利用する（BrokerClientFactory 経由）。
    - 依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立ててバックグラウンドスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル機構をサポート。

- 監視系ランチャー
  - SystemMonitor のポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - デフォルトポーリング間隔 60 秒、環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（監視データを本番 DB に集約する想定）。
    - DB 初期化（init_monitoring_db）と DuckDB 接続の確立、停止フラグ検出および例外ハンドリングを備える。

- 監視 DB 初期化（モジュール化）
  - 監視用 DB の初期化処理を提供（参照: monitoring.monitoring_db の利用箇所）。

- ポートフォリオ構築モジュール
  - 銘柄選定・重み計算機能を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - 候補選択（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を提供。
  - セクター集中制限・レジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター別エクスポージャー計算により候補フィルタリングを行う apply_sector_cap。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - ポジションサイズ計算を実装（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当ロジック、単元株切り捨て、ポートフォリオ合計でのスケーリング（aggregate cap）、コストバッファの考慮、lot_size 単位での再配分ロジックを実装。
  - 上記を統合するパッケージエクスポートを提供（src/kabusys/portfolio/__init__.py）。

- 研究（リサーチ）モジュール
  - ファクター計算基盤を実装開始（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 指標の計算方針、DuckDB 接続を利用した prices_daily/raw_financials 参照設計。
    - モメンタム計算（calc_momentum）などの関数骨子と定数を定義（計算実装はモジュール内で進行中）。

- ペーパートレード検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数等を SQLite のテーブル（system_status, trade_logs, risk_logs 等）から集計。
    - デフォルト判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - 日付フィルタ、DB パス指定オプション、欠損テーブルへの耐性を備える。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- ファイル入出力や OS 権限に依存する処理（ログディレクトリ作成、プロセス優先度設定、PID/stop フラグ検出）は失敗時に安全にフォールバックするよう設計されています。
- Paper Trading と本番 DB は意図的に分離されるよう設定可能（Settings の paper_sqlite_path、run_execution の sqlite_path 分岐）。
- 環境変数や設定ファイルの不整合を事前に検出するための CLI（validate_config）を備え、運用ミスを軽減します。

---

（以降のリリースでは Added / Changed / Fixed セクションに差分を追記してください。）