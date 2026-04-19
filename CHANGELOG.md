CHANGELOG
=========

すべての重要変更は Keep a Changelog の形式に従って記載しています。
（初回リリースの想定に基づき、コードベースから推測して作成した変更履歴です）

[Unreleased]
------------

- なし

0.1.0 - 2026-04-19
-----------------

Added
- プロジェクト初回リリース相当の実装を追加。
  - 核となる実行スクリプト
    - run_execution.py
      - ExecutionEngine を起動する CLI。
      - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト: data/paper_trading.db）と完全に分離して動作。
      - 停止制御用フラグファイル (data/stop_requested.flag) と PID ファイル (data/execution.pid) を利用して安全に停止可能。
      - 起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はログ警告後にデフォルト値へフォールバック。
      - 監視 DB は環境に関係なく本番 sqlite_path（デフォルト: data/monitoring.db）を使用。
      - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
      - 起動時にプロセス優先度を "high" に設定。

  - 設定 / ユーティリティ
    - config.py
      - 環境変数の読み込みとラッパー Settings を提供。
      - プロジェクトルートの自動探索（.git または pyproject.toml）に基づく .env 自動読み込み（.env, .env.local、OS 環境を保護）。
      - .env の詳細なパース実装（export プレフィックス、クォート内エスケープ、行内コメント処理等）。
      - 各種設定プロパティ（DB パス、PID/kill flag パス、閾値など）と簡潔なバリデーション（PAPER_FILL_MODE の有効値検査、KABUSYS_ENV/LOG_LEVEL の許容値チェックなど）。
    - config_setup.py
      - 対話式 .env 作成・更新ウィザードを提供（シークレット項目は表示をマスク、選択肢・デフォルト対応）。
      - .env ファイルの読み書きロジックを実装。
    - validate_config.py
      - 環境変数および config/*.yaml の事前検証ツール。
      - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース確認（PyYAML 未インストール時は警告）など。
      - --strict オプションで警告を FAIL 扱いにできる。

  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
      - スコア全ゼロ時は等金額配分にフォールバック（警告ログ）。
    - portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を実装（当日売却予定の銘柄は除外可能、"unknown" セクターは制限対象外）。
      - 市場レジームに応じた乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。
    - portfolio/position_sizing.py
      - ポジションサイズ算出ロジック（risk_based / equal / score）を実装。
      - 単元株（lot_size）丸め、1銘柄上限・アグリゲート上限、コストバッファ（手数料・スリッページ想定）を考慮したスケーリングと端数処理を実装。

  - 分析・検証ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポートを生成する CLI。
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
      - 基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
      - --from/--to/--db オプションをサポート。

  - ユーティリティ
    - utils/logging_setup.py
      - 全アプリケーションで共通利用できるロギングセットアップ関数 setup_logging を実装。
      - stdout に出す StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーへ設定。既存ハンドラの重複登録防止のためクリア処理あり。
      - ログディレクトリ作成失敗時はファイル出力を無効化して標準出力のみで継続。
    - utils/process_priority.py
      - クロスプラットフォームでプロセス優先度設定と CPU affinity 設定を提供（Windows / POSIX を吸収）。
      - set_process_priority(level: "high"|"normal"|"low")、set_cpu_affinity(cpu_count) を実装。権限不足時は警告ログでスキップ。

  - データ処理 / リサーチ（着手中）
    - research/factor_research.py
      - ファクター算出モジュールの骨組みを追加（モメンタム・ボラティリティ・バリュー等の定義と定数）。
      - DuckDB を利用して prices_daily, raw_financials を参照する方針を明記（実装の一部は継続中）。

  - パッケージメタデータ
    - __init__.py にてバージョン __version__="0.1.0" を設定。

Changed
- n/a（初回リリースのため既存からの変更点はなし）

Fixed
- n/a（初回リリースのため修正履歴はなし）

Security
- 環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env を通じて設定する想定。config_setup では .env を生成する注意書きを記載（.env を絶対に Git にコミットしないことを推奨）。

Notes / Migration
- 起動前に .env を準備してください。対話式ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config（--strict で警告も失敗扱い）
- 実行スクリプト:
  - 監視ループ: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（1 以上の正整数、無効値はデフォルト 60 秒にフォールバック）。
    - 監視は常に sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 実行エンジン: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録（デフォルト data/paper_trading.db）。
- ログ:
  - デフォルトは logs/<app_name>.log（ログローテート 30 日分）。
  - LOG_LEVEL 環境変数、もしくは setup_logging の level 引数で制御可能。
- Paper trading 固有:
  - PAPER_FILL_MODE = instant | partial | never | reject（無効な値は例外）
  - PAPER_TRADING_SQLITE_PATH で paper DB パスをオーバーライド可能。

既知の制限 / TODO
- research/factor_research.py の詳細実装（calc_momentum 等）が継続中（スニペット終端が途中）。
- position_sizing の価格欠損時のフォールバック（前日終値や原価）や銘柄別単元対応などは将来の改善候補としてコメントあり。
- 一部の機能は外部パッケージ（psutil, duckdb, PyYAML 等）が必要。PyYAML 未インストール時は YAML 検証をスキップして警告を出す設計。

お問い合わせ
- バグや不整合を見つけた場合は issue を作成してください。