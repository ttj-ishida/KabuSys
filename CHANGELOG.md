Keep a Changelog 準拠 — 変更履歴 (日本語)
=====================================

フォーマット: https://keepachangelog.com/ja/1.0.0/
このファイルは、リポジトリの現在のスナップショットからコードを読み取り推測して作成した CHANGELOG です。

0.1.0 — 2026-04-18
------------------

Added
- 初期リリース。以下の主要機能・モジュールを追加。
  - 実行エントリ / 管理ツール
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB と MockBroker を利用する、停止フラグ/PID 管理、スレッドベースの実行制御を実装。
    - run_monitoring.py: SystemMonitor を定期ポーリングする監視プロセス起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ検知で安全終了。
  - 設定関連
    - config.py: 環境変数および .env 自動ロード機能（.env, .env.local をプロジェクトルートから読み込み）。必須値チェック用ヘルパーと Settings クラス（各種パス・閾値・フラグ・環境判定プロパティを提供）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - config_setup.py: 対話式 .env 作成/更新ウィザード。シークレット表示のマスク、既存値再利用、ファイル書き込みフォーマットを含む。
    - validate_config.py: .env および config/*.yaml の事前検証 CLI。必須環境変数チェック、パス/ディレクトリ検査、YAML パース検証（PyYAML が存在する場合）、本番環境向けガードを実装。--strict モードをサポート。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio.portfolio_builder: シグナル選定 (select_candidates)、等金額ウェイト (calc_equal_weights)、スコア加重ウェイト (calc_score_weights)。
    - portfolio.risk_adjustment: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた乗数計算 (calc_regime_multiplier)。
    - portfolio.position_sizing: 各銘柄の発注株数計算 (calc_position_sizes)。risk_based / equal / score の配分方式、lot_size 単位丸め、集計キャップとスケーリング、cost_buffer による保守的見積を実装。
    - portfolio.__init__: 主要関数のエクスポート。
  - ユーティリティ
    - utils.logging_setup: ルートロガーの統一設定。stdout ストリームハンドラと日次ローテーションの TimedRotatingFileHandler を設定、ログディレクトリ自動作成とフォールバック（作成失敗時はコンソールのみ）を実装。
    - utils.process_priority: Windows / POSIX を吸収するプロセス優先度設定（high/normal/low）と CPU affinity 設定関数を提供。psutil ベースでアクセス権限エラー等を安全にハンドリング。
  - モニタリング / 実行周りの DB 初期化
    - monitoring.monitoring_db.init_monitoring_db を呼ぶことで監視用テーブルの冪等な確保を実行。
  - ツール
    - tools.paper_verification_report: Paper Trading 用 SQLite DB から検証レポートを生成する CLI。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定するしきい値を定義。
  - パッケージ API
    - __init__.py: バージョン番号 __version__="0.1.0" を設定。

Changed
- （初版のため該当なし）

Fixed
- 設定パース/読み込みの堅牢化
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、無効行スキップなどを実装し .env パースを堅牢化。
  - config._load_env_file: override/protected 引数により OS 環境変数を保護しつつ .env.local を適切に上書き可能に。
- 監視ループの堅牢化
  - run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL の値を検証し、0 以下や整数変換失敗時にログ警告を出してデフォルト（60 秒）にフォールバック。time.sleep に渡す不正値を排除。
  - run_monitoring: 監視ループ内で check_once() の例外を捕捉してログ出力しループ継続することで、1 回の例外で監視を停止しない設計に。
- 実行エンジンの安全性向上
  - run_execution: KABUSYS_ENV=paper_trading の場合に paper_trading 専用 SQLite を使用し、本番 DB と完全分離。起動前に停止フラグを確認して即時終了する安全チェックを追加。ExecutionEngine の PID ファイル管理および停止フラグ検知時の graceful stop を実装。
  - run_execution: init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
- ロギングの堅牢化
  - utils.logging_setup: ログディレクトリ作成に失敗した場合はファイルハンドラ生成をスキップしてコンソール出力のみで継続。また既存ハンドラを安全に flush/close してから再設定することで多重登録を防止。
- クロスプラットフォームのプロセス優先度設定
  - utils.process_priority: Windows と POSIX(nice) の差分を吸収。権限不足や未実装プラットフォームに対しては警告を出してスキップする設計。

Security
- config_setup.py/.env の取り扱いに関する注意喚起を出力（.env を決して Git にコミットしない旨のヘッダを生成）。
- config.Settings は必須環境変数未設定時に ValueError を投げ、起動時に設定ミスを露呈させることで誤った本番起動を抑止。

Notes / Implementation details
- Paper Trading
  - paper_trading モードでは MockBrokerClient を利用する設計（BrokerClientFactory.create により選択）。paper_trading 用 DB はデフォルト data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
  - paper_verification_report は P95 計算、稼働率・成功率の判定ロジックを組み込み、しきい値はソース内定数で定義（稼働率 >= 99%、成立率 >= 90% 等）。
- Portfolio logic
  - select_candidates はスコア降順、同点は signal_rank の低い方優先でタイブレーク。
  - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
  - apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いにしてセクター上限の適用除外とする（未知セクターはブロック対象外）。
  - calc_position_sizes は lot_size 単位で丸め、aggregate cap を超えた場合は比例スケーリング＋残差配分で lot 単位の微調整を行う。cost_buffer による保守的コスト見積りをサポート。
- ロギング挙動
  - stdout を StreamHandler に使用（stderr ではない）。これは cron 等でリダイレクトしやすくするための意図的な選択。
- 設定自動ロード
  - 起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env/.env.local を読み込む。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Known issues / TODO
- research/factor_research.py の一部（calc_momentum の実装途中？）でファイルが切れており、関数実装の続きを含める必要がある（現状 "start_da" で途切れ）。ファクター計算モジュールは DuckDB 操作を伴うため、残り実装の追加とテストが必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合のフォールバック価格（前日終値や取得原価）の利用は TODO コメントあり。価格欠損によりエクスポージャーや発注量が過小評価されるケースが想定されるため改良検討中。
- BrokerClientFactory / ExecutionEngine 等の外部依存（ブローカークライアント実装、Engine の内部実装、monitoring.system_monitor 等）は本 CHANGELOG の対象外。これらの振る舞いは実運用での検証が必要。

開発者向けメモ
- 起動スクリプトは全て setup_logging(...), set_process_priority("high") を最初に呼ぶ設計。プロセス優先度やログ設定によりデバッグがしやすくなっている一方、権限不足での警告を確認すること。
- 本番運用時は KABUSYS_ENV=live を設定すると validate_config にて注意喚起が出る（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認など）。
- .env の自動ロード機能はテスト時に不要な影響を与える可能性があるため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化可能。

ライセンス・その他
- この CHANGELOG はソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートはソース管理のコミットログを基に作成することを推奨します。