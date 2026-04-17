# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に従い、セマンティックバージョニングを採用しています。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys パッケージの基本機能を実装。
- 設定管理
  - Settings クラスを実装して環境変数経由で設定を取得する機能を提供（src/kabusys/config.py）。
  - .env 自動読み込み機構を追加（プロジェクトルートに基づく自動検出）。読み込み順序: OS 環境変数 > .env.local > .env。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用可能。
  - .env パーサーの強化: export プレフィックス、引用符付き値（バックスラッシュエスケープ対応）、およびインラインコメント処理に対応。
  - Settings が提供する主な設定:
    - J-Quants / kabuステーション / LINE API 関連（必須/任意の環境変数）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - 監視・PID/kill フラグ関連パスとしきい値（CPU/MEM/DISK）
    - 環境（KABUSYS_ENV）、ログレベル、paper trading の振る舞い（PAPER_FILL_MODE）
- 環境設定ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式に .env を作成・更新するウィザードを追加。
  - `python -m kabusys.config_setup` で起動。出力ファイルはデフォルトでプロジェクトルートの .env。
- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml の存在・妥当性を検証するコマンド。
  - `python -m kabusys.validate_config`、`--strict` オプションで警告をエラー扱いにできる。
  - PyYAML の有無に応じた YAML 検証の有効化/無効化、KABUSYS_ENV=live 時の追加ガードチェックを実装。
- 実行系 / 監視の起動スクリプト
  - ExecutionEngine 起動ラッパー（src/kabusys/run_execution.py）
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）および MockBrokerClient を利用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知時にエンジンに stop を投げる仕組みを実装。PID ファイル出力サポートあり。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視 DB 初期化処理を実行し、停止フラグでループを終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level: "high" | "normal" | "low") を実装。Windows / POSIX の差を吸収して設定を試みる（失敗時は警告でスキップ）。
  - set_cpu_affinity(cpu_count: int | None) を実装。指定が None の場合は設定しない。
- ポートフォリオ構築関連（src/kabusys/portfolio/*）
  - portfolio_builder: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear）
  - position_sizing: 株数計算、リスクベース/等配分/スコア配分の実装（calc_position_sizes）。単元株丸め、aggregate cap スケーリング、cost_buffer による保守的見積りをサポート。
  - これらは純粋関数（メモリ内計算）として設計され、DB 未参照。
- 研究/ファクター計算（src/kabusys/research/factor_research.py）
  - モメンタム・ボラティリティ等のファクター計算関数（calc_momentum, calc_volatility）を実装。DuckDB 接続と prices_daily テーブルを前提に計算。
  - ATR、移動平均乖離、出来高・売買代金関連指標等を提供。
- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95）等を算出してレポートを出力。
  - CLI: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db PATH`
  - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）。
- パッケージ情報
  - __version__ = "0.1.0" をパッケージルートに設定。

### Changed
- .env 読み込みポリシーを明確化: OS 環境変数を保護しつつ .env.local で上書き可能に。_load_env_file に protected 引数を導入して OS 環境変数の上書きを防止。
- run_* スクリプトで起動直後にプロセス優先度を High に設定するように変更（set_process_priority("high") を呼び出し）。

### Fixed / Robustness
- MONITOR_POLL_INTERVAL の不正値（非整数や 0 以下）に対して警告を出し、デフォルト値にフォールバックしてループ継続するように改善（run_monitoring）。
- process_priority の実行環境依存エラー（AccessDenied / NotImplemented / AttributeError）を捕捉し、警告を出して処理をスキップするようにして起動の頑強性を向上。
- validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告する挙動を実装（対話的に判別）。
- paper_verification_report における各種集計でテーブルが存在しない場合でも例外で終了しないように sqlite3.OperationalError を捕捉して N/A 相当を返すようにした。

### Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が 0.0 の場合にエクスポージャーが過少評価される可能性がある旨をコメントで記載。前日終値や取得原価でのフォールバック対応は将来的な改善案として残している。
- risk_adjustment.calc_regime_multiplier:
  - 未知のレジームに対しては 1.0（Bull 相当）でフォールバックし警告を出す設計。
- 一部の実行コンポーネント（ExecutionEngine, BrokerClientFactory, OrderManager 等）は起動スクリプトで組み立てているが、外部ブローカー実装や具体的なデータ構造に依存するため、運用環境での接続情報（.env）を正しく整備する必要がある。
- デフォルトのファイルパス:
  - DuckDB: data/kabusys.duckdb
  - SQLite（監視）: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  これらの親ディレクトリが存在しない場合は起動時に自動作成される場合があるが、validate_config では存在確認と警告を行う。

### CLI / 実行例
- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

将来的にリリースノートを更新するときは、追加・変更・修正・破壊的変更等を上記フォーマットに従って追記してください。