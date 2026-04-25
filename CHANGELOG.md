# Keep a Changelog に準拠した変更履歴（推定）
この CHANGELOG は提示されたコードベースの内容から推測して作成したものです。実際のコミット履歴ではなく、コードに記載された機能・挙動・注記をベースにしたリリースノートです。

フォーマット: https://keepachangelog.com/（日本語）

全般メモ:
- 本プロジェクトは日本株自動売買システム「KabuSys」を想定しています。
- DB：監視用 SQLite（monitoring.db）と分析用 DuckDB（kabusys.duckdb）を併用。
- 環境に応じて Paper Trading（ペーパートレード）用の SQLite を分離して運用可能。
- .env の自動読み込み、設定ウィザード、設定検証ツール、モニタリング・実行エンジン起動スクリプト、ポートフォリオ構築ライブラリ、ユーティリティ群、Paper Trading 向け検証レポートなどを含む。

## [Unreleased]
- （現時点では未リリース／今後の変更予定をここに記載）

## [0.1.0] - 2026-04-25
初回公開（推定）。コードベースに実装されている主要機能と改善点をまとめます。

Added
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するメインスクリプト。環境に応じて Paper Trading 用の MockBrokerClient を使用し、Paper 環境では専用 SQLite（data/paper_trading.db）を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）や PID ファイル連携に対応。
- 設定管理・ユーティリティ
  - config.py: アプリケーション設定クラス（Settings）を提供。環境変数／.env 読み込みの自動ロード機能、各種設定プロパティ（DB パス、API トークン、Paper Trading の挙動等）を実装。
    - .env の自動読み込み順序: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など Paper Trading 固有設定に対応。
  - config_setup.py: 対話式 .env 作成／更新ウィザード。秘密項目のマスク表示や選択肢サポートを提供。
  - validate_config.py: 起動前チェック CLI。必須環境変数や KABUSYS_ENV、DB パス、config/*.yaml の存在や YAML のパース（PyYAML があれば実行）を検証。--strict オプションで警告をエラー扱いに可能。
- ロギング・プロセス制御
  - utils/logging_setup.py: 共通ロギング設定。コンソール出力（stdout）と日次ローテーションファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーへ設定。LOG_DIR/LOG_LEVEL に従う。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（high/normal/low）を OS に依存せず設定するユーティリティ。Windows・POSIX(nice) を吸収。CPU affinity を最初 N コアに固定する関数も提供。権限不足など失敗時は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選定（タイブレークに signal_rank を利用）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用して候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づき株数を計算。損切り・リスク・単元（lot_size）丸め、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した厳格な資金配分ロジックを実装。
- データ解析 / ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプト。system_status, trade_logs, risk_logs から稼働率・注文成功率・送信率・レイテンシ（P95）等を集計。閾値（稼働率 99%、注文成功率 90% など）に基づき PASS/FAIL を判定。--from/--to/--db オプションをサポート。
- research/factor_research.py（部分実装）
  - DuckDB 接続を受けて Momentum などのファクター計算を行う設計（prices_daily / raw_financials を参照）。（ファイルは途中までの実装）

Changed
- データベース扱い
  - 監視（monitoring）用途の DB 初期化は冪等に実行され、環境（development/paper_trading/live）にかかわらず監視は本番 sqlite_path を参照する設計。これにより監視データは本番 DB に集約される。
  - Execution エンジンは settings.is_paper 判定により Paper Trading 用 DB に接続し、本番 DB と分離して動作可能。
- ログ出力
  - ロガー初期化時に既存ハンドラは flush/close の上で除去し、二重ハンドラ設定を防止。
  - stdout を StreamHandler に使用（cron などで stdout/stderr を一本化しやすくするため）。
- .env パーサーの堅牢化
  - config._parse_env_line はシングル/ダブルクォート内のバックスラッシュエスケープに対応し、インラインコメント処理や export KEY=val 形式の対応を含む。
  - .env 読み込み時に既存の OS 環境変数は保護される（protected set）。.env.local は .env を上書き（override=True）する動作。
- 起動挙動の安全化
  - stop_requested.flag（data/stop_requested.flag）に基づく安全停止機構を採用。起動前にフラグが立っていると ExecutionEngine を起動しない。
  - run_monitoring と run_execution の起動時にプロセス優先度を最初に "high" に設定する仕組みを導入。

Fixed
- 例外耐性の向上
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を吐いても次のポーリングへ復帰するよう logger.exception で捕捉。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップし、警告を出すようにした（ImportError の扱い）。
  - logging_setup: ログディレクトリ作成失敗時に例外で停止せず、コンソールのみで継続するように保護。

Security
- シークレット情報の扱い
  - config_setup のウィザードは J-Quants トークンや kabu API パスワードを "secret" としてマスク表示。README 等へのコミット禁止を明記（.env を絶対に Git にコミットしない警告を出力）。

Notes / Known limitations / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされブロックが外れる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を検討する旨の TODO が存在。
- position_sizing:
  - 単元株（lot_size）は現状は全銘柄共通 100 を想定。将来的には銘柄ごとの lot_size を持つ拡張を検討する旨の TODO が記載されている。
- research/factor_research.py:
  - ファイルは途中までの実装（コメントに設計方針あり）。完全なファクター計算は未完。
- 不可視の実装依存
  - ExecutionEngine、OrderManager、BrokerClientFactory、SystemMonitor 等の内部挙動（API 呼び出し、発注処理、監視項目など）は本スナップショット外のモジュールに依存しており、本 CHANGELOG はそれらを仮定的に扱っている。

開発者向け補足
- バージョン情報はパッケージルート src/kabusys/__init__.py の __version__ = "0.1.0" により管理。
- 自動ロードされる .env の挙動や KILL_FLAG_CLEAR_ON_START 等は本番運用において注意が必要（validate_config で live 時のガードを確認すること）。
- Paper Trading と live の DB 分離・MockBroker の存在により、ローカル検証と本番運用を分離できる設計。

（以上）