CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（日本語で記載）

Unreleased
----------
（現時点の未リリース変更はありません。）

0.1.0 - 2026-04-18
------------------

Added
- 基本リリース: KabuSys 初版を追加。パッケージバージョンを __version__ = "0.1.0" に設定（src/kabusys/__init__.py）。
- 実行用スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理に対応。
  - 監視（SystemMonitor）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、値検証あり）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する方針で起動。
    - stop フラグ検知・例外ハンドリング・クリーンな DB クローズ処理を実装。
- 設定管理
  - Settings クラスを追加し、環境変数から型付き設定値を取得（src/kabusys/config.py）。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等の Path 化。
    - env（KABUSYS_ENV）・log_level の検証（有効値チェック）。
    - PAPER_FILL_MODE の妥当性チェック。
    - 各種しきい値設定（cpu/memory/disk）や PID/KILL フラグ周りの設定を提供。
  - .env の自動読み込み機能を追加（プロジェクトルート検出、.env → .env.local の順で読み込む）。既存 OS 環境変数を保護する挙動を実装。
  - .env 行のパーサを robust に実装（export で始まる行、シングル/ダブルクォート、エスケープ、コメント処理に対応）。
- 設定ツール / 検証ツール
  - 対話式環境設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の生成・更新を対話式に実行、シークレット項目はマスク表示。
  - 起動前チェック CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の有無、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース検証（PyYAML がある場合）を行う。
    - --strict オプションで警告を失敗扱いにできる。
- ログ・プロセス管理ユーティリティ
  - ロギングセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / 引数での上書きに対応。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS 等）差分を吸収して優先度設定を行う（権限不足等は警告でスキップ）。
    - CPU affinity を最初の N コアに固定する機能を提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合のフォールバックを実装。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有のセクター比率が上限を超える場合、新規候補を除外）を実装。
    - calc_regime_multiplier（bull/neutral/bear に対する投下資金乗数）を実装。未知のレジームは警告の上フォールバック。
  - 位置サイズ計算（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装。allocation_method に応じた株数算出（risk_based / equal / score）と単元株丸め、per-position/max aggregate cap、コストバッファを考慮したスケーリング配分ロジックを実装。
  - 上記を透過的にエクスポートするパッケージインターフェースを提供（src/kabusys/portfolio/__init__.py）。
- 解析・研究ユーティリティ（部分実装）
  - ファクター計算の枠組みを追加（src/kabusys/research/factor_research.py）。DuckDB 接続で prices_daily / raw_financials を参照してモメンタム等を計算する設計（calc_momentum 関数の導入、定数群定義）。※ファイルの一部は続きあり。
- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 latency 200 ms）を定義し PASS/FAIL 判定を実装。
    - DB パスはコマンド引数または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

Changed
- ロギング
  - StreamHandler の標準出力先を stdout に明示。cron/Task Scheduler などでのリダイレクト運用を考慮して stderr ではなく stdout を使用（src/kabusys/utils/logging_setup.py）。
- .env 自動ロードの優先度
  - OS 環境変数を保護しつつ、.env（未設定のみ）→ .env.local（上書き可）を読み込む実装に。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（src/kabusys/config.py）。
- 監視（monitoring）
  - 監視用 DB 初期化呼び出しを冪等に行い、実行側でも監視テーブルの存在を保証するようにした（run_execution でも init_monitoring_db を呼ぶ）。

Fixed
- .env 行パーサの堅牢化
  - export プレフィックス、シングル/ダブルクォート内部のバックスラッシュエスケープ、インラインコメント処理などを正しく扱うよう改善（src/kabusys/config.py）。
- DB 初期化の安全化
  - 起動時に monitoring テーブルの初期化を必ず実行しておくことで、該当テーブルが無い場合の起動時エラーを回避（src/kabusys/monitoring/monitoring_db の init_monitoring_db 呼び出しを各起動スクリプトで保証）。

Security
- Settings._require により必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定の場合は起動前に明示的なエラーにより検出される（src/kabusys/config.py）。
- config_setup にて生成される .env は Git にコミットしない旨を明記（src/kabusys/config_setup.py）。

Notes / Internal
- 実行・監視プロセス開始時にプロセス優先度を "high" に設定する呼び出しを各スクリプトの最初に行う実装になっている（run_execution.py / run_monitoring.py）。
- 一部モジュール（research/factor_research.py 等）は継続実装が想定される（ファクター計算ロジックの補完等）。

将来の作業候補（未実装の改善点等）
- position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する設計への拡張（TODO コメントあり）。
- price フォールバック: price_map に欠損（0.0）がある場合のフォールバックロジック（前日終値や取得原価）検討。
- research モジュールの完全実装（calc_momentum の続きなど）。
- monitor / execution の単体テストの整備と E2E テスト。

----- 
変更点に関する不明点や、特定機能（例: position sizing のパラメタ調整、Paper Trading の閾値変更等）について詳細が必要であれば指示してください。