CHANGELOG
=========

すべての注目すべき変更履歴はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
---------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- パッケージ初回リリース (v0.1.0)。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知してループを終了。
    - 監視は KABUSYS_ENV に関係なく settings.sqlite_path（本番パス）を使用して DB に接続。
    - duckdb と sqlite の接続を管理し、終了時に確実にクローズ。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - 停止フラグ検知で安全にエンジン停止。実行 PID を data/execution.pid に記録する想定。
- 環境設定・検証ツール
  - config.py
    - 環境変数の読み込み・ラッパー Settings を提供。
    - .env の自動読み込み（プロジェクトルート検出: .git または pyproject.toml に基づく）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 各種設定プロパティ（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG 等）を提供。
    - PAPER_FILL_MODE のバリデーション（instant, partial, never, reject）。
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）。
  - config_setup.py
    - .env を対話形式で作成・更新するウィザードを追加。
    - 主要な環境変数（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）の入力支援。
    - .env の読み書きを安全に行い、シークレットは表示をマスク。
  - validate_config.py
    - 起動前に .env と config/*.yaml の基本的な検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパース検証（PyYAML があれば実行）など。
    - --strict オプションにより警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの共通設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテートされる TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_LEVEL / LOG_DIR による設定、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティを追加。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。
    - psutil による操作で権限不足や未サポート環境は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック、警告出力）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap：セクター集中上限を超える場合に新規候補を除外するロジックを実装。unknown セクターは除外しない。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes：allocation_method ("risk_based", "equal", "score") に応じた株数算出ロジックを実装。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、総投下キャッシュ上限（available_cash）に基づくスケーリング（スケールダウン時の残差処理あり）。
    - cost_buffer による保守的見積もりをサポート。
    - TODO: 将来的に銘柄別 lot_size のサポートを想定する旨コメントあり。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- 研究モジュール（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム / MA200 / ATR / volume 等を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計（関数の実装は継続中、calc_momentum の実装が途中まで含まれる）。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として公開。
  - パッケージ外へのエクスポート（portfolio 等の便利な top-level API）を提供。

Security, Dependencies and Notes
- 必要な外部ライブラリ:
  - duckdb（DuckDB 接続）
  - psutil（プロセス優先度 / CPU affinity）
  - PyYAML は任意（validate_config の YAML 検証で使用。未インストール時は警告を出してスキップ）
- .env の自動ロードはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。
- 環境変数と有効値:
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - PAPER_FILL_MODE: instant | partial | never | reject
  - MONITOR_POLL_INTERVAL: 正の整数秒。無効値はデフォルト 60 秒にフォールバック（警告）。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化され stdout のみで動作します（stability を重視）。
- 監視・実行制御
  - 停止フラグ: data/stop_requested.flag を検知して各プロセスは安全停止。
  - 実行 PID: run_execution は data/execution.pid を使用（設定により pid ファイルパスを変更可）。
- 設計上の注意点 / TODO:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りされる旨の注記あり。将来的に前日終値等でフォールバックする検討。
  - position_sizing の将来的拡張として銘柄別 lot_size を想定するコメントあり。
  - research/factor_research.calc_momentum の実装が途中（ファイル末尾が途中で切れている）。本格利用前に完了が必要。

Breaking Changes
- 本リリースは初期リリースのため破壊的変更はありません。

Migration
- 既存ユーザは .env を config_setup.py で生成・更新し、validate_config.py で検証してから起動スクリプト（run_monitoring / run_execution）を使用してください。

Acknowledgements / Contributors
- 本 CHANGELOG はソースコード内容から推定して作成しました。実際のコントリビュータ一覧はリポジトリの履歴をご参照ください。