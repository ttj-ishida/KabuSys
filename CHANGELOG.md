CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、日本語でまとめています。
セマンティックバージョニングに準拠します。

0.1.0 — 2026-04-24
------------------

Added
- 初回リリースを追加（バージョン: 0.1.0）。
- 起動スクリプト:
  - run_execution.py
    - ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV によって paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用可能。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全にエンジンを停止するロジックを実装。PID ファイル（data/execution.pid）を書き出す仕組みをサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視 DB は本番 DB を参照）。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。
- 設定管理:
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート（.git / pyproject.toml）を基準に探索）。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数を保護する protected 機構）。
    - 複数プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE など）を Settings クラスで提供。KABUSYS_ENV / LOG_LEVEL 等の検証を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - config_setup.py
    - .env の対話式ウィザードを実装。既存 .env の読み込み、入力プロンプト、シークレットマスク、最終確認後の .env 保存をサポート。
- 設定検証 CLI:
  - validate_config.py
    - .env と config/*.yaml の事前検証を行う CLI を提供。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ファイルパスの親ディレクトリチェック、PyYAML がない場合のスキップ扱い、KABUSYS_ENV=live 時の追加ガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築モジュール（pure function 群、DB 参照なし）:
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。スコア合計が 0 の場合は警告を出して等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中上限の適用（apply_sector_cap）。既存保有・売却予定を考慮してセクター別エクスポージャーを算出し、上限超過セクターの候補を除外。
    - レジームに基づく投下資金乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" のマッピングを実装。未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - ポジションサイズ算定（risk_based / equal / score）。最大ポジション比率、lot_size（単元）での丸め、コストバッファの考慮、aggregate cap（利用可能現金を超えた場合のスケーリング）を実装。
    - スケーリング後の残差処理で lot_size 単位で再配分する仕組みを追加。
- ユーティリティ:
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテートの TimedRotatingFileHandler をルートロガーへ設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェールセーフを実装。
    - LOG_LEVEL / LOG_DIR / 引数 level / log_dir による優先順位を実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。CPU affinity 設定関数も提供。
    - アクセス権限不足などで設定できない場合は警告を出してスキップ。
- tools:
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 構成指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを計算。
    - デフォルト DB パスは data/paper_trading.db。--db オプションもサポート。
    - P95 の独自計算、期間フィルタ、しきい値（稼働率 >=99%、注文成功率 >=90% 等）による PASS/FAIL 判定を実装。
- research:
  - research/factor_research.py
    - 定量ファクター（Momentum / Value / Volatility / Liquidity）を DuckDB を使って計算するためのモジュール基盤を追加（prices_daily / raw_financials を前提）。複数の時間窓・定数を定義。
    - （ファイル末尾で実装途中の箇所あり。機能の骨格と設計方針を導入。）
- パッケージ情報:
  - __init__.py に初期バージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため過去からの変更はありません）

Fixed
- （初回リリースのため過去からの修正はありません）

Notes / 備考
- run_monitoring は監視用 DB として Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用する設計です。監視が本番 DB を参照する意図になっているため、環境ごとに分離したい場合は設定を調整してください。
- .env 読み込みルールは OS 環境変数を優先し、.env.local で上書きできます。自動ロードが不都合な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading モードでは実運用 DB と分離されるよう paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。ペーパートレードと本番の混在を避ける設計です。
- ログ周りは初回リリースで堅牢性を重視し、ログディレクトリ作成失敗でもプロセスが継続するようにしています。ログの保存先やローテーション設定は logging_setup.setup_logging の引数／環境変数で調整可能です。

Acknowledgements
- このリリースは自動売買システムのコアユーティリティ群（設定管理、起動スクリプト、ポートフォリオ構築、検証ツール、研究用ファクター計算基盤）を提供します。今後のリリースで ExecutionEngine 本体、SystemMonitor の詳細実装、研究アルゴリズムの完全実装・最適化などを追加予定です。