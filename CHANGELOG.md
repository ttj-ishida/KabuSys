# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、重大度順にまとめています。

注意: 以下の履歴はソースコード（src/ 以下）の内容から推測して作成しています。実際のコミット履歴がある場合はそちらを優先してください。

## [Unreleased]
- ドキュメント、テスト、細かな改善やリファクタリングが将来追加される可能性があります（コード内に TODO コメントあり）。

---

## [0.1.0] - 2026-04-19

### 追加
- プロジェクト基本パッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: __version__ = "0.1.0"。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを提供。
    - KABUSYS_ENV に応じて本番/ペーパートレード DB 分離を実現（paper_trading 環境では PAPER_TRADING_SQLITE_PATH を使用）。
    - BrokerClientFactory によるブローカークライアントの抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み合わせてセッションをスレッドで実行。
    - data/stop_requested.flag による外部停止フラグ対応、実行 PID ファイルの使用。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境に関係なく本番 sqlite_path を使用（監視用 DB 初期化・接続処理を含む）。
    - 停止フラグ検出、例外キャッチでループの安定稼働を確保。
- 設定・環境管理
  - config.py: 環境変数読み込みと Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）に基づく .env 自動読み込み（.env と .env.local、OS 環境変数優先、.env.local は上書き）。
    - .env パースにおいてクォート／エスケープ／インラインコメント対応。
    - Settings に多くの設定プロパティ（DB パス、API トークン、閾値、環境判定ユーティリティ等）を提供。
    - PAPER_FILL_MODE のバリデーション実装。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 質問型インターフェースで必須/任意項目を促し、.env を生成。
    - .env をコミットしない旨の警告テンプレート出力。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認。
    - --strict オプションで警告を FAIL 扱いにできる。
    - PyYAML 未インストール時の挙動（パーススキップ）に配慮。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログディレクトリの自動作成失敗時にもフォールバックして動作。
    - 環境変数 LOG_LEVEL / LOG_DIR を尊重。
  - utils/process_priority.py:
    - cross-platform（Windows / POSIX）でのプロセス優先度設定（high/normal/low）を提供。
    - CPU affinity を指定する set_cpu_affinity 関数を追加。
    - 権限不足や未対応 OS の場合は警告を出して処理をスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計がゼロの場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装（売却予定銘柄除外、unknown セクターは除外しない）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知値はフォールバックと警告）。
  - portfolio/position_sizing.py:
    - ポジション株数計算 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、1銘柄上限、aggregate cap によるスケーリング／端数処理（lot 単位での再配分）などを実装。
    - cost_buffer による手数料・スリッページ見積りを許容。
- 解析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う（閾値はソース内定義）。
    - 日付フィルタ、コマンドライン引数（--from/--to/--db）に対応。
- 研究用モジュール（骨組み）
  - research/factor_research.py: DuckDB 接続を受け取りファクター計算を行う設計の雛形を追加（モメンタム等の計算ロジックの開始）。※一部未完（ファイル末尾で途切れ）。

### 変更
- 監視/実行スクリプトの振る舞い
  - run_monitoring はモニタリング用 DB 初期化を保証（init_monitoring_db を呼び出す）。
  - run_execution はペーパートレード環境時に専用 SQLite を使って本番 DB と分離。
- .env 自動読み込みの動作
  - OS 環境変数を保護する protected 機構を導入し、.env.local は OS 変数を上書きしない。
  - プロジェクトルート検出を __file__ ベースで行うことで CWD に依存しないよう改善。
- ログ設定
  - 出力先に stdout を明示的に使用（cron / scheduler でリダイレクトしやすくするため）。
  - 既存ハンドラを一度削除して再設定する実装により二重出力を防止。

### 修正（バグ修正・堅牢化）
- MONITOR_POLL_INTERVAL のパースで不正値（0 や負、非整数）を検出しデフォルトにフォールバック、かつ警告を出力するように改善（time.sleep に渡す不正値対策）。
- process_priority.set_process_priority:
  - 未対応 OS や権限不足時に例外で停止しないよう例外捕捉と警告ログを追加。
- config._load_env_file:
  - .env 読み込みでファイル I/O エラー発生時に警告を出し続行するよう安全化。
- config._parse_env_line:
  - クォート内エスケープ、インラインコメントの扱い、export プレフィックス対応などを実装し .env パースを堅牢化。
- generate_report / paper_verification_report:
  - DB に該当テーブルが存在しない場合でもエラーで落ちないよう sqlite3.OperationalError を捕捉してデフォルト値で続行。

### ドキュメント（コード内コメント）・注記
- 各モジュールに設計方針、使用例、注意点（例: .env を Git にコミットしない等）を詳細に記載。
- portfolio モジュールに将来の拡張点（銘柄別 lot_size、価格フォールバック等）の TODO を付記。
- config_setup で生成される .env テンプレートに注釈を追加（Kill Switch、ログ設定等の項目説明）。

### 既知の制約 / TODO
- research/factor_research.py は一部未完（ファイル末尾で途切れている箇所あり）。追加のファクター計算ロジック実装が必要。
- position_sizing の価格欠損時のハンドリングに注記あり（現状 0.0 を使用すると過少見積もりのリスクがあるため、将来的に前日終値等のフォールバックを検討）。
- 単体テスト・統合テストはソース内に明示的なテストファイルが見当たらないため、追加を推奨。

---

今後のリリース候補（参考）
- 0.1.x: research モジュール完成、ユニットテスト追加、細かなバグ修正
- 0.2.0: ExecutionEngine/Strategy 実装の拡張、運用向け監視アラート（LINE 通知）完全実装、リスク管理のチューニング

--- 

（注）この CHANGELOG はソースコードから推測して生成しています。実際のコミットメッセージや日付がある場合はそれに合わせて調整してください。必要ならば各ファイルごとのより詳細な変更点や、未完の関数位置（research/factor_research.py の続きなど）についても追記します。