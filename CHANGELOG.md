# Changelog

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

## [Unreleased]

(none)

## [0.1.0] - 2026-04-18

初回リリース。主要な機能追加・ユーティリティや CLI を含むリリースです。

### Added
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。
- 環境設定管理
  - `kabusys.config`:
    - .env 自動読み込み機能（プロジェクトルートの検出：.git または pyproject.toml を基準）。
    - 複雑な .env パースロジックを実装（export プレフィックス対応、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）。
    - 自動読み込みの無効化用フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
    - 各種設定プロパティ（DBパス、API トークン、監視しきい値、環境判定など）を提供する `Settings` クラスを追加。
- 環境設定ウィザード CLI
  - `kabusys.config_setup`:
    - `.env` の対話式ウィザード（初期作成・更新）を実装。
    - 保存／確認フロー、シークレット値のマスク表示、デフォルト値・選択肢サポート。
    - `.env` の読み書きユーティリティ（既存読み込み・テンプレート生成）。
- 設定検証ツール
  - `kabusys.validate_config`:
    - .env と config/*.yaml の設定状態を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリチェック、YAML パース（PyYAML が無ければスキップ）等を実行。
    - `--strict` オプションで警告を FAIL 扱いにする機能を追加。
- 起動スクリプト
  - `kabusys.run_execution`:
    - ExecutionEngine を起動するエントリポイント。
    - `KABUSYS_ENV=paper_trading` の場合は paper 用 SQLite（`data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由のブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立てと実行スレッド管理、停止フラグ（data/stop_requested.flag）に応答するロジックを実装。
    - 起動時にプロセス優先度を "high" に変更する処理を呼び出す。
  - `kabusys.run_monitoring`:
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - 環境にかかわらず監視用には本番 sqlite_path を使用する設計（監視は本番 DB を参照）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 停止フラグファイルによる優雅な終了処理と例外ハンドリングを実装。
- ログユーティリティ
  - `kabusys.utils.logging_setup`:
    - 共通ログ設定関数 `setup_logging(app_name, log_dir, level)` を追加。
    - stdout への StreamHandler（stderr ではなく stdout を使用）と、日次ローテーションの TimedRotatingFileHandler（30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続するフォールバックを実装。
- プロセス優先度 / CPU affinity
  - `kabusys.utils.process_priority`:
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定する `set_process_priority` を実装。
    - 指定コア数で CPU affinity を設定する `set_cpu_affinity` を実装。
    - 権限不足や未対応環境では警告を出して安全にスキップする設計。
- Portfolio 構築ライブラリ
  - `kabusys.portfolio` 以下:
    - `portfolio_builder`:
      - 候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコアが全て 0 の場合は等金額にフォールバックし Warning を出力。
    - `risk_adjustment`:
      - セクター集中制限を行う `apply_sector_cap`、市場レジームに応じた投下資金乗数を返す `calc_regime_multiplier` を実装（既知レジーム: bull/neutral/bear、未知は 1.0 にフォールバック）。
    - `position_sizing`:
      - 発注株数計算 `calc_position_sizes` を実装。risk_based / equal / score の割当方式に対応し、lot_size（単元株）丸め、各種上限（per-stock, aggregate）、コストバッファ考慮、スケーリングと残余配分ロジックを備える。
- Paper Trading 検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）からデータを集計して検証レポートを出力するスクリプトを追加。
    - 指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）など。
    - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定め、PASS/FAIL を判定。
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db / 環境変数）に対応。
- Research（着手）
  - `kabusys.research.factor_research`:
    - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム／MA200/ATR 等の計算ロジックの方針・定数群を含む）。実装は継続中（ファイル末尾で処理が途切れているため追加実装の余地あり）。

### Changed
- ログの標準出力を stdout に統一（cron/task scheduler 環境でのリダイレクトを考慮）。
- run_monitoring / run_execution の起動フローを統一的にプロセス優先度を最初に設定するように変更。

### Fixed
- .env パーサーの堅牢化:
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどへ対応し不正なパースを低減。
- DB 初期化呼び出し:
  - `init_monitoring_db` を起動時に呼び出し、監視用テーブルが存在することを冪等的に保証。

### Internal
- コード構成の整理:
  - 各機能（設定、実行エンジン、監視、ポートフォリオ構築、ユーティリティ、検証ツール）をモジュールごとに分離。
  - パブリック API をパッケージレベルの __init__ でエクスポート（portfolio モジュールなど）。
- ドキュメント的な docstring を多用し、各関数・クラスの設計意図と制約を明記。

### Known issues / TODO
- research/factor_research の実装が途中で終わっているため、ファクター計算の完全な実装が必要。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価の利用）は TODO として残されている。
- セクター不明 ("unknown") の扱いは現状で上限適用対象外だが、将来的な方針の明確化が必要。
- 一部のシステムは外部依存（psutil, duckdb, PyYAML）に依存するため、ドキュメントに明示したり要件ファイルで管理することが推奨。

---

最終更新: 2026-04-18 (初版)