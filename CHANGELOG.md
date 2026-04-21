# Changelog

すべての変更は Keep a Changelog の形式に従います。  
タグ付けやリリース日付はこのコードベースのスナップショットに基づいて推測しています。

注: バージョンはパッケージの __version__（0.1.0）を基に設定しています。

## [Unreleased]

（現在のスナップショットでは未リリースの変更はありません）

## [0.1.0] - 2026-04-21

初回リリース（推定） — 日本株自動売買システムのコア機能群を実装しました。主な追加点と実装上の挙動は以下の通りです。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン情報（kabusys/__init__.py に __version__ = "0.1.0" を追加）。
  - DuckDB / SQLite を用いたデータ保管と分析への基盤を導入（各コンポーネントで接続を利用）。

- 設定・環境
  - 環境変数管理モジュール（kabusys.config）
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み。
    - .env と .env.local の読み込み順を実装（OS 環境変数を保護する仕組みあり）。
    - 複雑な .env 行パース対応（export プレフィックス、クォート中のエスケープ、インラインコメント処理など）。
    - Settings クラスで各種設定値をプロパティとして提供（J-Quants、kabu API、DB パス、監視閾値、環境種別チェック等）。
    - PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - 対話式環境設定ウィザード（kabusys.config_setup）
    - .env の作成・更新を支援する CLI ウィザード（シークレット入力のマスク、デフォルト・選択肢提示、保存確認）。
  - 設定検証ツール（kabusys.validate_config）
    - .env および config/*.yaml の存在・基本妥当性を検証する CLI。--strict オプションで警告も失敗扱いに。

- 実行関連スクリプト
  - 実行エンジン起動スクリプト（kabusys.run_execution）
    - ExecutionEngine 起動フローを実装：プロセス優先度設定、DB 接続（paper_trading 時は専用 DB に分離）、BrokerClientFactory によるブローカクライアント生成、コンポーネント組み立て、別スレッドでのセッション実行と停止フラグ検出。
    - paper_trading モードでは MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離。
    - 起動時の停止フラグ検出（data/stop_requested.flag）により起動抑止。
  - 監視ポーリングループ起動スクリプト（kabusys.run_monitoring）
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず production 用の sqlite_path を使用する設計（重要な動作）。
    - 停止フラグでポーリングを終了。例外時はログを残して次回ポーリングまで待機。
  
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順・タイブレークのロジックで候補選定。
    - calc_equal_weights / calc_score_weights: 等比率・スコア加重重み計算（スコア合計が 0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中を抑制する候補フィルタ（unknown セクターは制限対象外）。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に基づく投下資金乗数（未知レジームはフォールバック）。
  - position_sizing
    - calc_position_sizes: 発注株数算出ロジック（risk_based / equal / score）を実装。単元株丸め、1銘柄上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer を考慮した保守的見積りと残差配分を実装。

- ユーティリティ
  - ロギング設定ユーティリティ（kabusys.utils.logging_setup）
    - 標準出力 (stdout) 用 StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーに統一設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップしてコンソール出力のみで継続）。
    - ログレベル解決順やログファイル命名（<log_dir>/<app_name>.log）、30 日分バックアップ等を実装。
    - 意図的に stderr ではなく stdout を使用（cron やスケジューラでのリダイレクトを想定）。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX の差を吸収し set_process_priority("high"|"normal"|"low") を提供。アクセス拒否等の場合は警告を出してスキップ。
    - set_cpu_affinity は最初の N コアにピン留めする機能。
  - DuckDB 接続を利用したリサーチ用ファクター計算モジュール（kabusys.research.factor_research）
    - モメンタム等の指標計算方針と定数を実装（ファイルはスニペット分で途中まで実装）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - paper_trading の SQLite（デフォルト data/paper_trading.db）を読み込み、稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、閾値定義（稼働率 99% など）を実装。

### 変更 (Changed)
- ログ出力の一貫化: すべての起動スクリプトが setup_logging を呼び出し、ルートロガーを共通設定することでログのフォーマットと保存先を統一。
- .env 自動ロードの挙動: OS 環境変数を保護しつつ .env/.env.local を上書きする仕組みを導入。プロジェクトルートが特定できない場合は自動ロードをスキップするように安全化。

### 修正 (Fixed)
- .env 解析の堅牢化: クォート内バックスラッシュエスケープ、インラインコメントの取り扱い、export プレフィックス対応を追加し、誤ったパースによる設定ミスを低減。
- process_priority のクロスプラットフォーム対応性強化: psutil のプラットフォーム固有定数へのフォールバックや例外ハンドリングを追加。

### 注意点 / 既知の挙動
- run_monitoring の設計上、監視 DB 接続には Settings.sqlite_path（本番用）を使用します。KABUSYS_ENV の設定に依らず監視は production sqlite_path を参照するので、運用時は意図せぬ DB 書き込みが発生しないよう注意してください（ドキュメントにもこの挙動が明記されています）。
- Paper Trading と本番 DB は分離されていますが、設定の間違いによりパスが上書きされるとデータが混在する可能性があります。validate_config および config_setup を利用して事前に確認してください。
- position_sizing の価格欠損時の取り扱いや apply_sector_cap の price fallback は将来的に改善余地がある旨の TODO コメントがあります（欠損 price による過小評価など）。
- ログディレクトリ作成に失敗した場合はファイル出力が無効化され、コンソール出力のみになります。重要な環境では LOG_DIR の書き込み権限を確認してください。

### 互換性（Breaking Changes）
- このリリースは初回と推定されるため後方互換性の観点での破壊的変更はありません。ただし、運用設定（KABUSYS_ENV、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH 等）に依存するため、既存の環境に導入する際は validate_config を実行して問題がないことを確認してください。

---

この CHANGELOG はコードから推測して作成しています。実際のリリースノート作成時は変更履歴（コミットログ）やリリース日・著者情報を併せて更新してください。