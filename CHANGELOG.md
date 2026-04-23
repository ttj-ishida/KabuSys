CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記録します。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-23
-------------------

Added
- 基本アプリケーション骨格を初期リリースとして追加。
  - パッケージバージョン: __version__ = "0.1.0"
- 実行用スクリプト / デーモン機能
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。paper/live に応じた振る舞いを想定。
    - エンジンは別スレッドで実行され、 data/stop_requested.flag による安全な停止をサポート。起動時に既に停止フラグが立っている場合は起動を中止。
    - execution.pid への PID 書き込み（pid_file 経由）をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動（監視テーブル初期化を含む）。
    - stop フラグファイル検知による安全停止、例外ハンドリングによるループ継続。

- 設定・環境変数管理
  - config.py: Settings クラスを追加。環境変数経由で設定を取得。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）や API トークン系を管理。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
    - プロジェクトルート自動検出(_find_project_root) と .env / .env.local の自動読み込みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - pid/kill flag 関連設定や各種しきい値（CPU/MEM/DISK）を環境変数から取得。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 主要設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 通知、LOG_LEVEL、Kill Switch 設定など）を対話的に作成・更新。
    - .env ファイルに安全なヘッダを付けて書き出す機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があればパースも実行）。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全銘柄スコアが0の場合は等配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるフィルタ（既存ポジションの時価総額比で上限を判定）。"unknown" セクターは上限適用外に。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供。未知のレジームは警告とともに 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。
      - 単元（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer（手数料・スリッページ見積り）反映、残余を用いた端数配分アルゴリズムを実装。
      - price 欠損時のスキップやログ出力を考慮。

- 研究・ファクター計算
  - research/factor_research.py（骨組み）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いて Momentum / Value / Volatility / Liquidity 系ファクターを計算する設計を追加。
    - モメンタム計算（calc_momentum）等の実装方針と定数（窓長など）を定義。
    - （注）ファイル末尾が途中で切れているため、実装は部分的または継続中の状態を想定。

- ユーティリティ
  - utils/logging_setup.py
    - setup_logging ユーティリティを追加。ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。ログディレクトリの生成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順や既存ハンドラの安全なクローズ処理を実装。
  - utils/process_priority.py
    - set_process_priority, set_cpu_affinity を実装。Windows と POSIX（Linux/Mac/FreeBSD）差分を吸収。権限がない場合は警告を出してスキップ。
    - Windows 用優先度定数のフォールバックや nice 値マップを提供。
  - __init__ のパッケージエクスポート整理（portfolio などの主要関数を re-export）。

- 監視・モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を起動時に idempotent に呼ぶ実装（monitoring/run と execution/run 両方で呼び出し、テーブルが存在することを保証）。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py を追加。
    - paper_trading 用 SQLite（デフォルト: data/paper_trading.db）から期間別の各種指標を集計し、検証レポートを標準出力に表示。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなど。閾値に基づく PASS/FAIL 判定を実装。
    - P95 計算、日付フィルタ対応、DB 存在チェック、テーブル欠損時のフォールバックが実装済み。

Changed
- .env 読み込みロジック
  - export KEY=val、シングル/ダブルクォートおよびバックスラッシュエスケープ、インラインコメントの扱いなどを詳細に実装し、より堅牢な .env パーシングに更新。
  - .env.local を上書きモードで読み込み、OS 環境変数は protected として上書きされないように設計。

Fixed
- 実行時の堅牢性向上
  - run_monitoring のポーリング間隔不正値（0 以下や非数）に対してデフォルトフォールバック＆警告を追加し、time.sleep による ValueError を回避。
  - ログハンドラの二重追加を防止するため、setup_logging にて既存ハンドラを安全に閉じてクリアする処理を導入。
  - process_priority や cpu_affinity の実行環境での権限不足や未実装 API に対して警告を出して安全にスキップするよう改善。

Security
- 機密情報取扱い
  - config_setup と .env の扱いに関する注意書きを出力（.env を Git 管理下に置かないことを明記）。
  - CLI でシークレット項目はマスク表示を行う。

Notes / Known issues
- research/factor_research.py の実装は途中で切れている箇所が見られる（ファイル末尾が不完全）。本モジュールは今後の実装完了が必要。
- 一部の機能（BrokerClientFactory や ExecutionEngine、SystemMonitor 等）はこの差分により参照されるが、実装詳細はこのスナップショットに含まれていない可能性がある（外部モジュール依存）。
- Windows/POSIX の優先度設定・CPU affinity は OS 権限や環境に依存するため、実行環境での検証を推奨。

Authors
- 本 CHANGELOG は提供されたソースコードから推測して作成しました。実際の変更履歴・コミットログを基にした追記・修正を推奨します。