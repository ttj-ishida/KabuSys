# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は "Keep a Changelog" に準拠します。

全てのバージョンは実装内容から推測して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回公開リリース。以下の主要機能・ユーティリティ・CLI を実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御はプロジェクトルートの `data/stop_requested.flag` を監視。
    - 監視は環境にかかわらず本番用の `sqlite_path` を使用する設計。
    - duckdb を併用した分析用接続を確立。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine を起動するメインスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離（MockBrokerClient の利用）。
    - 停止フラグ (`data/stop_requested.flag`) の存在をチェックして安全に起動/停止。
    - 起動時にプロセス優先度を "high" に設定。
    - ExecutionEngine はデーモンスレッドで実行され、フラグ検知で停止処理を行う。
    - デフォルトで PID ファイル（`data/execution.pid`）を使用。

- 環境設定管理
  - config.py
    - .env 自動読み込み機能（`.env`, `.env.local`）を実装。OS 環境変数を保護しつつ上書き制御を行う。
    - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
    - プロジェクトルート探索は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
    - .env の行パースは `export KEY=val`、クォート、エスケープ、インラインコメント等に対応。
    - 各種設定プロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, `kill_flag_path`, `cpu_threshold_pct` 等）。
    - 環境（KABUSYS_ENV）・ログレベルのバリデーションを実装。
    - `paper_fill_mode` に対する妥当性チェック（"instant" | "partial" | "never" | "reject"）。

  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加。
    - 既存 .env の読み込み、シークレット値のマスク表示、選択肢サポート、保存確認を実装。
    - デフォルト値・説明付きの項目定義を提供（J-Quants, kabuAPI, DB パス, LINE 等）。

  - validate_config.py
    - 起動前に .env と config/*.yaml の整合性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、YAML の存在・パース検査（PyYAML があれば内容チェック）を実施。
    - `--strict` オプションで警告を失敗（exit 1）として扱う。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリは引数 > 環境変数 > デフォルト の順で解決。
    - ログディレクトリ作成失敗時はファイル出力をスキップしつつ警告を出力。
    - コンソール出力は stdout を使用（stderr ではない）。

  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）を実装。
    - CPU affinity 設定のための set_cpu_affinity() を追加。
    - psutil を使用し、権限や未サポート環境では安全にスキップして警告を出す。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア合計が 0 の場合のフォールバック（等金額配分）と警告を追加。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装（allocation_method: "risk_based" | "equal" | "score"）。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、総投下上限（max_utilization）、コストバッファ考慮、aggregate cap によるスケールダウンと端数調整ロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。

- Execution 周辺コンポーネント（宣言位置）
  - run_execution が依存するコンポーネントのファクトリ・クラス参照（BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等）を起動時に組み立てる実装。RiskConfig にデフォルト値をセットし、初期ポートフォリオ値を broker.get_available_cash() から取得する設計。

- 監視・レポート関連
  - monitoring_db の初期化呼び出しを各起動スクリプトで実行（冪等）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - デフォルト DB は `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` で上書き可能）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数等を計算・表示。
    - 判定基準（閾値）を定義: 稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200 ms（ソース内定数）。
    - 日付フィルタ（--from / --to）対応、DB ファイル存在チェック、SQL の安全な実行を実装。

- 研究用モジュール（部分実装）
  - research/factor_research.py
    - DuckDB 接続を受けてファクターを計算する設計（Momentum, Value, Volatility, Liquidity）。
    - モメンタム計算のための定数・方針を実装（期間、スキャンバッファ等）。
    - 実装は関数群（例: calc_momentum）で進められているが、ファイル末尾で切れている箇所がある（今後拡張予定）。

### Changed
- （初版のため過去からの変更はなし）コード構成とモジュール分割を明確化。
- ログ出力は stdout を標準化。

### Fixed
- （初版のため過去からの修正はなし）

### Security
- .env を生成する際にシークレット項目は標準出力でマスク表示。`.env` は Git にコミットしないよう注意書きを記載。

### Notes / Operational details
- 停止フラグ/キルフラグ:
  - 停止制御は `data/stop_requested.flag`（起動停止のためのファイル）を用いる設計。
  - kill flag パスは `KILL_FLAG_PATH`（デフォルト: `data/kill.flag`）、起動時に自動クリアするかは `KILL_FLAG_CLEAR_ON_START`（デフォルト 0）で制御。validate_config で本番環境時の注意喚起チェックあり。

- DB の分離:
  - Paper Trading は本番の監視 DB と完全分離された SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用する設計になっているため、本番データと混在しない。

- ログローテーション:
  - 日次ローテーション・30 日保持でファイル出力。ログディレクトリ作成に失敗してもコンソールログは維持。

- 依存:
  - psutil（プロセス操作）、duckdb（分析用）、PyYAML（オプションで config 検証）が利用想定。PyYAML が無い場合は YAML 検証をスキップして警告。

## 今後の予定（推測）
- research/factor_research.py の完遂（ファクター計算の SQL 実装完了）。
- ExecutionEngine 周りの実装（エンジン内部ロジックの詳細実装 / 単体テスト）。
- モニタリング・アラート（LINE 通知等）の実装強化。
- 各種ユニットテストと CI 設定の追加。

---

この CHANGELOG はコードから推測して作成した要約です。実際のリリースノートや運用手順はリポジトリのドキュメントや開発者の意図に基づいて調整してください。