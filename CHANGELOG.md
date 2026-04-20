# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日はコード解析日（2026-04-20）を使用しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時に専用 MockBrokerClient / paper_trading DB を使用する分離動作をサポート。停止フラグ（data/stop_requested.flag）や pid ファイル (data/execution.pid) を監視して安全に停止できる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動。
- 環境設定・検証ツールを追加
  - config_setup.py: 対話式 .env ウィザード。デフォルト値・説明付きで .env を生成/更新する機能を提供。
  - validate_config.py: 起動前の設定検証 CLI。必須環境変数や config/*.yaml、パスの存在等をチェック。--strict オプションで警告を FAIL 扱いにできる。
- ペーパートレード検証ツールを追加
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定する。CLI で期間指定 (--from / --to) や DB 指定 (--db) が可能。
- ポートフォリオ構築関連の純粋関数群を追加
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター上限適用 (apply_sector_cap)、マーケットレジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 株数決定ロジック (calc_position_sizes)。リスクベース・等配分・スコア配分、単元株丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的計算を実装。
- 設定読み込み・検証基盤を整備
  - config.py: .env の自動読み込み（プロジェクトルート検出）、quoted 字句や export 形式のパース、OS 環境変数保護（上書き禁止）など堅牢化。Settings クラスで各種設定プロパティ（PAPER_FILL_MODE の検証、データベースパス、閾値設定、env/log_level の検証など）を提供。
- ロギングとプロセス制御ユーティリティを追加/改善
  - utils/logging_setup.py: StreamHandler を stdout に出力、TimedRotatingFileHandler（日次ローテーション・30日保持）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力にフォールバック。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity)。呼び出し側は OS を意識せずに利用可能。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用し、監視用テーブルが存在することを保証（冪等）。

### 変更 (Changed)
- 起動時の振る舞い
  - run_monitoring と run_execution が起動直後にプロセス優先度を "high" に設定するよう統一（set_process_priority を最初に呼び出し）。
  - run_monitoring は KABUSYS_ENV に依存せず Settings.sqlite_path（本番監視 DB）を使用する仕様に明示的に固定。
  - run_execution は KABUSYS_ENV=paper_trading の際に paper_sqlite_path（デフォルト data/paper_trading.db）を用いることで本番 DB と分離。
- .env 自動読み込みルール
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。OS 環境変数は protected として上書きを防止。
- .env パースの強化
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装。
- ロギングのデフォルト解決順
  - ログレベルとログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。ログファイルは logs/<app_name>.log。
- Paper Trading の分離運用
  - BrokerClientFactory を通して、paper_trading 環境では MockBrokerClient を使用する想定（実装側で動作切替）。
- position sizing のスケーリングロジック
  - aggregate cap 超過時の比例スケーリングだけでなく、lot_size（例: 100）単位での再配分（fractional remainder を使った追加割当）を実装。

### 修正 (Fixed)
- 起動・終了時のリソースクリーンアップ
  - run_monitoring/run_execution で必ず sqlite/duckdb 接続を close するよう finally ブロックを配置してリソース漏れを防止。
- 監視ループの堅牢化
  - monitor.check_once() 内で例外が発生してもログ出力してループを継続するように安全にハンドリング（監視の一時停止でプロセスが死なない）。
- ログハンドラ二重登録防止
  - setup_logging() が既存ハンドラをフラッシュ・クローズしてから削除・再設定するようにし、複数回呼び出してもハンドラが重複しないようにした。

### 破壊的変更 (Breaking Changes)
- 監視 DB の使用対象
  - run_monitoring は環境に関わらず Settings.sqlite_path を使用するため、以前の（環境依存の監視 DB を期待していた）運用は見直しが必要。
- .env 上書きポリシー
  - 自動読み込み時に OS 環境変数は保護され上書きされないため、.env に設定しても OS 側で既にセットされているキーは保持される点に注意。

### ドキュメント / 使用上の注意 (Notes)
- 環境変数の主要な設定
  - KABUSYS_ENV: development | paper_trading | live（必須ではないが検証で使用）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。1 未満や不正値はデフォルトにフォールバック。
  - PAPER_FILL_MODE: paper_trading の MockBrokerClient の約定振る舞い（instant|partial|never|reject）。不正値は ValueError。
  - KILL_FLAG_CLEAR_ON_START: 本番での自動 Kill フラグクリアは危険（validate_config で警告）。
- ログ
  - デフォルトは logs/ 以下に日次ローテーションで出力。ログディレクトリ作成に失敗した場合はコンソールのみで継続。
- CLI
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### 既知の制限 / TODO
- position_sizing の price フォールバック: open_prices が欠損（0.0）の場合、エクスポージャーや発注量が過少見積りされる可能性がある。将来的に前日終値等をフォールバックする拡張を検討中。
- research/factor_research.py はファクター計算機能の骨子を含むが、一部実装（ファイル末尾）が未完の可能性あり。DuckDB を用いた prices_daily/raw_financials 参照設計。
- strategy/実行エンジン等の実行詳細（BrokerClient 実装、ExecutionEngine の内部ロジック等）はこの変更ログでは概略のみ。各モジュールの詳細なテストとドキュメント整備が推奨される。

---

今後のリリースでは、テストカバレッジの充実、運用ドキュメント（デプロイ手順・監視運用ガイド）、および paper_trading のシミュレーション精度向上を優先して取り組む予定です。