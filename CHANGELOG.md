# Changelog

すべての重要な変更は Keep a Changelog の指針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [0.1.0] - 2026-04-24
初回リリース。KabuSys のコア CLI/ユーティリティ、実行エンジン起動スクリプト、監視、ポートフォリオ構築、及び各種ユーティリティ関数群を追加。

### 追加
- 全体
  - パッケージ初期化とバージョン定義を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB / SQLite を併用するデータレイヤーのサポートを導入（設定経由でパス指定）。
- 起動/運用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV による paper_trading モードを判定し、paper_trading 時は専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動処理（別スレッド実行、停止フラグ検知、PID ファイル管理）。
    - 停止フラグ（data/stop_requested.flag）と実行 PID（data/execution.pid）を利用した安全な停止処理。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境に依存せず本番用 sqlite_path を使用する仕様。
    - 停止フラグ検知でループ終了、例外発生時はロギングして次サイクルへ継続。
- 設定管理
  - config.py: 環境変数/ .env 自動読み込みと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local をプロジェクトルートから読み込む。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env ロード時、OS の既存環境変数を保護する仕組み（protected set）。
    - .env のパースを堅牢化（export プレフィックス、クォート内のバックスラッシュエスケープ、コメント処理等に対応）。
    - 各種設定プロパティを提供（J-Quants、kabu API、DuckDB/SQLite パス、paper trading 関連、監視閾値、環境判定等）。
    - PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）。
- 設定ツール / 検証
  - config_setup.py: 対話式 .env ウィザードを追加。
    - UI で主要設定を入力し .env を生成/更新。シークレット項目は表示マスク。
    - デフォルト値・選択肢・説明を表示し、保存確認後に .env を書き出す。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML があれば実施）。
    - --strict オプションで警告を Fail 扱いに変更可能。
    - 本番（live）用の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
- ポートフォリオ/戦略関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分ロジック、全スコアが 0 の場合は等分配へフォールバック。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェックにより候補を除外するロジック（売却予定銘柄はエクスポージャー計算から除外、unknown セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告して 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元株（lot_size）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap によるスケールダウン処理を実装。
    - risk_based モードでは risk_pct, stop_loss_pct に基づく株数決定。
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - SQLite（paper trading DB）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、Pass/Fail を判定する閾値を組み込み。
    - コマンドラインで期間指定（--from/--to）や DB 指定（--db）が可能。
- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定、ファイル出力失敗時のフォールバック（コンソールのみ）。
  - utils.process_priority: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定を追加。
    - Windows/POSIX に対応した優先度設定（high/normal/low）。権限不足時は警告してスキップ。
    - set_cpu_affinity によるコア固定機能（利用可能コア数チェック・権限不足時は警告してスキップ）。

### 変更（設計上のポイント）
- 設定の自動ロード順序を明確化
  - OS 環境変数 > .env.local > .env（.env.local は .env より優先して上書き。ただし OS 環境変数は保護）。
- ロギング
  - stdout を使用する StreamHandler を採用（cron 等で stdout/stderr を一本化する運用を想定）。
  - ログファイルの生成に失敗した場合でもプロセスは継続、ログはコンソールへフォールバック。
- 監視と実行の停止制御
  - data/stop_requested.flag（停止フラグ）や PID ファイルにより外部からの停止制御・liveness をサポート。
- データベース分離
  - paper_trading（シミュレーション）用 DB と本番監視 DB を明確に分離することで、テスト/検証と本番データの混同を防止。

### 修正（バグ修正 / 安全対策等）
- .env パーサーの堅牢化
  - export プレフィックス、クォート中のバックスラッシュエスケープやインラインコメントの扱いを正しく処理するよう修正。
- 設定取得の退避・検証強化
  - Settings クラスの各プロパティで不正な値（例: KABUSYS_ENV の未知値、LOG_LEVEL の未知値、PAPER_FILL_MODE の不正値）を検出して ValueError を送出するようにして起動前に問題を検出しやすくした。
- polling 関連
  - MONITOR_POLL_INTERVAL の不正値（整数変換失敗や 0 以下）を検出し、警告ログを出してデフォルトへフォールバックする挙動を追加（time.sleep に渡す不正値による例外回避）。
- process_priority / affinity
  - 権限不足や未サポート環境での例外を捕捉して警告ログを出し、プロセス継続を確保。

### 既知の制約 / TODO
- position_sizing.calc_position_sizes:
  - open_prices に欠損（0.0）がある場合、エクスポージャーが過少見積りされブロックが外れる可能性がある旨を注記。将来的には前日終値等のフォールバック価格導入を検討。
- apply_sector_cap:
  - "unknown" セクターは上限制限の対象外としているため、マスタにセクター情報がない銘柄の取り扱いに注意が必要。
- config_setup / validate_config:
  - config/*.yaml のパースは PyYAML に依存。PyYAML 未インストール時は YAML 検証をスキップする（警告のみ）。
- ログディレクトリ作成失敗時はファイルハンドラを無効化する仕様（権限やコンテナ環境での注意点）。

### セキュリティ
- .env の生成時に注意文を付与（.env を絶対に Git にコミットしないことを明示）。

---

今後の予定（例）
- ExecutionEngine / SystemMonitor のユニットテスト追加。
- ポートフォリオ構築ロジックのチューニングとシミュレーション検証ツールの拡張。
- 銘柄毎の lot_size 等をマスタ化して position sizing を拡張。