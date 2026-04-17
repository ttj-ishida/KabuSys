# CHANGELOG

すべての重要な変更点を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存挙動の変更 / 設計上の決定
- Fixed: バグ修正・堅牢化
- Removed / Security 等は必要時に追加

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。
  - パッケージ情報
    - バージョン定義: kabusys.__version__ = "0.1.0"
  - 設定管理
    - .env 自動ロード機能（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数を保護して優先度を扱う）を追加（src/kabusys/config.py）。
    - Settings クラスを追加し、環境変数から型付き設定を取得する API を提供（データベースパス、API トークン、監視閾値等）。
    - .env パーサは export 文、クォート文字列、インラインコメント等に対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - 設定ユーティリティ / CLI
    - 対話式ウィザードで .env を作成/更新する config_setup（python -m kabusys.config_setup）を追加。シークレットのマスク表示、デフォルト値や選択肢の提示をサポート（src/kabusys/config_setup.py）。
    - 起動前に環境・設定ファイルを検証する validate_config CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 等の検証、config/*.yaml の存在とパース検証（PyYAML あれば実施）を行う（src/kabusys/validate_config.py）。
  - 実行 / 監視プロセス起動スクリプト
    - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
      - 停止フラグ（data/stop_requested.flag）や pid ファイル（data/execution.pid）の扱いを実装。
      - デフォルトでプロセス優先度を "high" に設定。
    - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログを出してデフォルトにフォールバック。
      - Monitoring は環境にかかわらず（paper/live ともに）本番 sqlite_path を使用する設計上の決定。
      - stop フラグの監視、例外発生時のログ出力と継続動作を実装。
  - 監視 DB 初期化ユーティリティ（init_monitoring_db を呼び出す箇所を run スクリプト内で保証）。
  - Paper Trading / 検証ツール
    - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
      - SQLite の paper_trading DB から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL 判定を出力（しきい値はソース内で定義）。
      - --from / --to / --db オプションをサポート（src/kabusys/tools/paper_verification_report.py）。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
    - ポジションサイズ計算: calc_position_sizes（等分・スコア・リスクベースの配分、lot_size・集計キャップ処理、スケーリングロジックを含む）（src/kabusys/portfolio/position_sizing.py）。
    - これらをトップレベルにエクスポート（src/kabusys/portfolio/__init__.py）。
  - リサーチ（ファクター計算）
    - DuckDB を用いたファクター計算モジュールを追加（momentum / volatility 等）。prices_daily / raw_financials テーブルを参照し、各種指標（mom_1m/3m/6m, ma200_dev, atr_20, avg_turnover 等）を計算（src/kabusys/research/factor_research.py）。
  - ユーティリティ
    - プロセス優先度・CPU affinity 設定ユーティリティを追加（set_process_priority, set_cpu_affinity）。Windows / POSIX の差分を吸収し、アクセス拒否等の例外はログで無視（src/kabusys/utils/process_priority.py）。

### Changed
- 設計上の決定（初期実装として明示）
  - 監視プロセスは環境変数に関わらず「本番 sqlite_path」を参照する（run_monitoring）。
  - .env 自動ロードの優先順位: OS 環境 > .env.local > .env（既存 OS 環境変数は保護され上書きされない）。
  - config_setup が生成する .env テンプレートに注意書き（.env を絶対に Git にコミットしない旨）を追加。
  - ExecutionEngine の paper_trading モードは DB を完全に分離（PAPER_TRADING_SQLITE_PATH）して検証ができるようにした。

### Fixed / Hardened
- 設定パーサの堅牢化
  - .env 行パースで export プレフィックス、シングル/ダブルクォートのエスケープ、インラインコメント処理を正しく扱うよう改善（src/kabusys/config.py）。
- 環境変数値のバリデーション強化
  - MONITOR_POLL_INTERVAL が 0 または負数・非整数のときにデフォルトにフォールバックし、警告ログを出力するようにした（run_monitoring）。
  - PAPER_FILL_MODE に対する有効値チェックを追加（instant / partial / never / reject）。無効値は ValueError を送出（Settings.paper_fill_mode）。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックにより早期検出（Settings と validate_config）。
- 実行時の例外耐性
  - 監視ループ内で monitor.check_once() が例外を投げてもループを継続し、スタックトレースをログに残すようにした（run_monitoring）。
  - process priority / cpu affinity 設定でアクセス権限不足や未実装のプラットフォームの場合は警告ログを出し動作継続するようにした（utils/process_priority.py）。
- Paper Verification レポートの堅牢化
  - DB テーブルが存在しない・クエリが失敗した場合に個別にフォールバックしてレポートを生成するようにした（src/kabusys/tools/paper_verification_report.py）。
  - P95 計算ユーティリティを追加し、タイムレンジフィルタで UTC ISO8601 形式（開始日の 00:00:00 / 終了日の 23:59:59.999999）を用いるようにした。

### Documentation / CLI hints
- 各 CLI スクリプトの使い方・例をモジュールドキュメントに記載（config_setup, validate_config, paper_verification_report 等）。
- config_setup は最後に設定内容を表示して確認を求め、保存する仕組みを採用。

### Notes / Known limitations
- 一部の関数はデータ不足時に None を返す（ファクター計算の移動平均や ATR など）。呼び出し元は None を扱う必要あり。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別拡張を想定）。
- apply_sector_cap の exposure 計算は price が欠損（0.0）の場合に過少見積もりとなる可能性がある旨を TODO コメントで残している。
- monitor / execution の PID・フラグファイルのパスはデフォルトで data/ 以下。プロダクション運用時は適切な配置と権限管理が必要。

---

上記は現行ソースコードの実装内容・設計意図から推測してまとめた CHANGELOG です。必要であれば、各ファイルごとのより詳細な変更点（関数レベルの説明や使用例）を追記します。