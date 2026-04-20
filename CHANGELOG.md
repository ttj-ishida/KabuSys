CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このファイルでは、リポジトリ内の現在のコードベース（初期リリース相当）から推測できる機能追加・改善点・注意点を日本語でまとめています。

フォーマット参考: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現在の提供物は初期リリースに相当します。以降の変更はここに記載します。）

0.1.0 - 2026-04-20
------------------

Added
- 基本機能の初回リリース。
  - 環境設定/読み込み
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env の行パーサを独自実装し、export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメント等に対応。
    - Settings クラスを提供し、各種環境変数（J-Quants, kabuステーション, DB パス, ログレベル, 実行環境フラグ等）を型変換して取得可能。
    - env 値の検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE のバリデーション）を実装。無効値は ValueError を送出。

  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - プロセス優先度を "high" に設定（set_process_priority）。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine のスレッド起動・停止ロジックを実装。
      - 停止フラグ（data/stop_requested.flag）と PID ファイルの扱いをサポート。
      - RiskManager のデフォルト構成（max_position_pct 等）を定義し、初期 available_cash を broker.get_available_cash() で取得。

    - run_monitoring.py
      - SystemMonitor のポーリングループ起動用スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告を出してデフォルトにフォールバック。
      - 監視は環境に依存せず本番 sqlite_path を使用する（監視データは一貫した DB に保存）。
      - 停止フラグ検知でループを安全に終了。例外はログに記録して次のポーリングまで待機。

  - ユーティリティ
    - ログ設定ユーティリティ（kabusys.utils.logging_setup）
      - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）を root ロガーに設定。
      - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
      - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
      - デフォルトログディレクトリ logs/、日次 30 世代保持。

    - プロセス優先度と CPU affinity（kabusys.utils.process_priority）
      - Windows / POSIX (Linux/Mac/FreeBSD) を吸収してプロセス優先度を設定。
      - set_cpu_affinity によりカレントプロセスを最初の N コアに固定可能（権限不足等は警告を出して無視）。

  - 検証・セットアップ CLI
    - config_setup.py
      - .env を対話式に作成/更新するウィザードを提供。シークレット入力や選択肢、既存値の再利用に対応。
      - 生成された .env をコミットしないよう注意文を出力。
    - validate_config.py
      - 起動前に .env と config/*.yaml の存在・基本整合性を検証する CLI。
      - 必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML があれば YAML のパース検証を実行。
      - --strict オプションで警告を FAIL 扱い（exit 1）にできる。

  - Paper Trading ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite から稼働率、注文成功率・送信率、レイテンシ（平均・最大・P95）などを集計してレポートを生成。
      - P95 の計算、日付フィルタ (--from / --to)、DB パス指定 (--db) に対応。
      - デフォルト閾値（稼働率 99.0%, 成立率 90.0% など）を使って PASS/FAIL 判定を行う。

  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py
      - シグナル選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分にフォールバック）を実装。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap（売却予定銘柄の除外や "unknown" セクター扱いの説明あり）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を提供。
    - portfolio/position_sizing.py
      - weight / candidates / リスクベースに基づくポジションサイズ計算ロジックを実装。
      - 単元株（lot_size）で丸め、per-position 上限・aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した安全なスケーリングと残余配分アルゴリズムを実装。
    - 各モジュールは DB を参照せずメモリ内計算のみで再現性を重視した純粋関数設計。

  - リサーチ（骨組み）
    - research/factor_research.py
      - DuckDB 接続を受け取り、Momentum/Value/Volatility/Liquidity 等のファクターを計算する設計の骨組みを用意（モメンタム算出関数の説明あり）。DuckDB の prices_daily / raw_financials テーブル参照を前提。

  - パッケージメタ
    - __version__ を "0.1.0" に設定。
    - パッケージの __all__ を設定（data, strategy, execution, monitoring）。

Changed
- （初回リリースのためなし）

Fixed
- .env パーサの堅牢化（引用符・エスケープ・インラインコメント処理）。これにより複雑な .env 値の読み込みが安定。

Security
- config_setup による .env 生成時に「.env を絶対に Git にコミットしないこと」を明示。
- validate_config で本番（KABUSYS_ENV=live）時の注意（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を警告として追加。

Notes / Breaking changes / Migration
- Settings クラスは環境変数の妥当性チェックを行うため、既存の環境変数で無効な値がある場合は起動時に ValueError を投げます（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。運用環境ではこれらを見直してください。
- run_monitoring は「監視データ保存先に常に本番 sqlite_path を使用する」挙動です。監視データを別 DB に分離したい場合は設定やコードを調整してください。
- run_execution は paper_trading 用に DB を分離しているため、ペーパートレードと本番のデータが混在しません。既存の運用スクリプトから移行する際は PAPER_TRADING_SQLITE_PATH の設定に注意してください。
- process_priority / cpu_affinity は権限や OS に依存する操作です。権限不足時は警告を出してスキップします。

Acknowledgements
- 本 CHANGELOG はリポジトリ内のソースコードから実装意図を推測して作成しています。実際のリリースノートや運用ドキュメントは意図に合わせて追記・修正してください。