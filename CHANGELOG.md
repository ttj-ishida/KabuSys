KEEP A CHANGELOG — KabuSys

この CHANGELOG は "Keep a Changelog" の形式に従い、意味的バージョニング (SemVer) を想定して作成しています。以下は、提示されたコードベース（バージョン 0.1.0 想定）から推測できる主要な変更点・追加機能です。

注意: 日付や一部の実装意図はソースコードから推測して記載しています。実際のリリースノート作成時には必要に応じて調整してください。

Unreleased
---------
- 進行中 / 未完成の実装メモ
  - research/factor_research.py の実装が途中（ファイル末尾で切れている）。モメンタム等ファクター計算の残り実装が必要。
  - 将来的な改善候補として、position_sizing の銘柄別 lot_size 対応や price フォールバックロジックの強化がコメントに記載されている。

[0.1.0] - 2026-04-18
--------------------

Added
- 全体
  - 初期リリース相当のコア機能を追加。
  - パッケージ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。Broker の生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動と停止フラグ処理を実装。
    - paper_trading 環境利用時は paper_trading 用専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する設計。
    - 実行中プロセス用 PID ファイル管理と停止フラグ（data/stop_requested.flag）によるグレースフルシャットダウンをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用することを明示。

- 設定管理 / CLI
  - config.py: 環境変数管理モジュールを追加。
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
    - 複数設定プロパティ（DB パス、API トークン、Paper Trading モード設定、監視閾値など）を提供する Settings クラスを追加。
    - PAPER_FILL_MODE 等の値検証（有効値チェック）を実装。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。既存 .env 読み込み、秘密項目マスク表示、保存機能を提供。
  - validate_config.py: 起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリチェック、config/*.yaml の存在と YAML パース（PyYAML があればパース検証）を実行。
    - --strict モードで警告も失敗扱いにできる。

- 監視 / レポート
  - monitoring_db の初期化呼び出しを各起動スクリプトで行い、監視テーブルの存在を保証（冪等）。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート作成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を算出し、PASS/FAIL 判定を出力。
    - デフォルト閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200 ms）を定義。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重 calc_score_weights を追加。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。
  - portfolio/position_sizing.py: 発注株数決定ロジック calc_position_sizes を追加（risk_based / equal / score の allocation_method に対応）。
  - portfolio/__init__.py: 上記機能をパッケージとしてエクスポート。

- ユーティリティ
  - utils/logging_setup.py: ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を用いたファイル出力（logs/<app>.log）を設定。
    - 既存ハンドラの二重設定防止、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX を吸収する実装、失敗時の安全なワーニング出力、set_cpu_affinity を提供。

Changed
- ロギング/起動順序
  - 起動スクリプト（monitoring / execution）は最初に set_process_priority("high") を呼び出し、以降の処理の優先度を高くするように変更（または初期設計として実装）。
  - setup_logging を各スクリプトで利用し、統一的なログ設定を行う流れに統一。
- DB 接続の扱い
  - monitoring は環境に関わらず本番 sqlite_path を使用する（設計上の明示）。
  - Execution は paper_trading 環境時に paper_sqlite_path を使用し DB を分離。

Fixed
- 環境変数/.env 取り扱いの堅牢化
  - config._parse_env_line: export プレフィックス対応、クォート文字列内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしのコメント判定などを実装し、.env の多様な表記に対応。
  - _load_env_file: override/protected オプションで OS 環境変数を保護して .env 上書きを制御する実装を追加。

- MONITOR_POLL_INTERVAL の安全なパース
  - run_monitoring._get_poll_interval において、環境変数の不正値（整数変換失敗や 0/負値）を検知してデフォルトにフォールバックする実装を追加（警告ログ出力）。

- position_sizing のスケーリング・丸め処理
  - aggregate cap 超過時のスケールダウンロジックを導入。比例スケールに加え lot_size 単位での端数処理と残余キャッシュを用いた追加配分ロジックを実装（再現性のための安定ソート順を考慮）。

- risk_adjustment の動作注記
  - apply_sector_cap: "unknown" セクターはセクター上限適用外にする挙動を明記（既存コメント）。
  - calc_regime_multiplier: 未知のレジームに対しては警告を出して 1.0 でフォールバック。

Security
- 機密情報取り扱い
  - config_setup のウィザードで秘密情報はマスク表示（標準出力上）、.env ファイル生成時に「.env は絶対に Git にコミットしないこと」と明記。

Documentation / Developer notes
- 各モジュールの docstring とコメントを充実させ、設計方針（PortfolioConstruction.md / StrategyModel.md 参照）や将来の拡張点（例: 銘柄別 lot_size、価格フォールバック）を記載。
- validate_config による事前チェック機能により、設定ミスで本番に被害が出るリスクを低減。

Acknowledgements / Known limitations
- research/factor_research.py の実装が途中で切れており、ファクター計算モジュールの残り実装が必要。
- position_sizing の price 欠損時におけるエクスポージャー不足による誤った許容処理や、銘柄別単元数対応は TODO として残っている。
- Windows / POSIX の優先度設定は権限や環境に依存し、失敗した場合は警告にフォールバックする設計（アクセス権限が必要）。

参考: バージョン管理方針
- 本 CHANGELOG は SemVer を想定しています。機能追加は MINOR、後方互換性のない変更は MAJOR、バグ修正は PATCH で運用してください。

もし特定の変更や日付を確定したい場合、実際のコミットログやリリース管理情報を提供いただければ、より正確で網羅的な CHANGELOG を生成します。