CHANGELOG
=========

このファイルは Keep a Changelog の様式に準拠して記述されています。
https://keepachangelog.com/ja/1.0.0/

すべての重要な変更はここに記録してください。  
日付は本リポジトリの現時点 (2026-04-21) を用いて記載しています。

Unreleased
----------

- （現在のブランチに未リリースの変更はありません）

0.1.0 - 2026-04-21
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアユーティリティ群を追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - KABUSYS_ENV による paper_trading モード切り替えをサポートし、ペーパートレード時は専用 SQLite (data/paper_trading.db) を使用する。
    - エンジンの実行をバックグラウンドスレッドで行い、data/stop_requested.flag による外部停止フラグをサポート。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) による終了、KeyboardInterrupt の優雅な終了処理を実装。
    - 監視は環境に依らず本番用の sqlite_path を使用する仕様。

- 設定管理
  - config.py: 環境変数 / .env 自動ロード機能、Settings クラスを追加。
    - プロジェクトルート検出 (.git / pyproject.toml) を基に .env / .env.local を自動的に読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパース機能はシングル/ダブルクォート、エスケープ、export プレフィックス、コメント処理に対応。
    - 各種設定プロパティ（DBパス、LINE トークン、Paper Trading など）とバリデーションを提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）など Paper Trading 固有の設定を取り扱う。

- 設定補助 CLI
  - config_setup.py: .env の対話式ウィザードを追加。既存値の読み込み、シークレットマスキング、保存機能を提供。
  - validate_config.py: .env と config/*.yaml の起動前検証ツールを追加。必須環境変数チェック、パス存在チェック、YAML パース（PyYAML が無い場合はスキップ）や本番時のガード（LINE 通知の有無、KILL_FLAG_CLEAR_ON_START の危険設定等）を実施。--strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコア全ゼロ時は等配分にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。unknown セクターは上限適用の対象外。未知レジームはフォールバックで multiplier=1.0 として警告を出す。
  - portfolio.position_sizing: 株数計算 (calc_position_sizes) を実装。risk_based / equal / score の各方式に対応し、単元株（lot_size）丸め、最大ポジション比率、利用可能資金に基づくスケールダウン、cost_buffer による保守的見積りなどを考慮する。aggregate cap 超過時のスケーリングと残差処理を実装。

- 実行系ユーティリティ
  - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: Windows / POSIX の差分を吸収したプロセス優先度設定と CPU affinity 設定を追加。アクセス権限不足などは警告でスキップ。
  - utils パッケージを整理。

- モニタリング / 実行補助
  - monitoring.monitoring_db.init_monitoring_db や SystemMonitor、execution 側の OrderManager / RiskManager / ExecutionEngine 等の呼び出しを起動スクリプト側で統合（実装ファイルは別途存在）。DuckDB と SQLite の両方を使用する設計を導入。

- 分析ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを生成するツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、PASS/FAIL 判定を行う。--from/--to/--db オプションをサポート。

- 研究用モジュール（未完/部分実装）
  - research.factor_research.py: Momentum / Value / Volatility / Liquidity 指標を算出する方針でモジュールを追加（DuckDB 接続前提、prices_daily/raw_financials を参照）。部分的に実装されているが、一部未完（ソース末尾で切れている）。

Changed
- なし（初回リリースのため、既存機能からの変更はありません）。

Fixed
- 多数の堅牢化:
  - MONITOR_POLL_INTERVAL の不正な値に対してデフォルトへフォールバックするロジックを追加（run_monitoring）。
  - .env 読み込み処理でファイル読み込み失敗時に警告を出すようにして自動ロード処理の安全性を向上（config._load_env_file）。
  - ログ設定で既存ハンドラの二重登録を防ぐため、ハンドラの flush/close とクリアを行うようにした（logging_setup）。
  - process_priority や set_cpu_affinity は権限不足や未対応 OS を警告でスキップする堅牢化を実施。

Security
- シークレット値 (.env のトークン/パスワード) を対話ウィザードでマスク表示する扱いにした（config_setup）。
- .env は Git に絶対にコミットしない旨の注意書きを出力するテンプレートを実装（config_setup._write_env）。

Known issues / Notes
- research.factor_research.py はファイル末尾が途切れており、完全実装ではありません。実運用前に実装完了・ユニットテストの追加が必要です。
- position_sizing.calc_position_sizes:
  - price_map / open_prices に 0.0 や欠損がある場合、現在は該当銘柄をスキップする（TODO: 前日終値や取得原価でのフォールバックを検討）。
- apply_sector_cap:
  - "unknown" セクターは上限適用の対象外としているため、マスタの欠損があると期待どおりに制限されない場合がある。銘柄マスタの整備を推奨。
- start/stop フラグ制御はファイルベースで実装しているため、運用環境では適切な監視・権限設定を行ってください。
- 実際のブローカークライアントや ExecutionEngine 等の振る舞い（注文送出・リコンシリエーション・リスク管理）は別モジュールに依存しており、本ログではそれらの実装詳細は含みません。

Contributing
- バグ報告や改善提案は Pull Request / Issue を通じて受け付けます。機能追加の際は CHANGELOG.md を更新してください。

License
- リポジトリ内のライセンスファイルを参照してください。