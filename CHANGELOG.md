# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

初回リリース。プロジェクトのコア機能と運用用ユーティリティを実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて 0.1.0 として定義。

- 設定管理
  - src/kabusys/config.py
    - .env 自動ロード機能（プロジェクトルート自動検出: .git or pyproject.toml）。
    - .env/.env.local の読み込み順序と保護（OS 環境変数保護）を実装。
    - .env 行パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスで各種環境変数プロパティを提供（JQUANTS, KABU API, DB パス, PID/kill フラグパス, 監視閾値, 環境種別判定等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path の分離などペーパートレード用設定をサポート。
    - settings インスタンスをモジュールレベルでエクスポート。

- 設定支援 / 検証 CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の作成/更新を支援。
    - 入力ガイド、シークレットマスキング、確認・保存機能を実装。
  - src/kabusys/validate_config.py
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV 値、ログレベル、DB パスの親ディレクトリ、config/*.yaml の存在/パースチェック（PyYAML がある場合に実施）、本番環境用ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使用したブローカクライアント切替、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のスレッド実行・停止フラグ監視、PID ファイル・stop flag の取り扱いを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視データは共通 DB に格納）。

- 監視 DB 初期化
  - run 系スクリプトから監視テーブルの初期化呼び出し（init_monitoring_db）を行うことで冪等にテーブルを準備。

- ロギング / プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を実装。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続する耐障害性を備える。
    - 既存ハンドラのクリアや LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）設定ユーティリティを追加（Windows/Linux/macOS 対応、psutil を使用、例外発生時に警告）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（利用不可環境は警告してスキップ）。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア全て 0 の場合は等配分にフォールバックして警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（売却予定銘柄除外、"unknown" セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマッピングし未知レジームは警告して 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に対するスケールダウンロジックを実装。スケールダウン後の端数は lot_size 単位で再配分するアルゴリズムを実装。
    - cost_buffer（手数料・スリッページ見積り）を加味した保守的なコスト見積りをサポート。

- 分析 / ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用の検証レポート生成ツールを追加（DB からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ等を集計）。
    - P95 計算、日付フィルタ (--from/--to)、基準値による PASS/FAIL 判定を実装。PAPER_TRADING_SQLITE_PATH 環境変数や --db オプションで DB 指定可能。

- 研究用モジュール（作業中）
  - src/kabusys/research/factor_research.py
    - ファクター計算基盤を追加（モメンタム、移動平均乖離、ATR、流動性指標等を計画）。DuckDB を用いた prices_daily / raw_financials 参照を前提とした実装方針を明記。モジュールは開発途中。

- パッケージエクスポート
  - src/kabusys/portfolio/__init__.py で主要関数を公開。

### Changed
- 設計上の注意点（ドキュメント化）
  - run_* スクリプトは起動時にプロセス優先度を "high" に設定するように統一。
  - ログは stdout とファイルの両方に出力するが、ログディレクトリ作成に失敗してもプロセスは継続するように変更（運用の頑健性強化）。
  - .env の読み込み順序・上書きポリシーを明確化（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

### Fixed
- レジーム乗数の不明値ハンドリングを明確化
  - calc_regime_multiplier で未知のレジーム値が来た場合に警告を出してフォールバックするように修正（予期しない文字列による例外回避）。

### Security
- .env 取り扱いの注意喚起を config_setup に明記（.env を Git にコミットしない旨のヘッダを追加）。

### Notes / Known issues
- research/factor_research.py は実装途中（ファイル末尾に未完のコードが存在）。今後のリリースで完了予定。
- 一部の I/O 操作（ログディレクトリ作成、psutil による優先度設定 / affinity）は権限不足や非対応環境で失敗する可能性があるが、失敗時は警告出力して処理を継続する堅牢化を行っています。
- PAPER_FILL_MODE 等の環境変数は厳密なバリデーションを行うため、設定ミスは起動時に例外となることがあります。validate_config や config_setup を使って事前確認してください。

---- 

今後の予定:
- factor_research の残実装完了（Momentum 等の計算ロジック）。
- ExecutionEngine / Monitoring の詳細な単体テスト追加。
- Strategy / Execution コンポーネントの公開 API 整備とドキュメント拡充。