# CHANGELOG

すべての重要な変更を記載します。フォーマットは Keep a Changelog に準拠しています。

全般的な注意
- 本リリースはソースから推測した変更点をまとめたものです。実際の変更履歴（コミット履歴等）に基づくものではないため、運用・導入時は該当ソースの挙動を併せてご確認ください。

## [0.1.0] - 2026-04-18

### Added
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine を起動するエントリスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の MockBrokerClient を利用し、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はプロジェクト内 data/stop_requested.flag による。
- 設定・環境管理
  - config.py: 環境変数・設定を集中管理する Settings クラスを実装。自動でプロジェクトルートを探して .env / .env.local を読み込む機能を追加（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。各種パス・閾値・動作モードのプロパティを提供。
  - config_setup.py: .env を対話的に作成・更新するウィザード CLI を追加（項目: KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH 等）。
  - validate_config.py: .env と config/*.yaml の起動前検証用 CLI を追加（--strict オプションで警告をエラー扱いにできる）。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等分配・スコア加重）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用ロジックとレジーム乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score、単元丸め、aggregate cap のスケーリング）を実装。
  - portfolio/__init__.py: 上記関数群を外部公開。
- ユーティリティ
  - utils/logging_setup.py: 標準化されたロギング設定ユーティリティを追加（StreamHandler を stdout に設定、TimedRotatingFileHandler による日次ローテーション、ログディレクトリ自動作成・フォールバック処理）。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority、set_cpu_affinity）。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を解析して稼働率・注文成功率・レイテンシ等の検証レポートを生成する CLI を追加。期間指定 (--from / --to) と DB パス指定 (--db) に対応。
- リサーチ（骨格）
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールの骨格（モメンタム等の定義、計算方針、定数）を追加（詳細実装の継続が想定される）。

### Changed
- DB 周りの挙動
  - 監視系初期化（init_monitoring_db）を起動時に必ず呼び出し、監視テーブル等の存在を保証（冪等に作成）。run_monitoring は環境にかかわらず production の sqlite_path を使用する設計になっている点に注意。
  - run_execution は paper_trading モード時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離するよう変更。
- ロギング
  - ログディレクトリが作成できない場合はファイル出力をスキップし、コンソール出力のみで継続。既存ハンドラは再設定前に flush/close してクリアするように変更し、二重出力を防止。
  - StreamHandler は stdout を使うように統一（cron 等で stdout/stderr を一本化してリダイレクトする運用を考慮）。
- 環境読み込み
  - .env パーサーの仕様を強化（export プレフィックス対応、クォート中のバックスラッシュエスケープ処理、インラインコメント取り扱いの改善）。.env.local は .env の上書きとして読み込まれる（OS 環境変数は保護される）。
- プロセス優先度
  - set_process_priority は Windows / POSIX を吸収し、アクセス権限不足などの場合は警告を出して続行する堅牢化を行った。
- Risk / Execution デフォルト設定
  - Execution の RiskManager にデフォルト設定値（max_position_pct=0.20、max_utilization=0.80、rate_limit_per_sec=5、circuit_breaker_errors=10、circuit_breaker_window_sec=60、max_drawdown=0.20）を導入。initial_portfolio_value は broker.get_available_cash() を利用して初期値を決定。

### Fixed
- .env の読み書き
  - .env 読み込みでのコメント・クォート・エスケープ処理を改善し、誤って値にコメントやエスケープが混入するケースを修正（より厳密なパースロジックを採用）。
- run_execution / run_monitoring のシャットダウン挙動
  - data/stop_requested.flag による外部からの停止検出を実装。run_execution は停止検出時に engine.stop() を呼び、run_monitoring は検知次第ループを抜けるように改善。
- paper_verification_report
  - P95 計算の実装を追加し、空データの取扱いや SQL の実行エラー（テーブル未存在など）を安全に扱うフォールバックを追加。

### Deprecated
- なし（初期リリースのため該当なし）

### Removed
- なし（初期リリースのため該当なし）

### Security
- .env の生成テンプレートにて「.env は絶対に Git にコミットしないこと」を明記。config_setup の出力は秘密情報を含むため取り扱いに注意。
- Settings は必須環境変数未設定時に ValueError を送出することで、起動時に明示的に失敗させて安全側に寄せる設計。

### 注意点 / 互換性に関する情報
- Settings.env の値は "development", "paper_trading", "live" のいずれかでなければならず、その他の値は ValueError を送出します。既存環境で別の値を使っている場合は修正が必要です。
- PAPER_FILL_MODE（paper trading の fill 動作）は有効値が制限されており、不正な値を設定すると ValueError になります。事前に環境変数を確認してください（valid: "instant","partial","never","reject"）。
- run_monitoring は「監視 DB」として settings.sqlite_path を使用する設計になっているため、paper_trading 環境でも同じ sqlite_path を参照します（監視データは本番 DB に集約する意図）。監視 DB と実行 DB を完全分離したい場合は設定を調整してください。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。テスト環境やパッケージ配布後の実行で環境読み込みを抑制したい場合に利用してください。

---

今後の予定（想定）
- research/factor_research の詳細実装（DuckDB SQL によるファクター計算の完成）。
- ExecutionEngine、SystemMonitor 等のより詳細なログ、メトリクス強化。
- 単体テスト・CI の整備（設定検証 CLI を CI に組み込む等）。