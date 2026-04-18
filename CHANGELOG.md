# Changelog

すべての変更は「Keep a Changelog」形式に従って記載しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 2026-04-18

### Added
- 全体
  - 初期公開リリース。日本株自動売買システム「KabuSys」の基礎モジュール群を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て、ExecutionEngine のデーモン実行を実装。
    - 起動時にプロセス優先度を設定し、停止フラグ（data/stop_requested.flag）検知で安全にエンジン停止するロジックを実装。
    - PID ファイルの取り扱い（settings での pid_file_path 指定）に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイントを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）でポーリング間隔を上書き可能。
    - 停止フラグ検知、例外時のログ出力、起動時プロセス優先度設定、sqlite / duckdb コネクション管理を実装。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env 読み込みの上書き制御（.env, .env.local の優先度）、OS 環境変数の保護（protected keys）に対応。
    - .env パース機能を強化（`export KEY=…`、クォート値、インラインコメントの取り扱いをサポート）。
    - Settings クラスを実装し、J-Quants / kabu API / DB パス /監視・システム設定等のプロパティを提供。
    - PAPER_FILL_MODE（paper trading の fill 挙動）等の検証ロジックを組み込み（有効値検査）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードによる .env の作成・更新機能を実装。
    - J-Quants トークンや kabu API パスワード等の秘匿項目はマスク表示、デフォルト値・選択肢サポート。
    - .env の読み書きフォーマットを定義（コミット禁止の注意文含む）。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を実装。
    - 必須環境変数の有無チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば config/*.yaml のパース検証を行う。
    - `--strict` オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定する共通ユーティリティを追加。
    - LOG_DIR 環境変数 / 引数でログ出力先を指定可能。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - 既存ハンドラをクリアして二重登録を防止。
  - utils/process_priority.py
    - プロセス優先度（high/normal/low）を Windows / POSIX の差分を吸収して設定するユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応環境では警告ログでスキップする安全設計。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナルから候補抽出(select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を実装。スコア合計が 0 の場合は等金額フォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有をもとに特定セクターが上限超過なら新規候補をフィルタ。
    - レジームに応じた投下資金乗数(calc_regime_multiplier) を実装（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック(calc_position_sizes) を実装。`risk_based` と `equal/score` の割当方式に対応。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer による保守的コスト見積り、available_cash に基づくスケーリングを実装。残差に基づく追加配分アルゴリズムも実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite ログを集計して検証レポートを出力する CLI を実装。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下件数、レイテンシ（avg/max/P95）を算出し、閾値判定（PASS/FAIL）を行う。
    - P95 算出ロジック、日付フィルタ、DB ファイル存在チェック、閾値は定数で明示。
- その他
  - monitoring DB の初期化ユーティリティ（init_monitoring_db）および SystemMonitor / ExecutionEngine 側での DB 初期化呼び出しを組み込み（冪等に実行）。
  - モジュール公開インターフェースを package level に整理（kabusys.portfolio の __all__ 等）。

### Changed
- 起動スクリプト/設定
  - 監視コンポーネント（run_monitoring）では KABUSYS_ENV に関係なく本番用 sqlite_path を参照する設計を採用（監視は環境に依存しない想定）。
  - run_execution は paper_trading 環境時に DB の分離を徹底（settings.paper_sqlite_path を使用）。
- .env 読み込みロジック
  - .env の読み込み順序を OS > .env.local (override) > .env（初期値）に明確化。
  - OS 環境変数を保護するため protected keys を導入し、.env.local 等で OS 変数を誤って上書きしないようにした。
- ロギング
  - StreamHandler を stdout に固定し、cron 等でのリダイレクト取り扱いを想定した設計に変更。

### Fixed
- 安全性 / 堅牢性
  - process_priority / set_cpu_affinity は権限不足や未対応 OS で例外になるケースを捕捉し、警告ログで処理をスキップするようにして起動失敗を回避。
  - logging_setup: ログディレクトリ作成失敗時に print で警告を出し、ファイルハンドラ作成失敗も捕捉してコンソールのみで継続するように改善。
  - run_monitoring / run_execution: 停止フラグ検知や KeyboardInterrupt による優雅なシャットダウン処理を追加。
  - .env パーサー: export 形式、クォート値、バックスラッシュエスケープ、インラインコメントを適切に扱うよう改良し、一般的な .env 書式差異に対応。
- position_sizing
  - aggregate cap 適用時のスケーリング・端数処理（lot_size 単位での調整）と残余資金を利用した追加配分ロジックを修正して、合計投資が available_cash を超えないようにした。

### Notes / Known limitations
- research/factor_research.py はモメンタム等のファクター計算機能を導入していますが（DuckDB を使った設計、定数群の定義）、ファイル末尾が途切れており実装完了/テストが必要（calc_momentum 等の実装継続を予定）。
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる点は TODO コメントとして残しており、将来的にフォールバック価格の採用を検討。
- ExecutionEngine / SystemMonitor 等の内部実装（エンジン詳細、ブローカークライアントの実装、monitoring_db のスキーマ等）はこのリリースに含まれるが、外部依存（ブローカー API、DuckDB / SQLite の実データ）での実行検証が必要。

### Security
- 本リリースでは特にセキュリティ修正は含まれていません。機密情報（.env）については .env を Git にコミットしない旨の注意書きを config_setup に明記。

---

この CHANGELOG は、ソースコードの内容から推測して作成しています。さらに詳細な変更履歴やコミット単位の差分が必要な場合は、Git のコミットログやリポジトリの履歴を参照してください。