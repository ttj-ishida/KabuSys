# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- 重要な機能追加・仕様・動作の説明は日本語で記載しています。
- 環境変数やファイルパスなど運用に関する注意点も含めています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
最初の公開リリース。株式自動売買システムのコアユーティリティと CLI、ポートフォリオ構築・ポジション管理ロジック、検証ツール群を含む初期実装。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - 監視用 SQLite は環境にかかわらず production の sqlite_path を使用して初期化。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper 用 Mock ブローカーを利用し、専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
    - 実行中の PID 管理（data/execution.pid）および停止フラグでの安全停止をサポート。
    - 実行前に監視テーブルが存在することを保証するため init_monitoring_db を呼び出す。

- 環境設定 / 構成管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）を実装。優先順位は OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパース処理を実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理など）。
    - Settings クラスを実装し、各種環境変数（DB パス、API トークン、紙トレード設定、監視しきい値、KABUSYS_ENV 等）をプロパティとして提供。バリデーション（有効な値集合チェック）を行う。
    - PAPER_FILL_MODE 等の paper_trading 固有オプションをサポート。
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新できる CLI を追加。シークレットマスク表示、選択肢、デフォルト値の提示、最終確認後に書き込み。
  - validate_config.py
    - 起動前検証用 CLI。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在および（PyYAML があれば）パース検証を実行。
    - --strict オプションで警告を FAIL として扱うモードを提供。ライブ環境（KABUSYS_ENV=live）に対する追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）あり。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル候補の選定（スコア降順、タイブレークは signal_rank）select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコア 0 の場合は等配分にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値超過のセクターから新規候補を除外）。
    - 市場レジームに応じた投資乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは警告の上フォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" | "equal" | "score"）。
    - 単元株（lot_size）、最大ポジション比率、max_utilization、cost_buffer（スリッページ/手数料見積もり）対応。
    - aggregate cap の超過時にスケールダウンし、残余キャッシュで残差を lot 単位で再配分するロジックを実装。
    - Price 欠損や非正の価格の取り扱いに注意する実装。

- 実行・注文管理関連（起動スクリプトから呼ばれるコンポーネント）
  - run_execution から EngineConfig/ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager（RiskConfig）等を組み立てて起動することを想定（ファクトリ経由で BrokerClient を作成）。

- 監視・検証ツール
  - monitoring.monitoring_db の初期化呼び出しを共通化（冪等に監視テーブル作成）。
  - tools/paper_verification_report.py
    - Paper Trading DB を解析して検証レポートを標準出力に生成するツールを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、API レイテンシ（avg/max/P95）等の集計・閾値判定ロジックを実装。
    - 日付範囲フィルタ（--from/--to）、DB パス指定（--db / 環境変数）をサポート。
    - P95 計算、NULL/データ欠損時の N/A 出力、PASS/FAIL 判定を実装。

- 研究 / ファクター計算
  - research/factor_research.py（骨子）
    - DuckDB を用いたファクター計算モジュールの骨組みを追加。モメンタム（1M/3M/6M / MA200 乖離率）、ATR、出来高指標、バリュー指標等を計画。
    - calc_momentum のインターフェース定義と定数多数を準備（テーブル参照は DuckDB）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 共通ロギング設定: stdout StreamHandler と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定。
    - LOG_LEVEL, LOG_DIR の解決順、ファイル出力失敗時の graceful fallback（コンソールのみ）を実装。
    - stdout を使用することで cron 等の起動時のログリダイレクトに配慮。
  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac/FreeBSD）を考慮した優先度設定（high/normal/low）を実装（psutil を利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - アクセス権限等で失敗した場合は警告を出してスキップする安全設計。

- パッケージ初期化
  - 各モジュールを __all__ や package-level export を通じて公開（portfolio など）。

### Changed
- 環境ファイル読み込み方針
  - OS 環境変数は保護され、.env/.env.local は OS 環境変数を上書きしない（.env.local は上書き可能だが protected により OS 環境は保護）。
- 監視 DB の扱い
  - monitoring 用の sqlite DB 初期化は起動環境にかかわらず本番 sqlite_path を使用する仕様を明示（run_monitoring.py）。
- run_execution の DB 接続
  - paper_trading 実行時は paper_sqlite_path を使用して本番 DB と完全分離する挙動を明記。

### Fixed / Robustness improvements
- .env パーサの改善
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、空行・コメント行のスキップなどを考慮して堅牢化。
- ロギング設定の耐障害性向上
  - ログディレクトリ作成に失敗した場合でもコンソール出力のみで動作を継続するように変更。
- プロセス優先度・CPU affinity
  - 未対応 OS や権限不足時に例外で落とさず警告ログでスキップするように変更。

### Notes / 運用上の注意
- デフォルトパス
  - DuckDB: data/kabusys.duckdb（DUCKDB_PATH）
  - 監視 SQLite: data/monitoring.db（SQLITE_PATH）
  - Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - ログディレクトリ: logs/（LOG_DIR）
- Kill / Stop フラグ
  - 停止制御はプロジェクト内の data/stop_requested.flag、data/kill.flag（config によりパス変更可能）等の存在検知で行うため、運用時のファイル管理に注意。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動クリアを許可すると意図しない起動で kill flag が消されるリスクあり）。
- Paper Trading
  - KABUSYS_ENV=paper_trading の場合は発注処理は MockBrokerClient 経由で行われ、paper_trading 用 DB に記録されるため本番データと分離される。
  - PAPER_FILL_MODE でモックの約定動作（instant/partial/never/reject）を設定可能。
- 依存
  - psutil（プロセス制御）、duckdb（分析）、PyYAML（validate_config の YAML 検証は任意）などの外部ライブラリが想定される。PyYAML 未インストール時は YAML 検証をスキップする。

---

今後の予定（想定）
- research モジュールの完全実装（ファクター計算の SQL 実装完了）。
- ExecutionEngine / RiskManager / BrokerClient 等の詳細実装・テスト充実。
- 単体テスト・統合テスト、CI 設定、デプロイ手順の整備。