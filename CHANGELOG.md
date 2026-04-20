# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
リリース履歴はコードベースの内容から推測して作成しています。

変更の意図や挙動はソースコードの実装に基づいて記載していますが、運用上の細かい仕様（外部 API の挙動や実行環境依存の副作用など）は省略しています。

## [Unreleased]

### Added
- 環境変数での監視ポーリング間隔指定機能を追加
  - 環境変数 `MONITOR_POLL_INTERVAL` により監視ループの sleep 間隔を上書き可能（デフォルト 60 秒）。
- 停止制御（Stop/Kill フラグ）を標準化
  - プロジェクト直下の `data/stop_requested.flag` および `data/kill.flag` を用いた停止制御に対応。
  - 実行用 PID ファイル管理をサポート（`data/execution.pid` 等）。
- 実行・監視プロセス起動スクリプトを追加
  - `run_execution.py`: ExecutionEngine の起動スクリプト。paper_trading 環境では MockBrokerClient を利用し、paper 用の SQLite（`data/paper_trading.db`）に記録することで本番 DB と完全分離。
  - `run_monitoring.py`: SystemMonitor のポーリングループ起動スクリプト。モニタリングでは環境にかかわらず本番用の sqlite_path を利用する旨を明示。
- .env 操作用ユーティリティを追加
  - `config_setup.py`: 対話式ウィザードで `.env` を生成・更新する CLI を追加。選択肢・デフォルト表示・シークレットマスクなどの対話機能を備える。
  - `.env` 自動読み込みの実装を改善: `.env` / `.env.local` の読み込み順、OS 環境変数の保護機能（上書き防止）を実装。
  - `.env` パーサで `export KEY=val`、クォート値、インラインコメント等に対応。
- 設定検証 CLI を追加
  - `validate_config.py`: 必須環境変数、`KABUSYS_ENV`、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば内容検証）などをチェック。`--strict` オプションで警告もエラー扱いにできる。
- ロギング・プロセス優先度ユーティリティを追加
  - `utils/logging_setup.py`: stdout ストリームハンドラ + 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成、環境変数に基づくログレベル・ディレクトリ切替をサポート。
  - `utils/process_priority.py`: Windows / POSIX に跨るプロセス優先度（high/normal/low）設定と CPU affinity 設定ユーティリティを追加。アクセス権限や非対応 OS の場合は安全にフォールバック。
- ポートフォリオ構築関連の純粋関数群を追加
  - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコア 0 の場合は等配分にフォールバック）
  - リスク制御: `apply_sector_cap`（セクター集中制限を適用、unknown セクターは除外しない）、`calc_regime_multiplier`（market レジームに応じた投下資金乗数）
  - 株数決定: `calc_position_sizes`（`risk_based` / `equal` / `score` の配分方式、lot（単元）丸め、aggregate cap によるスケールダウン・再配分ロジック、コストバッファ対応）
- 分析・検証ツールを追加
  - `tools/paper_verification_report.py`: Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して PASS/FAIL レポートを生成する CLI。閾値（稼働率 99%、成立率 90% など）を定義。

### Changed
- DB 周りの扱いを明確化
  - 監視（monitoring）は実行環境に依らず本番用 sqlite_path を使うよう挙動を明示（run_monitoring）。
  - Execution は paper_trading 環境で専用の paper_sqlite_path を使い本番 DB と分離。
- ログ出力の標準化
  - 全起動スクリプトから `setup_logging(app_name=...)` を呼ぶことでログの出力先やレベルを統一。
  - StreamHandler は stdout を使用（cron 等でのリダイレクトを想定）。
- .env 読み込みの安全性向上
  - OS 環境変数を保護する仕組みを導入（`.env.local` の上書きに際しても OS 環境変数は保持）。
- 設定検証ロジックを整理
  - 必須/任意環境変数リスト、config YAML の存在・パースチェック、KABUSYS_ENV=live 時の追加ガード等を実装。

### Fixed
- 例外耐性の向上
  - 監視ループ内での check_once() 呼び出し時の例外をキャッチしてログ出力し、ループを継続するフェイルセーフを追加（run_monitoring）。
  - ロギング設定でログディレクトリ作成失敗時にファイルハンドラ作成をスキップして stdout 出力のみで継続するように修正。

### Documentation
- モジュール・関数に対する docstring を充実化（各 CLI、ユーティリティ、ポートフォリオ関数等）。
- config_setup と validate_config の使い方・例を README 的に同梱（スクリプト冒頭の使用例コメント）。

---

## [0.1.0] - 2026-04-20

初回公開リリース（推定）。上記の主要機能群をまとめて初版として実装。

### Added
- 基本的な自動売買フレームワークの骨格を実装：
  - ExecutionEngine 起動フロー / OrderManager / OrderRepository / Reconciler / RiskManager の組み立て（run_execution にて起動）。
  - SystemMonitor と監視 DB 初期化（init_monitoring_db が存在）。
- 環境設定管理
  - `Settings` クラスによる環境変数ラップ（DB パス、API トークン、KABUSYS_ENV 判定、ログレベル、閾値設定など）。
  - 自動 `.env` ロード（プロジェクトルート検出ロジックを含む）。
- ポートフォリオ構築ロジック（select/weights/position sizing/sector cap/regime multiplier）。
- 分析用 DuckDB の統合（duckdb 接続を受け取る設計）。
- Paper Trading 向け分離設計（MockBrokerClient の利用、専用 SQLite）。
- CLI ツール群
  - `python -m kabusys.config_setup`（.env ウィザード）
  - `python -m kabusys.validate_config`（設定検証）
  - `python -m kabusys.tools.paper_verification_report`（Paper Trading レポート）
  - `run_monitoring.py`, `run_execution.py` の起動スクリプト

### Changed / Fixed
- 初期実装段階での例外・フォールバック処理を追加（ログディレクトリ作成失敗時、プロセス優先度設定失敗時など）。
- `.env` パースの堅牢化（クォート・エスケープ・コメント処理の改善）。

---

（以降のリリースでは、外部ブローカー実装、Strategy モジュール、market data ingestion、より詳細なテストカバレッジ、ドキュメント整備、セキュリティハードニング等が想定されます。）