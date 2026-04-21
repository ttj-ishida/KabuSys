# CHANGELOG

すべての重要な変更を記録します。慣例に従いセマンティックバージョニングを採用します。

フォーマットは「Keep a Changelog」を参考にしています。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 初期リリースとして以下の主要コンポーネントを実装・公開。
  - 実行・監視用エントリーポイントスクリプト
    - run_execution.py: ExecutionEngine を起動するスクリプトを提供。スレッドでエンジンを起動し、data/execution.pid への PID 管理、data/stop_requested.flag による停止制御を実装。
    - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを提供。停止フラグ、例外ハンドリング、MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
  - 環境設定・検証用ツール
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を実装（シークレット項目のマスク表示、保存前の確認、.env を Git にコミットしないよう注意喚起）。
    - validate_config.py: .env と config/*.yaml の静的検証 CLI を提供。必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、PyYAML がない場合のスキップ通知、--strict モードで警告を FAIL 扱いにするオプション等を実装。
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）からパフォーマンス／安定性指標を集計・レポート出力するスクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）判定などを行う。CLI で期間や DB パスを指定可能。
  - 設定管理
    - config.py: .env ファイルの自動読み込み（プロジェクトルート検出）を実装。設定値をプロパティとして提供する Settings クラスを追加。多くの環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_* 等）をラップ。
    - .env パーサーは引用符付き値やエスケープ、インラインコメントの取り扱いに対応。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - portfolio/risk_adjustment.py: セクター集中除外ロジック (apply_sector_cap)、市場レジームに応じた乗数 (calc_regime_multiplier、"bull"/"neutral"/"bear" をマッピング) を実装。
    - portfolio/position_sizing.py: position sizing ロジックを実装。risk_based、equal、score の配分方式をサポート。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りなどを実装。
    - portfolio/__init__.py で上記関数群を公開。
  - ユーティリティ
    - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の解決ロジックを実装。既存ハンドラのクリア処理を行う。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX(nice)）と CPU affinity 設定ユーティリティを追加。失敗時は警告を出してスキップする安全設計。
  - データ解析基盤
    - DuckDB を利用する設計を導入（Settings.duckdb_path、各コンポーネントが duckdb 接続を受け取る）。
    - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム / MA / ATR / リクイディティ指標などの方針と定数）を実装（calc_momentum 等の実装開始）。
  - その他
    - パッケージの基本情報を __init__.py に追加（__version__ = "0.1.0"）。

### 変更 (Changed)
- ログ出力ポリシー
  - ログのコンソール出力は stdout を使用するよう明示（cron/task runner のリダイレクト運用を想定）。
  - ログファイルはデフォルト logs/ 以下に日次ローテーションで保存される（バックアップ 30 日）。
- Execution / Monitoring の DB 接続ポリシー
  - run_execution: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、発注ログ等を本番 DB と分離。
  - run_monitoring: 監視用テーブルの初期化は環境にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用して行う旨を明示（監視データは本番 DB に集約する設計）。
- 環境変数のデフォルトと検証強化
  - PAPER_FILL_MODE（paper trading の fill 動作）に対して有効値チェックを実装（"instant" / "partial" / "never" / "reject"）。
  - KABUSYS_ENV / LOG_LEVEL の検証を Settings 側で追加。validate_config でも整合性チェックを実施。
- エラー耐性
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げた場合に例外ログを出して次のポーリングへ回復するように変更（監視の頑健化）。
  - run_execution/run_monitoring 共に finally ブロックで SQLite / DuckDB 接続を確実にクローズ。

### 修正 (Fixed)
- .env パーシングの挙動を改善
  - export プレフィックス対応、引用符内のバックスラッシュエスケープ、インラインコメントの取り扱いを追加して実運用での .env 設定の柔軟性を向上。
- validate_config の検査項目追加・メッセージ改善
  - config/*.yaml の存在確認処理を追加し、PyYAML 未導入時はパース検証をスキップして警告を出すようにした（依存性に左右されない挙動）。
  - 必須環境変数がプレースホルダ（例: *_here, your_value）のままの場合に警告を出す。

### ドキュメント (Documentation)
- 各スクリプト／モジュールの docstring を充実化。使い方、環境変数、想定挙動、設計上の注意点（例: .env を絶対に Git へコミットしない旨）を明記。

### 既知の制限 / TODO (Known issues / TODO)
- research/factor_research.py はファクター計算の方針と定数を含むが、一部関数の実装が未完（ファイル末尾が途中で切れているような状態）。完全実装は今後の作業予定。
- portfolio/position_sizing.py にて、銘柄ごとの lot_size を将来的にサポートする旨の TODO（現在は共通 lot_size を想定）。
- apply_sector_cap 内で価格情報が欠損（price が 0.0）の場合にエクスポージャーが過少見積りされる可能性がある点を注記。将来的にフォールバック価格の導入を検討。

### セキュリティ (Security)
- シークレット扱いの環境変数（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に平文保存される設計のため、.env の取り扱いや配布に注意すること（config_setup.py のヘッダでも Git にコミットしないよう明示）。

---

何か抜けや間違いがありそうでしたら、特に重点的に説明して欲しい箇所（例: 実装の振る舞い、環境変数の一覧、CLI の使い方など）を指定してください。必要に応じて CHANGELOG の細分化・追記を行います。