CHANGELOG.md
=============

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows semantic versioning.

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装しました。
主要な追加点・設計のポイントを以下にまとめます。

### Added
- 基本パッケージ初期実装
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 起動用スクリプト
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト直下の data/stop_requested.flag により行う。（src/kabusys/run_monitoring.py）
  - run_execution: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db）と Mock ブローカを使用して本番 DB と分離。PID ファイル管理および停止フラグ検知を実装。（src/kabusys/run_execution.py）
- 設定管理・自動ロード
  - Settings クラスを実装し、環境変数取得を集中管理。各種プロパティ（J-Quants トークン、kabu API、DB パス、監視閾値、実行環境判定など）を提供。（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml から探索し、.env / .env.local を自動ロード（既存 OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。（src/kabusys/config.py）
  - .env ファイルのパースでクォート・エスケープや inline コメントに対応する堅牢な実装を追加。（src/kabusys/config.py）
- 設定ウィザード CLI
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE トークン等）を扱う。（src/kabusys/config_setup.py）
- 設定検証 CLI
  - validate_config: .env と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、YAML のパースチェック、live 環境向けガード（LINE 設定や kill flag の自動クリア設定）を実装。--strict オプションで警告も失敗扱いにできる。（src/kabusys/validate_config.py）
- 監視関連
  - 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db）を起動スクリプトで保証。monitoring 用のテーブルが存在することを冪等的に確保。（run_monitoring / run_execution）
  - duckdb を分析用 DB として利用（Settings.duckdb_path）。起動スクリプトで接続を確立。（run_monitoring / run_execution）
- Execution コンポーネント骨格
  - ExecutionEngine の起動フロー（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立て）を run_execution に実装。RiskManager のデフォルト設定例を記述し、初期現金取得に broker.get_available_cash() を参照。（src/kabusys/run_execution.py）
- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading 用 SQLite DB からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計して PASS/FAIL 判定するレポート生成 CLI を追加。期間指定 (--from/--to) と DB パス指定 (--db) に対応。デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）。（src/kabusys/tools/paper_verification_report.py）
- ポートフォリオ構築ライブラリ
  - portfolio モジュールを追加（純粋関数群）
    - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。（src/kabusys/portfolio/portfolio_builder.py）
    - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier)。（src/kabusys/portfolio/risk_adjustment.py）
    - position_sizing: 発注株数計算 (calc_position_sizes)。allocation_method により risk_based / equal / score をサポートし、単元株（lot_size）、max_position_pct、max_utilization、cost_buffer に基づくスケーリングを実装。合計資金が available_cash を超過した場合のスケールダウンと端数処理（lot 単位での再配分）を実装。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージの __all__ を整備。（src/kabusys/portfolio/__init__.py）
- リサーチ（ファクター計算）
  - research/factor_research: DuckDB の prices_daily 等を参照してモメンタム・ボラティリティ・流動性等のファクター計算関数を実装開始。モメンタム（1M/3M/6M、MA200乖離）、ATR、20日平均売買代金等を SQL + Python で計算する設計。（src/kabusys/research/factor_research.py）
- ユーティリティ
  - utils/process_priority: クロスプラットフォームでプロセス優先度設定（Windows の priority class、POSIX の nice）および CPU affinity 固定のユーティリティを実装。アクセス権限・未対応 OS の場合は警告してスキップする設計。（src/kabusys/utils/process_priority.py）
  - 起動スクリプトで起動直後に set_process_priority("high") を呼ぶことで優先度を上げる処理を導入。（run_monitoring/run_execution）

### Changed
- 初期設計方針の明記
  - research と portfolio の関数群は「DB 参照なし / メモリ内計算のみ」「純粋関数」であることを明示。（portfolio/*、research/*）
- 設定読み込みの優先順位
  - OS 環境変数 > .env.local > .env の順で読み込む仕様に統一し、既存 OS 環境変数は保護（上書き不可）する動作を採用。（src/kabusys/config.py）
- Paper Trading の DB 分離
  - 実行時に settings.is_paper を判定し、paper_trading 用の SQLite DB を使用するように変更（settings.paper_sqlite_path）。これにより paper_trading と本番 DB の完全分離を実現。（src/kabusys/run_execution.py）

### Fixed
- .env パースの堅牢化
  - クォーテーション内のバックスラッシュエスケープや inline コメントの扱いを改善し、意図しない切断やコメント解析の誤りを防止。（src/kabusys/config.py）
- ポーリング間隔の不正入力処理
  - MONITOR_POLL_INTERVAL が 0 以下や非整数の場合にデフォルト（60 秒）にフォールバックし、警告ログを出すようにした（time.sleep に渡す不正値による例外回避）。（src/kabusys/run_monitoring.py）
- 起動時の監視 DB 初期化の冪等化
  - init_monitoring_db を起動スクリプトで呼び、テーブルがない場合の初期化を保証することで起動失敗を防止。（run_execution/run_monitoring）

### Notes / Implementation details
- 多くの機能は「設定ファイル（.env や config/*.yaml）と環境変数」に依存するため、本番稼働前に validate_config による事前チェックを推奨します。
- process_priority や CPU affinity の設定は権限不足や未対応 OS の場合に安全にスキップされます（警告ログ出力）。
- Paper Trading レポートはデータが不足（該当テーブルがない、Created イベントがない等）の場合に N/A を表示し、判定基準に従って FAIL 理由を列挙します。
- レジーム乗数やリスク設定などのデフォルト値はコード内に明記してありますが、運用環境に合わせて .env / 設定ファイルでチューニングしてください。

### Deprecated
- なし

### Removed
- なし

### Security
- 設定ファイル (.env) は生成時に「絶対に Git にコミットしないこと」を README／出力メッセージで明示しています。シークレット系の項目はウィザードでマスク表示します（表示は ****）。

---

今後の予定（例）
- ExecutionEngine・OrderManager 等の実装詳細・テスト充実
- portfolio の単元株サイズ差異対応（銘柄別 lot_size）
- factor_research の追加ファクター実装、DuckDB ベースのバッチ処理改善
- ドキュメント（README、運用手順、デプロイ手順）の整備

（以上）