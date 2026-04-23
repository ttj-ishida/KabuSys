# Changelog

すべての重要な変更をここに記録します。これは Keep a Changelog の形式に準拠しています。  

初期リリースや機能追加の多くはソース内の docstring と実装から推測して記載しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

最初の公開バージョン。システム全体の起動スクリプト、設定管理、監視・実行の基盤、ポートフォリオ構築ユーティリティ、各種 CLI ツール、およびユーティリティ関数群を追加。

### Added
- 全体
  - パッケージ初版を追加（__version__ = "0.1.0"）。
  - 各モジュールに詳細な docstring と実装コメントを付与。

- 起動スクリプト / 実行
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による paper_trading モード専用の SQLite パス分離（data/paper_trading.db を想定）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせてエンジンを起動。
    - ストップフラグファイル（data/stop_requested.flag）検知による安全停止。
    - 実行 PID を data/execution.pid に記録・参照する仕組み（pid_file の利用）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - stop フラグファイル検知でループを終了。
    - 例外発生時にもループ継続しログ出力で復帰する堅牢化。

- 設定・環境管理
  - config.py: 環境変数管理クラス Settings を追加。
    - .env 自動ロード機構（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env のパースは export プレフィックス、クォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - 各種設定プロパティを提供（DB パス、paper_trading 用設定、監視しきい値、ログレベル、KABUSYS_ENV 等）。
    - OS 環境変数を保護するための上書きポリシーを実装。
  - config_setup.py: 対話式 .env 設定ウィザードを追加。
    - 一連の項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）に基づき .env を生成/更新。
    - シークレット項目はマスク表示、デフォルト/既存値の再利用サポート。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス存在チェック（親ディレクトリ存在確認）、config/*.yaml の存在およびパース（PyYAML が存在する場合）を実施。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）。
    - --strict オプションで警告も失敗扱いに可能。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分とスコア加重配分（スコア全てが0のときはフォールバックで等金額配分）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限に基づく候補フィルタリング（売却予定銘柄除外等を考慮）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: weight/score/risk_based に対応した株数決定ロジック。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer による保守的見積り、端数配分ロジックを実装。

- ツール
  - tools.paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status, trade_logs, risk_logs から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - Pass/Fail 判定の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
    - --from / --to / --db オプションをサポート。

- ユーティリティ
  - utils.logging_setup:
    - setup_logging(): ルートロガーを統一的に設定（stdout StreamHandler と日次ローテートする TimedRotatingFileHandler）。
    - 既存ハンドラをクリアして二重設定を防止。
    - LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils.process_priority:
    - set_process_priority(): Windows/Linux/Mac の差分を吸収してプロセス優先度を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity(): 指定コア数へのピン止めをサポート（権限不足や未対応 OS は警告でスキップ）。

- 研究モジュール（着手）
  - research.factor_research: モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。一部実装が続き（ファイル末尾で途切れ）として含まれる。

### Changed
- ロギングの挙動を明示的に統一
  - setup_logging() が既存ハンドラを安全にクローズしてから再セットアップするようにして、複数回呼び出し時の二重出力を防止。
  - コンソール出力は stdout を使う設計に統一（cron 等でのリダイレクト運用を想定）。

- 環境変数読み込み順の明確化
  - OS 環境変数 > .env.local > .env の優先度で自動ロード（自動ロード無効化用 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意）。

### Fixed / Hardening
- .env 読み込みの堅牢化
  - export プレフィックス、引用符付き値のバックスラッシュエスケープ、インラインコメント処理などに対応してパーサを強化。
  - .env ファイル読み込み失敗時は警告を出して起動継続（テストや CI を配慮）。

- デーモン/スレッド安全性
  - ExecutionEngine はデーモンスレッドで起動し、監視ループから停止フラグを検知したら engine.stop() を呼ぶことで安全退出を試みる。

- DB 初期化
  - init_monitoring_db(sqlite_conn) を run_execution/run_monitoring 起動時に冪等に呼び出して監視テーブルの存在を保証。

### Notes
- 環境変数の設定例や必須項目は .env.example を参照すること。必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD。
- 本番運用時は KABUSYS_ENV=live を設定し、LINE 通知設定や KILL_FLAG の取り扱い（KILL_FLAG_CLEAR_ON_START）に注意すること。
- paper_trading モードでは paper 専用の SQLite DB を使用して本番 DB と分離する設計。
- DuckDB は分析用データベースとして利用（パスは DUCKDB_PATH 環境変数で指定可）。

---

（この CHANGELOG はソースコードの内容から機能・変更点を推測して作成しています。実際のコミット履歴とは差異が生じる場合があります。）