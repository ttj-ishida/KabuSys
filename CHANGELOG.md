# Changelog

すべての重要な変更履歴をこのファイルに記載します。  
フォーマットは「Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)」に準拠します。

※ 本 CHANGELOG は提示されたソースコードから機能・修正点を推測して作成しています。

## [Unreleased]
- 今後の変更をここに記載します。

## [0.1.0] - 2026-04-11
初回リリース。日本株自動売買システム「KabuSys」の基本機能を実装。

### Added
- 実行・監視の起動スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ (data/stop_requested.flag)、実行 PID ファイル管理 (data/execution.pid) のサポート。
    - スレッドでエンジンを実行し、停止フラグで安全に停止可能。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に sqlite_path（本番パス）を使用する設計。
    - 停止フラグ (data/stop_requested.flag) 検知によるループ終了。

- 設定・環境管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（.env → .env.local、OS 環境変数を保護）。
    - export KEY=val 形式、クォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理など堅牢なパーサ実装。
    - 各種設定プロパティを提供（DB パス、PID ファイルパス、閾値、環境判定ヘルパ等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等、Paper Trading 向け設定を追加。
  - src/kabusys/config_setup.py
    - 対話式の .env 作成・更新ウィザードを提供。シークレットはマスク表示。
    - .env の読み書きユーティリティ、デフォルト値や説明付きの設定項目を実装。
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML がある場合）パース検証。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_DIR/LOG_LEVEL の環境変数対応、ログディレクトリ作成の失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティ。
    - Windows（psutil の priority class を使用）および POSIX（nice 値）に対応。CPU affinity 設定もサポート（set_cpu_affinity）。

- ポートフォリオ構築（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み付け（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等金額配分へフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存ポジションを考慮して候補をフィルタリング（"unknown" セクターは制限適用外）。
    - 市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear、未知レジームはログ出力して 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理。
    - available_cash を超えた場合のスケールダウンと残差に基づく追加配分処理を実装。

- Execution / Order 管理関連（起動時に組み立てられるコンポーネント）
  - 実行時に使用するコンポーネント群の初期化（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立て）を行うコードを追加（run_execution.py 内の組み立てロジック）。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を指定。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（data/paper_trading.db など）から統計を集計し、稼働率・注文成功率・送信率・レイテンシ等を評価してレポート出力。
    - P95 レイテンシ計算、閾値（稼働率 99% 等）による PASS/FAIL 判定を実装。
    - コマンドライン引数で期間（--from/--to）や DB パス（--db）を指定可能。

- リサーチ用ファクター計算（骨格）
  - src/kabusys/research/factor_research.py
    - モメンタム等のファクター計算の骨格を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - （注）ファイル末尾で実装が途中で切れている箇所あり（作業中）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン 0.1.0 を追加。

### Changed
- ログ設定の見直し
  - コンソール出力を stderr ではなく stdout に統一（cron/Task Scheduler でのリダイレクトを考慮）。
  - 既存ハンドラの flush/close と削除処理を経て再設定することで二重ハンドラ設定を回避。

- .env 読み込み挙動
  - プロジェクトルート検出を __file__ ベースの親ディレクトリ探索により実行（CWD 非依存）。
  - OS 環境変数は保護（protected set）して .env.local の上書きを制御。

### Fixed
- 設定パースの堅牢化
  - クォート付き値のバックスラッシュエスケープやインラインコメント処理などを正しく処理することで、.env 中の複雑な値の誤解釈を防止。
- プロセス優先度設定でアクセス権限エラーや未実装プラットフォームを例外で落とさず警告ログに切り替えるように改善。

### Known issues / Notes
- src/kabusys/research/factor_research.py は一部実装が未完（ファイル末尾で切れている）。継続実装が必要。
- 一部 TODO コメント（position_sizing の銘柄別 lot_size 拡張、apply_sector_cap の価格フォールバック等）が残っている。
- validate_config は PyYAML 非インストール時に YAML 検証をスキップして警告する動作。CI 等で厳密検証する場合は PyYAML を必須にすることを推奨。

## 参考: 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live; default: development)
- LOG_LEVEL (default: INFO)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB; default: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔、秒; default: 60)
- PAPER_FILL_MODE (instant | partial | never | reject; default: instant)
- KILL_FLAG_CLEAR_ON_START (0/1; 本番で 1 は危険)

---

（この CHANGELOG はソースコードから推測して作成しているため、実際のコミット履歴や変更差分と若干の相違があり得ます。必要であればソース管理履歴から実際の差分を抽出して正確なログを作成します。）