Keep a Changelog 準拠 CHANGELOG.md
=================================

すべての注記はコードベースから推測して作成しています。実装の意図や仕様に基づく要約であり、厳密な差分履歴ではありません。

フォーマット
-----------
- 変更は https://keepachangelog.com/ja/ に準拠しています。
- バージョンはパッケージ内の __version__（現行: 0.1.0）に合わせています。

[Unreleased]
------------
（無し）

[0.1.0] - 2026-04-25
-------------------

Added
-----
- 初期リリース: KabuSys 自動売買フレームワークの基本モジュール群を追加。
  - エントリポイント / 起動スクリプト
    - run_execution.py
      - ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、ブローカークライアント生成、ExecutionEngine のスレッド起動・停止処理を実装。
      - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用する分離設計を採用。
      - 停止制御に data/stop_requested.flag および PID ファイル（data/execution.pid）を使用。
    - run_monitoring.py
      - SystemMonitor ポーリングループ開始スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
  - 設定管理
    - config.py
      - 環境変数読み込み・ラッパ（Settings クラス）を追加。.env/.env.local の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
      - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 複数の設定プロパティを提供（J-Quants、kabuAPI、LINE、データベース、監視閾値、環境判定フラグ等）。
      - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START など paper/live 環境向け設定を追加。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加。既存値再利用、シークレットマスク、選択肢サポートなどを提供。
    - validate_config.py
      - .env と config/*.yaml の起動前検証 CLI を追加。必須 env のチェック、KABUSYS_ENV／LOG_LEVEL の妥当性、DB パスや YAML の存在/パース検証、live 環境向けの追加警告等を実装。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築関連（純関数群）
    - portfolio.portfolio_builder
      - 銘柄候補選定 (select_candidates)、等重み/スコア重み計算 (calc_equal_weights, calc_score_weights) を実装。
    - portfolio.risk_adjustment
      - セクター集中制限の適用 (apply_sector_cap)、マーケットレジームに応じた投資乗数 (calc_regime_multiplier) を実装。
    - portfolio.position_sizing
      - 各銘柄の発注株数計算 (calc_position_sizes) を実装。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate キャップ調整、コストバッファ考慮などを実装。
    - 上記モジュールは DB 参照せずメモリ内純関数として設計され、テスト容易性を考慮。
  - ユーティリティ
    - utils.logging_setup
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保存）を設定するユーティリティを追加。LOG_DIR / LOG_LEVEL の解決順を実装。ディレクトリ作成失敗時はファイル出力をスキップする耐障害性を持つ。
    - utils.process_priority
      - クロスプラットフォームのプロセス優先度設定と CPU affinity 固定ユーティリティを追加（Windows / POSIX を吸収）。権限不足や未対応環境を想定して警告でフォールバック。
  - monitoring / execution 補助
    - monitoring.monitoring_db の初期化呼び出しを起動時に行い、監視テーブルの存在を担保（冪等）。
  - tools
    - tools.paper_verification_report
      - ペーパートレードの検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）を算出し、閾値判定で PASS/FAIL を出力。コマンドライン引数で期間・DB パスを指定可能。
  - research
    - research.factor_research（実装開始）
      - Momentum などのファクター計算関数 calc_momentum の骨格を追加（DuckDB 接続を受け取り prices_daily を参照する設計。ファイルは途中まで実装）。

Changed
-------
- 設計上の注意点（ドキュメント的に明示）
  - run_monitoring は KABUSYS_ENV にかかわらず production sqlite_path を使用する（監視データは本番 DB に記録する方針）。
  - .env のロード挙動:
    - 優先順位は OS 環境 > .env.local > .env。
    - OS 環境を保護するための protected set を導入し、.env.local は既存 OS 変数を上書きしない。
  - run_execution は paper_trading モード時に paper 用 DB を用いることで本番 DB と完全分離する設計。

Fixed
-----
- .env パースの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、空行/コメント行のスキップなどを実装し、.env の柔軟な記述に対応。
- ログ周りの堅牢化
  - ログディレクトリ作成に失敗した場合でも stdout 出力は保証するようフォールバックを実装。

Security
--------
- 機密値（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）は Settings 経由で必須チェックを行う（未設定時は起動時に例外）。
- config_setup にて .env を生成する際に「絶対に Git にコミットしないこと」という注意喚起を出力。

Notes / その他
---------------
- 環境変数やファイルパスのデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - LOG_DIR: logs/
- 起動停止フラグ:
  - data/stop_requested.flag を監視して Graceful shutdown を行う設計。
  - KILL_FLAG_CLEAR_ON_START による Kill Switch 自動クリアの設定が存在（本番での誤設定に対して validate_config で警告）。
- ロギングは stdout を優先（cron 等で stdout/stderr を一本化して扱いやすくするため）。

今後の改善候補（コードから推測）
--------------------------------
- factor_research の完全実装（Momentum / Value / Volatility / Liquidity の計算を完了）。
- position_sizing における価格欠損時のフォールバック（前日終値や取得原価の利用）。
- 銘柄毎の lot_size をマスタ化して柔軟に対応。
- テストカバレッジの拡充（ユニットテスト / CI）。
- ドキュメントの充実（各 CLI の使用例、運用手順、監視閾値のガイドライン等）。

問い合わせ
---------
不明点や差分の修正希望があれば、対象ファイル名と期待する変更点を教えてください。