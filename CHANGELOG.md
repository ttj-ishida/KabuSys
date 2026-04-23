# Changelog

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。日付は本コードベースのスナップショット作成日です。

## [Unreleased]

## [0.1.0] - 2026-04-23
初期リリース。日本株自動売買システム「KabuSys」の基礎機能群を実装しました。以下の主要コンポーネントとユーティリティを含みます。

### 追加 (Added)
- コア起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClient の切り替え（paper_trading 時は MockBrokerClient を想定）、スレッドでエンジンを実行し停止フラグで制御。
    - paper_trading 環境では専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - 実行中の PID を data/execution.pid に保存する想定（pid_file を受け取る）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
    - 停止フラグ file(data/stop_requested.flag) を検知して安全にループを終了。
    - 監視は常に本番用 sqlite_path を使う（環境に依存しない挙動）。

- 設定関連
  - config.py
    - Settings クラスを追加し、環境変数から設定を取得するユーティリティを実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を基準）を実装。優先順は OS 環境 > .env.local > .env。
    - 各種既定値およびバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - データベースパス（DUCKDB_PATH/SQLITE_PATH）、paper_trading 用 sqlite パス、PID/kill flag 周りの設定を提供。
  - config_setup.py
    - 対話式 .env ウィザードを実装。既存 .env 読み込み・編集、.env ファイル書き出し機能あり。
    - J-Quants / kabu API / ログ設定 / Kill Switch 等の設定を促す。

- 設定検証 CLI
  - validate_config.py
    - .env および config/*.yaml の検証ツールを実装。必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証も行う。
    - --strict オプションで警告を FAIL 扱いにする機能を追加。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等重み・スコア重み配分関数を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap （当日売却予定銘柄の除外等を考慮）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップし、未知レジームは警告の上 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes を実装。allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリングロジック（端数分配の再現性確保）あり。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定関数 setup_logging を追加。コンソール(stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU アフィニティ設定のユーティリティを追加。アクセス権限がない場合は警告を出してスキップ。
  - tools/paper_verification_report.py
    - ペーパートレード DB（SQLite）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力するスクリプトを追加。
    - デフォルト閾値（稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from/--to）と DB パス指定オプション（--db）をサポート。

- リサーチ / ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム・ボラティリティ等のファクター計算関数の設計と一部実装。DuckDB を利用して prices_daily / raw_financials テーブルを参照する設計方針を採用。
    - 将来的に Z スコア正規化等を組み込む前提。

### 変更 (Changed)
- パッケージ情報
  - __init__.py に初期バージョン情報 __version__ = "0.1.0" を追加。

### 修正 (Fixed)
- 設定・パーサ
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを改善。これにより .env の柔軟な記述をサポート。
- run_monitoring.py / run_execution.py
  - 停止フラグの存在チェックにより、安全にプロセスを終了できるように改善。
  - DB 初期化（init_monitoring_db）を冪等に実行してテーブル不在時の起動失敗を防止。

### ドキュメント（コード内コメント）
- 各モジュールに利用方法・設計意図を示す docstring やコメントを充実させ、運用時の挙動や設計上の注意点（例: price 欠損時の影響、Bear レジームの扱い、ログ出力の stdout 使用理由など）を明確化。

### 既知の制約・注意点 (Notes)
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布後の運用を想定）。
- paper_trading 用の MockBrokerClient 実装はファクトリ経由で切り替えられる想定だが、実際の BrokerClient の詳細実装はこのスナップショットでは含まれない可能性があります。
- research/factor_research.py は一部実装が未完（コメント末尾で中断）です。実運用での完全なファクター計算は追加実装が必要です。
- process_priority・cpu_affinity の設定は権限やプラットフォームに依存するため、失敗時はログ警告でスキップされます。

### セキュリティ (Security)
- .env を絶対にリポジトリにコミットしないことを README/コメントで明示しています。
- 実行環境（KABUSYS_ENV=live）では LINE 通知設定等が未設定だとアラートが届かない旨を validate_config で警告。

---

今後の予定（提案）
- research/factor_research の完成と単体テスト追加
- BrokerClient 実装（実ブローカ / Mock）とその統合テスト
- モニタリング用ダッシュボードやメール/LINE 通知の実装強化
- 単体テスト・CI 設定および型チェックの整備

（必要であれば、変更点をファイル単位での一覧やコミットメッセージ風にさらに詳述します。）