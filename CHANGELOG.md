CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」形式に準拠しています。  
コードベースの内容から変更点・機能を推測して記載しています。

Unreleased
----------
- ドキュメント:
  - 一部モジュール（特に research/factor_research.py の末尾）が未完成である旨を注記。
  - 将来的な改善点（価格フォールバック、銘柄ごとの単元対応など）を既知の TODO として明示。

- 既知の注意点:
  - .env 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD の存在を明確化。
  - paper_trading 環境の検証・レポート生成でデータ欠損時に N/A を出力する挙動を維持。

0.1.0 - 2026-04-18
------------------

Added
- 基本的な実行スクリプト群を追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境に応じて paper_trading 用の専用 SQLite（data/paper_trading.db）を利用し、本番 DB と分離。プロセス優先度設定、PID ファイル、停止フラグ対応を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用。

- 設定／ユーティリティ
  - config.py: 環境変数・設定管理モジュールを追加。
    - .env 自動読み込み: プロジェクトルート (.git または pyproject.toml) を探索し、.env/.env.local を適切な優先度で読み込む。
    - .env パースはシングル／ダブルクォート、export プレフィックス、インラインコメント等に対応。
    - 各種プロパティ（DB パス、PAPER_FILL_MODE の検証、KABUSYS_ENV の検証など）を提供。
  - config_setup.py: .env を対話的に作成・更新するウィザードを追加。必須項目やデフォルト値、シークレット入力のマスク表示などに対応。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パス／config/*.yaml の存在・パース確認、--strict モードをサポート。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一されたロギング設定を提供。stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs//*.log、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定 API も提供。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）・等重（calc_equal_weights）・スコア加重（calc_score_weights）を実装。
  - portfolio/position_sizing.py: position sizing ロジックを実装（risk_based / equal / score）。単元株丸め（lot_size）、aggregate cap（利用可能現金に合わせたスケールダウン）、cost_buffer（手数料・スリッページ推定）に対応。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック（1.0）し、Bear/Neutral/Bull で乗数を変化させる。

- 実行系コンポーネントの組立て
  - run_execution 内で BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立て、スレッドで ExecutionEngine を実行するワークフローを追加。停止フラグ検知で安全に停止する機構を実装。

- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。system_status/trade_logs/risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 含む）等を集計し、閾値に基づく PASS/FAIL 判定を行う。コマンドラインで期間指定および DB パス指定をサポート。

Changed
- logging の挙動設計
  - stdout を標準出力に使う方針を採用（cron 等で stdout/stderr を一本化する運用を想定）。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定することで二重設定を防止。

Fixed
- .env パースの堅牢化
  - export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等を適切に処理することで .env ファイルの柔軟な記述に対応。

- DB 初期化の冪等性確保
  - init_monitoring_db(sqlite_conn) を起動時に呼ぶことで、monitoring テーブルの存在を保証（実行・監視双方で呼び出し同一化）。

Security
- シークレットの取り扱い
  - config_setup の対話表示ではシークレット項目をマスク表示（****）してユーザーに表示する実装。

Removed
- （該当なし）初期リリースのため削除項目なし。

Notes / Implementation details
- PAPER_FILL_MODE の妥当性検証を Settings で行い、不正な値は ValueError を送出する。
- PID・停止フラグ・kill フラグ関連のファイルパスは Settings やスクリプト内定義で扱い、起動/停止の制御に使用。
- position_sizing のアルゴリズムは現状で全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別単元対応を行う設計がコメントで示されている。
- apply_sector_cap は "unknown" セクターの銘柄をセクター上限の適用外とする設計で、price が欠損する場合の補正は TODO として残している。
- research/factor_research.py は主要設計（モメンタム・ボラティリティ等）の骨組みがあるが、ファイル末尾が切れており実装が未完。

Development / Future
- research/factor_research.py の未完部分を実装（ファクター計算の最終処理、DuckDB クエリの完成）。
- 銘柄ごとの lot_size をサポートするための拡張（stocks マスタに単元情報を持たせる等）。
- position_sizing の価格フォールバック実装（前日終値、取得原価等）を追加してエッジケースを低減。
- 実稼働に向けた監視アラート（LINE 通知）設定の改善と validate_config でのチェック強化。

References
- リポジトリ内の各 CLI はモジュールを直接実行可能:
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report

以上。コードベースのコメント・実装から推測して CHANGELOG を作成しました。必要に応じて日付やバージョンの細部を編集してください。