Keep a Changelog
=================

このファイルは Keep a Changelog 規約に準拠して作成しています。  
公開日や変更内容はコードベースから推測して記載しています。

※注意: 以下はソースコードから推測した変更点・機能説明です。実際の変更履歴と差異がある可能性があります。

Unreleased
---------

（現在なし）

[0.1.0] - 2026-04-25
-------------------

Added
- 初回リリース (バージョン 0.1.0)
  - パッケージの基本構成を追加: kabusys モジュール、サブパッケージ（portfolio, execution, monitoring, tools, utils, research 等）を含む。
  - __version__ を "0.1.0" に設定。

- 起動スクリプト / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を監視して安全にループを終了。
    - 監視テーブルの初期化（init_monitoring_db）と DuckDB 接続を行う。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を利用して本番 DB と分離。Paper 環境では MockBrokerClient を使用する想定（BrokerClientFactory 経由）。
    - エンジンはスレッドで実行され、停止フラグや PID ファイル (data/execution.pid) を扱う。
    - 起動時にプロセス優先度を High に設定する。

- 設定関連
  - config.py
    - Settings クラスを提供。環境変数からアプリケーション設定を取得する。
    - .env 自動読み込み機能を実装（.env / .env.local、OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは quotes, export プレフィックス、インラインコメントの扱い等を考慮した実装。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や各種しきい値（CPU/MEM/DISK）などをプロパティで提供。
    - env（development / paper_trading / live）やログレベルのバリデーションを行う。
  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを追加。秘密値はマスク表示。
    - デフォルトテンプレートを .env に書き出す機能を提供。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェックを実施。
    - PyYAML 未インストール時は YAML の内容検証をスキップし警告。
    - --strict オプションで警告をエラー扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - setup_logging を追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - LOG_DIR 作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決順を明確化 (引数 > 環境変数 > デフォルト)。
  - utils/process_priority.py
    - set_process_priority(level) を追加。Windows と POSIX (Linux/Mac/FreeBSD) を吸収する実装。権限不足や未対応 OS は警告でフォールバック。
    - set_cpu_affinity(cpu_count) を追加。最初の N コアに固定するユーティリティ。権限不足等は警告でスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順にソートして上位 N を返す。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限をチェックし、超過セクターの候補を除外する。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知レジームは警告の上で 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based"/"equal"/"score") に応じて発注株数を計算。
    - 単元株（lot_size）で丸め、per-stock 上限・aggregate cap を実装。予算超過時はスケールダウンし、残余を fractional 残差に基づいて再配分するアルゴリズムを搭載。
    - cost_buffer により手数料・スリッページ分を保守的に見積もる処理を追加。
    - 将来の拡張（銘柄別 lot_size）用の TODO コメントあり。

- リサーチ（ファクター）
  - research/factor_research.py
    - Momentum/Value/Volatility/Liquidity を想定したファクター計算モジュールの骨組みを追加。
    - calc_momentum の実装を開始（関数シグネチャ、定数、設計方針を含む）が、ソースは途中で切れており部分実装の状態。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード検証レポート生成スクリプトを追加。
    - DB から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定を行う。
    - コマンドライン引数 --from / --to / --db をサポート。PAPER_TRADING_SQLITE_PATH 環境変数に対応。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。

Changed
- (初回リリースのため変更履歴なし)

Fixed
- (初回リリースのため修正履歴なし)

Known issues / Notes
- research/factor_research.calc_momentum はソース途中で切れており、モメンタム計算の完全実装は未完。
- position_sizing:
  - lot_size は現在グローバル固定（デフォルト 100）。銘柄別 lot_size 対応は将来的な拡張予定。
  - open_prices に欠損 (0.0) があるとエクスポージャーが過少見積りされる可能性があり、その対策（前日終値などのフォールバック）は TODO。
- config の .env 自動ロードはプロジェクトルート検出に依存（.git や pyproject.toml）。配布後や特殊な配置では自動ロードがスキップされる可能性あり。
- process_priority / set_cpu_affinity は権限や環境に依存するため、AccessDenied 等で失敗した場合は警告を出して安全に継続する。
- validate_config は PyYAML 非依存設計。PyYAML がない場合は YAML 内容検証はスキップされる（警告）。
- logging_setup はログディレクトリ作成失敗時にファイル出力を無効化して stdout のみで継続する。

References
- リポジトリ内の各 CLI スクリプトはモジュールとして直接実行可能（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report, python -m kabusys.run_execution, python -m kabusys.run_monitoring）。

-------------------------------------------------------------------------------

（以上）