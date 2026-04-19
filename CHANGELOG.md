# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
（注: この CHANGELOG は提供されたコードベースの内容から実装・設計意図を推測して作成しています。）

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。以下の主要機能・ユーティリティを実装。

### 追加 (Added)
- 起動スクリプト / 実行系
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作する設計。
    - BrokerClientFactory により環境（本番/ペーパー）に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session を別スレッドで実行。
    - data/execution.pid に PID を書き、 data/stop_requested.flag で停止制御を行う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定、停止フラグの検知、例外発生時のロギングと継続動作を実装。

- 設定 / 環境
  - config.py
    - Settings クラス実装。環境変数から各種設定値を取得するプロパティ群を提供（DB パス、API トークン、KABUSYS_ENV 等）。
    - 自動 .env ロード機能: プロジェクトルート（.git または pyproject.toml を基準）を探索し、.env / .env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env パーサは export プレフィックス、クォート（シングル・ダブル）、エスケープ、インラインコメントの扱いに対応。
    - 環境値のバリデーション（KABUSYS_ENV の許容値、LOG_LEVEL の許容値、PAPER_FILL_MODE の許容値など）。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。シークレット入力のマスキング、デフォルト提示、確認プロンプト付き。
  - validate_config.py
    - .env と config/*.yaml の事前検証を行う CLI を実装。必須環境変数チェック、パス存在チェック、YAML パース（PyYAML がインストールされている場合）、本番時の追加警告等を実装。`--strict` モードで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。コンソール (stdout) 出力と日次ローテートされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリの自動作成、既存ハンドラのクリア、ログレベル解決ロジックを実装。
  - utils/process_priority.py
    - set_process_priority(level) で Windows / POSIX を吸収したプロセス優先度設定を提供（psutil ベース）。アクセス不可や未対応 OS は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count) で CPU affinity を設定するユーティリティも実装。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N 件を選出。
    - calc_equal_weights: 等金額配分（各銘柄 1/N）。
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等配分へフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を監査し、上限超過セクターの候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull / neutral / bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づいて買い数量を算出。単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer を考慮した保守的見積りを実装。

- ツール
  - kabusys.tools.paper_verification_report
    - ペーパートレード用 SQLite から期間集計を行い、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを計測して PASS/FAIL 判定を出力する CLI を実装。
    - デフォルト DB は data/paper_trading.db。CLI オプションで期間指定・DB パス指定可。
    - 基準値（稼働率 99% など）を定義し、欠損データを考慮した判定ロジックを持つ。

- research/factor_research
  - ファクター計算モジュールの導入（モメンタム等を計算する設計）。DuckDB 接続を受け取り prices_daily / raw_financials を利用して計算する方針を実装（コード一部に続きあり）。

### 変更 (Changed)
- ロギングのコンソール出力は stdout を使用するよう設計（cron / バッチ実行環境での stdout/stderr リダイレクトを想定）。
- run_execution 内で監視テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等的に監視テーブルを準備）。
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされない）。

### 修正 (Fixed)
- .env パーサの堅牢化
  - export プレフィックスのサポート、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いを改善。
  - ファイル読み込み失敗時に警告を出すようにし、ロード失敗でクラッシュしない挙動に変更。
- process_priority / set_cpu_affinity は権限不足や未対応 OS を捕捉して警告ログを出しスキップするようにしている（起動失敗を避ける）。

### 注意点 / 既知の制約 (Notes / Known issues)
- research/factor_research の実装は（提供されたスニペットの範囲では）一部が切れており、完全実装（全ファクター計算・テスト）は継続作業が必要。
- apply_sector_cap 内で price が欠損（0.0）の場合に過少評価される可能性があり、将来的なフォールバック（前日終値など）の検討をコメントで明示している。
- position_sizing では現状 lot_size がグローバルに固定（引数で与えられるが銘柄毎の単元対応は未実装）。将来的に銘柄別 lot_map を使う拡張が想定されている。
- ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続する挙動（失敗時のフォールバック実装）。
- run_monitoring は監視用 DB に常に settings.sqlite_path（本番想定パス）を使う設計であるため、開発環境での監視データ分離を行いたい場合は設定の上書きに注意。

### セキュリティ (Security)
- 機密値（J-Quants リフレッシュトークン、kabu API パスワード等）は .env に保存する前提。config_setup の出力時に「.env は絶対に Git にコミットしないこと」と明示しているが、運用での取り扱いに注意が必要。

---

変更・追加点の詳細や誤植・補足事項が必要であれば、コードの特定ファイルごとにより詳細な変更履歴を作成します。どの形式（例: Git コミット単位や機能別）での分割を希望するかを教えてください。