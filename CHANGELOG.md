# Changelog

すべての注目すべき変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初回リリース。システム全体のコア機能（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、検証ツールなど）を実装しました。

### 追加（Added）
- パッケージ初期化
  - パッケージ名: KabuSys、バージョン `0.1.0` を設定。
  - エクスポート済みサブパッケージ: data, strategy, execution, monitoring。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアントの生成。
    - ExecutionEngine の組み立て（OrderRepository、OrderManager、RiskManager、Reconciler 等）。
    - デーモンスレッドでエンジンを実行し、data/stop_requested.flag による停止検知をサポート。
    - 起動時にプロセス優先度を設定し、PID ファイルを書き出す仕組みを有効化。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データは本番 DB を参照）。
    - stop フラグ（data/stop_requested.flag）で安全にループを終了。
    - 例外発生時にもループ継続するための例外ハンドリングを実装。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - `.env` と `.env.local` の優先順位を実装（OS 環境変数は保護）。
    - export KEY=val、引用付き値、インラインコメントなどに対応した堅牢な .env パーサを実装。
    - Settings クラスを提供し、各種環境変数をプロパティとして取得（バリデーション付き）。
    - PAPER_FILL_MODE 等の許容値チェックを実装。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - 既存 .env の読み込み、秘匿項目のマスク表示、テンプレート生成機能を実装。
    - .env ファイルの書き込み時に注意書きを出力（.env を Git にコミットしない旨）。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在チェック（PyYAML がない場合は YAML 検証をスキップして警告）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の注意喚起）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択（signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし、警告を出す）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限。既存保有を除いたセクター別エクスポージャー計算と新規候補除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームはフォールバックと警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数計算。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケーリング、cost_buffer を考慮した保守的見積り、端数処理（残余キャッシュでの追加配分）を実装。
    - 価格欠損時のスキップ・ログ出力を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - system_status, trade_logs, risk_logs などから稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を行う。
    - P95 計算ユーティリティ、日付フィルタ、閾値を定義。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging: stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（ログディレクトリ作成が失敗した場合はファイル出力をスキップ）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装、既存ハンドラのクリア、フォーマッタ設定。
    - ログ出力を stdout に固定（cron 等のログ集約を想定）。

  - utils/process_priority.py
    - set_process_priority: Windows / POSIX を吸収したプロセス優先度設定（psutil ベース、権限不足は警告でスキップ）。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定をサポート（利用不可時は警告）。

- 研究用モジュール（基礎実装）
  - research/factor_research.py
    - モメンタム等のファクター計算を行う関数群の骨子を追加（DuckDB を用いた prices_daily 参照設計、各種窓長定義）。
    - calc_momentum 等の関数を実装開始（注: ファイル末尾が断片的に存在）。

### 変更（Changed）
- 環境変数ロードの挙動
  - .env 自動ロード時に OS 環境変数を保護する仕組みを導入。（.env の値で OS 環境変数を不用意に上書きしない）
  - .env と .env.local の読み込み順を明確化（.env で未設定のキーを設定、.env.local は上書き可。ただし OS 環境変数は protected）。

- ログ出力先
  - 標準エラーではなく標準出力へログを出すことで、外部環境（crontab / Task Scheduler 等）でのリダイレクト運用を想定。

- 監視挙動
  - run_monitoring: check_once() 実行中の例外はループを停止させずログ出力して継続するように変更（堅牢性向上）。

- 実行エンジン起動
  - run_execution: スレッド監視ループに停止フラグ検出を追加。停止時は ExecutionEngine.stop() を呼んで安全に終了するように。

### 修正（Fixed）
- .env パーサの堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理など複数ケースに対応。
  - 無効行や空行、コメント行をスキップ。

- .env 書き込みテンプレート
  - config_setup の出力テンプレートに注意書きを追加（.env を Git にコミットしないよう注意喚起）。

- DB 初期化
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等操作）。run_execution / run_monitoring 起動前に必ず実行。

- エラー時のリソースクリーンアップ
  - run_monitoring / run_execution での DB 接続は finally ブロックで確実に close() するように。

### セキュリティ（Security）
- .env の取り扱いに関する注意喚起をドキュメント/ウィザードに追加。
- 設定検証で本番環境（live）の場合に通知設定（LINE）の未設定を警告する等、本番稼働時の安全ガードを実装。

### 既知の制限・注意点（Notes）
- research/factor_research.py はモメンタム等ファクターの計算骨子を含みますが、ファイル末尾に断片的な実装が残っています（未完）。リリース後に続きの実装・テストが必要です。
- position_sizing の価格欠損（price が 0.0）の扱いに関する TODO コメントあり（フォールバック価格の導入検討）。
- process_priority / set_cpu_affinity は権限やプラットフォームの違いで動作しない場合があるため、失敗時は警告ログにより継続します。

---

この CHANGELOG はコードベースの現状から推測して作成しています。細かい実装意図や追加の変更がある場合は適宜追記してください。