CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
ルール: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（現在なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アーキテクチャと CLI を実装（初期リリース）。
  - パッケージメタ情報: kabusys/__init__.py にバージョン 0.1.0 を設定。
- 環境設定周り
  - 自動 .env ロード機能を実装（プロジェクトルートに基づき .env と .env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。 (src/kabusys/config.py)
  - .env ファイルパーサを実装。export プレフィックス、クォート文字列、インラインコメント等に対応。無効行の無視や読み込み時の上書き制御をサポート。 (src/kabusys/config.py)
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に（J-Quants / kabu API / DB パス / 監視しきい値 / 実行環境判定等）。一部プロパティで値検証を行う（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。 (src/kabusys/config.py)
- 設定ウィザード
  - 対話式の .env 生成・更新ウィザードを実装（保存前確認あり）。デフォルト値やシークレットマスキングに対応。出力テンプレートは .env に書き込まれる旨を明示。 (src/kabusys/config_setup.py)
- 設定検証 CLI
  - 起動前の設定検証ツールを追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース（PyYAML があれば内容検証）等を実行。--strict オプションで警告を失敗扱いにできる。 (src/kabusys/validate_config.py)
- 実行系ランナー
  - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" に設定、環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH を使用）し、BrokerClientFactory からブローカークライアントを生成してエンジンをバックグラウンドスレッドで実行。停止フラグおよび PID 管理に対応。 (src/kabusys/run_execution.py)
- 監視系ランナー
  - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視機能は実行環境にかかわらず本番 sqlite_path を使用する設計。停止フラグ polling を行い、例外発生時もログ出力してループを継続。 (src/kabusys/run_monitoring.py)
- ログ設定ユーティリティ
  - 統一的なログ初期化関数を実装。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決、ログディレクトリ作成失敗時のフォールバック対応、既存ハンドラのクリーンアップを行う。 (src/kabusys/utils/logging_setup.py)
- プロセス優先度ユーティリティ
  - set_process_priority / set_cpu_affinity を実装。Windows と POSIX 系（Linux/Mac 等）の差分を吸収し、アクセス権限不足や未対応 OS の場合は警告ログを出してスキップする。 (src/kabusys/utils/process_priority.py)
- ポートフォリオ構築ライブラリ
  - 銘柄選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等金額にフォールバック。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装。既存ポジションのセクター露出を計算して新規候補を除外し、レジームに応じた投下資金乗数を提供（bull/neutral/bear をサポート）。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定ロジック（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応、lot_size（単元）で丸め、per-position と aggregate cap の制約処理、コストバッファを用いた保守的見積り、スケーリングと端数処理を実装。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージのエクスポート定義を追加。 (src/kabusys/portfolio/__init__.py)
- 研究用モジュール（基礎）
  - ファクター計算モジュール（factor_research）を追加（Momentum, Value, Volatility, Liquidity の設計方針、DuckDB を用いるインターフェースを備える。モメンタム計算関数の実装開始）。 (src/kabusys/research/factor_research.py)
- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）等を集計し、閾値に基づいて PASS/FAIL を判定。コマンドライン引数 --from/--to/--db に対応。 (src/kabusys/tools/paper_verification_report.py)
- その他ユーティリティ・インフラ
  - monitoring_db 初期化呼び出しの確保（冪等なテーブル初期化）を run_monitoring/run_execution 両方で行う。
  - 各スクリプトで duckdb / sqlite の接続を作成し、確実にクローズする処理を実装。

Changed
- ログ出力の標準化: 全起動スクリプトから setup_logging を呼ぶことでログ出力の一貫化を実現。 (複数ファイル)
- DB の分離設計:
  - 実行エンジン（Execution）は paper_trading モード時に専用の paper_trading DB を使用するように実装。監視（Monitoring）は常に監視用 sqlite_path を使用する明示的設計。 (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)
- .env 書式の柔軟化:
  - export キーワードやクォート文字、エスケープをサポートし、コメント処理を改善。 (src/kabusys/config.py)

Fixed
- 各種起動スクリプトでのリソースクリーンアップ漏れを防止（sqlite/duckdb 接続の finally での close を徹底）。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
- position_sizing の aggregate スケーリングでの端数配分を安定化（残余キャッシュ分配の安定な順序付け、上限チェック）。 (src/kabusys/portfolio/position_sizing.py)

Notes / Usage & Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD は必須（validate_config で未設定の場合はエラー）。.env.example を参考に .env を準備してください。 (src/kabusys/config.py, src/kabusys/validate_config.py)
- PAPER_TRADING:
  - KABUSYS_ENV=paper_trading の場合、Execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離されます。PAPER_FILL_MODE（instant/partial/never/reject）で模擬約定動作を制御できます。 (src/kabusys/config.py, src/kabusys/run_execution.py)
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションでログを出力します。LOG_DIR で変更可能。ログディレクトリの作成に失敗した場合はコンソール出力のみになります。 (src/kabusys/utils/logging_setup.py)
- Process Priority / Affinity:
  - 起動時に set_process_priority("high") を呼び出します。権限や OS によっては設定がスキップされます（警告出力）。CPU 固定は明示的呼び出しで行えます。 (src/kabusys/utils/process_priority.py)
- 停止フラグ:
  - 停止制御はプロジェクト内 data/stop_requested.flag 等のフラグファイルを用いています。実行環境に合わせた管理を行ってください。 (src/kabusys/run_monitoring.py, src/kabusys/run_execution.py)
- Paper Verification Report:
  - デフォルト閾値:
    - 稼働率 >= 99.0%
    - 注文成功率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms
  - DB ファイルが存在しない場合はエラーを出力します。 (src/kabusys/tools/paper_verification_report.py)

Security
- .env は絶対に Git にコミットしないでください。.env の生成テンプレートと README を参照し、機密情報（API トークン・パスワード）は環境変数で管理してください。 (src/kabusys/config_setup.py)

Deprecated
- なし

Removed
- なし

Acknowledgements / Future
- research/factor_research は設計方針と一部実装（モメンタム系）を含み、今後 Value / Volatility / Liquidity の実装を進める予定です。
- 今後のリリースで以下の点を改善予定:
  - 銘柄別単元サイズのサポート（現状は共通 lot_size）
  - price の欠損時のフォールバックロジック（前日終値等）
  - 監視・検証の追加メトリクスと alerting（LINE 通知連携の強化）

---