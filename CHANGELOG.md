# Changelog

すべての変更は https://keepachangelog.com/ja/ の仕様に準拠して記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能とユーティリティを実装しています。

### Added
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）を監視してグレースフルに終了。
    - 監視は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する挙動を明示。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite (デフォルト: data/paper_trading.db) を使用して本番 DB と分離。
    - BrokerClientFactory を利用しブローカークライアントを生成、ExecutionEngine をスレッド起動して停止フラグで停止可能にする。
    - 実行用 PID ファイル管理（data/execution.pid）をサポート。

- 設定管理・ユーティリティ
  - config.py
    - 環境変数読み込みロジックを実装（.env/.env.local 自動ロード、.env の行パーサ実装）。
      - `export KEY=val` 形式とクォート付き値（バックスラッシュエスケープ対応）、インラインコメント処理に対応。
    - 環境変数取得ラッパ `Settings` クラスを提供（各種デフォルト・バリデーションを含む）。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーションを実装。
    - paper_sqlite_path / duckdb_path / sqlite_path 等のパス取得を標準化。
  - config_setup.py
    - .env を対話的に作成・更新するウィザード CLI を実装。
    - シークレット項目はマスク表示し、Enter で既存値・デフォルトを再利用可能。
    - 出力フォーマットとテンプレート（コメント付き）で .env を書き出す機能を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パース検証（PyYAML がインストールされている場合）などを実行。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合に等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）を実装。既存保有のセクター暴露に基づいて当日新規候補を除外する。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" マッピング、未知レジームは警告してフォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
    - cost_buffer による保守的コスト見積り、スケーリング後の残差分配ロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定関数 setup_logging を実装。
    - コンソール出力は stdout、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリは引数 / LOG_DIR / デフォルト logs/ で決定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する堅牢化。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を実装。
    - 権限不足などの例外は警告ログに降格して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計して PASS/FAIL 判定を出力。
    - デフォルト DB パスは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - P95 計算、および日付フィルタ（ISO8601 UTC 変換）をサポート。
  - tools パッケージ初期化ファイルを追加（空）。

- 研究モジュール（スキャフォールディング）
  - research/factor_research.py
    - ファクター計算の設計方針とモメンタム指標計算関数のスケルトンを追加（DuckDB 接続を用いた計算を想定）。モメンタム計算の定数設定や docstring を実装（実装は一部未完）。

- パッケージ情報
  - kabusys/__init__.py にてバージョンを設定: __version__ = "0.1.0"

### Changed
- なし（初回リリースのため既存の変更履歴はありません）。

### Fixed
- なし（初回リリース）。

### Security
- 環境変数管理に関する注意書き:
  - .env は絶対に Git にコミットしない旨を config_setup の出力ヘッダに明記。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テスト用途など）。

### Notes / Implementation details
- run_monitoring と run_execution の両起動スクリプトは起動時に set_process_priority("high") を呼び出し、プロセス優先度を上げる設計（失敗時は警告）。
- config の自動ロードはプロジェクトルート検出（.git または pyproject.toml）に基づいて行われるため、パッケージ配布後も動作するように CWD に依存しない実装となっている。
- validate_config は PyYAML の有無で挙動が変わる（未インストール時は YAML 検証をスキップして警告）。
- portfolio モジュールは副作用のない純粋関数群として設計され、DB 参照を行わずメモリ内計算で完結する。

---

（今後のリリース候補）
- research/factor_research の完全実装（DuckDB SQL を用いたファクター算出の完成）
- 監視・実行系コンポーネント間のメトリクス連携強化（より詳細なモニタリング項目）
- 単体テスト・CI 設定、型ヒントの厳密化、ドキュメント（README / API リファレンス）追加

---