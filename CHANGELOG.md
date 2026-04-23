# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン 0.1.0 は初回公開リリース想定の内容をコードベースから推測してまとめたものです。

## [0.1.0] - 2026-04-23

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤機能群を追加。
  - パッケージ基本情報
    - src/kabusys/__init__.py にバージョン情報とエクスポート一覧を追加（__version__ = "0.1.0"）。
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory 経由のブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、スレッドベースのセッション実行・停止制御、paper_trading 用 DB 分離（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を実装。
    - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能（デフォルト 60 秒）、監視 DB 初期化、停止フラグ（data/stop_requested.flag）検知でループ終了。
  - 設定管理・検証・ウィザード
    - config.py: 環境変数の読み込み・ラッパー Settings クラスを実装。自動 .env ロード（.env, .env.local）、安全な上書きロジック、必須環境変数取得用ヘルパ、paper_trading 用設定（paper_fill_mode, paper_sqlite_path）等を実装。
    - validate_config.py: 起動前の設定検証コマンドラインツールを追加。.env の必須項目チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、live 環境向けの追加警告などを実装。--strict オプションをサポート。
    - config_setup.py: 対話式 .env 作成ウィザードを追加。デフォルト・選択肢表示、シークレット項目のマスク、既存 .env の読み込み・編集、ファイルへ書き出し機能を提供。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選別 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を提供。
    - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を提供。
    - portfolio/position_sizing.py: ポジションサイズ計算 (calc_position_sizes) を提供。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケールダウン、手数料・スリッページ用 cost_buffer などを実装。
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーの統一設定ユーティリティ（コンソール stdout 出力 + 日次ローテートファイル出力、LOG_DIR / LOG_LEVEL の解決など）を追加。ログディレクトリ作成失敗時はファイル出力をスキップするフォールバック実装。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定・CPU affinity 設定を追加（Windows/Linux/Unix 対応のフォールバック、psutil 利用、権限不足時は警告でスキップ）。
  - 解析・研究
    - research/factor_research.py（途中まで実装）: DuckDB 接続を用いたモメンタム等のファクター計算モジュールの骨子を追加（モジュール設計、定数、calc_momentum の実装開始）。
  - 運用ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し PASS/FAIL 判定を行う。閾値（稼働率 99%、成功率 90% など）を定義。
  - DB 初期化
    - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから呼び出して監視用テーブルの存在を保証（冪等）する仕組みを追加（run_monitoring.py, run_execution.py）。
  - その他
    - tools と portfolio 等の各モジュールに対する README 相当の docstring を充実させ、設計・使い方・注意点を明記。

### Changed
- 環境変数ロード挙動（config.py）
  - 自動 .env 読み込みの優先度を明確化: OS 環境変数 > .env.local > .env。テスト向けに KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
  - .env パーサは export KEY=val, シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱い等をサポートするよう強化。
- run_execution/run_monitoring の DB 接続ポリシー
  - run_execution は paper_trading モード時に専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番データと完全に分離するように明示。
  - run_monitoring は環境に関わらず本番 sqlite_path を使用して監視データを保存する仕様を明記（監視は実運用 DB を見るため）。
- ログ設定: setup_logging の挙動
  - 既存ハンドラがある場合は一旦 flush/close してから削除し、重複ハンドラ設定を防止。
  - stdout をストリーム出力に使う（stderr ではなく stdout）。ファイルハンドラ作成失敗時はコンソール出力のみで継続。

### Fixed / Robustness
- process_priority の例外取り扱いを追加
  - psutil の権限不足やプラットフォーム差分による例外を警告ログでハンドリングし、起動失敗に繋がらないようにした。
- .env 読み込み時のファイル読み取り障害を警告で処理（warnings.warn）し、プロセスを継続可能にした。
- run_monitoring の MONITOR_POLL_INTERVAL パースを堅牢化
  - 0 または負数、非整数が指定された場合に警告出力してデフォルト（60秒）にフォールバックする処理を追加。
- paper_verification_report.py
  - DB にテーブルが無い等の sqlite3.OperationalError 発生時に各集計を N/A 相当で安全に扱うフォールバック処理を追加。
  - P95 計算の防御的実装（空リストで None を返す）。

### Documentation / UX
- config_setup.py: 対話ウィザードの UX 向上
  - シークレット値は表示時にマスク、既存 .env の読み込み・Enter で既存値継承、選択肢チェック等を実装。
  - 保存確認プロンプトを追加。
- validate_config.py: 検証結果の INFO/WARNING/ERROR をわかりやすく出力し、--strict で警告を FAIL 扱いにできるようにした。
- 各モジュールに docstring と使用例・設計注記を追加し、保守性を向上。

### Breaking Changes
- なし（初回リリース想定）。既知の挙動・環境変数名は .env.example を参照する想定。

### Notes / Migration
- 環境変数に依存する設定が多く存在するため、初回起動前に config_setup.py で .env を作成し、python -m kabusys.validate_config で検証することを推奨します。
- paper_trading を利用する場合は KABUSYS_ENV=paper_trading を設定すると専用の paper_trading DB に記録され、本番 DB と分離されます。
- 監視ループのポーリング間隔変更は MONITOR_POLL_INTERVAL 環境変数で可能（正の整数を指定してください）。無効値は 60 秒にフォールバックします。
- ログ出力先は環境変数 LOG_DIR で変更可能。ディレクトリ作成に失敗するとファイル出力は無効化され、コンソールのみでロギングが行われます。

---

今後のリリースでは、factor_research モジュールの完成、ExecutionEngine や RiskManager の詳細実装・テスト、Broker クライアントの実装（およびモックの拡充）、および各種ユニットテスト・CI 設定の追加が期待されます。