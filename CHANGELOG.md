# Changelog

すべての重要な変更点を Keep a Changelog の形式で記載します。  
リリース日や内容はコードベースから推測してまとめています。

全般的な注記
- 初期リリースとしてシステム全体のコア機能（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、検証ツールなど）を実装しています。
- 環境変数・設定ファイル（.env）を中心とした設定管理と CLI ウィザード / 検証ツールを提供します。
- DuckDB と SQLite を併用し、分析用データベースと監視/注文ログを分離する設計です。

## [0.1.0] - 2026-04-20

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行 / 監視スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、スレッド実行によるエンジン制御と停止フラグ監視を実装。
  - run_monitoring.py
    - SystemMonitor をポーリングで実行する起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値や 0 以下の場合はデフォルトへフォールバック。
    - 監視機能は環境に関わらず本番用の sqlite_path を使用（監視 DB を一元管理）。

- 設定管理
  - config.py
    - Settings クラスで環境変数を一元管理（J-Quants, kabuAPI, DB パス, paper trading 設定, 監視しきい値等）。
    - `.env` ファイル自動読み込み（プロジェクトルート判定: .git または pyproject.toml を基準）。読み込み順: OS 環境変数 > .env.local > .env。
    - `.env` 自動読み込みを無効にするフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - PAPER_FILL_MODE のバリデーション（有効値: "instant", "partial", "never", "reject"）。
    - env 解釈（KABUSYS_ENV）とログレベルのバリデーション。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI。
    - シークレット項目は表示をマスクし、既存値の再利用やデフォルト値をサポート。
    - 生成された .env はテンプレートヘッダ付きで書き出す。

  - validate_config.py
    - 起動前に .env や config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML がない場合は検証をスキップ）などを実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分、全スコアが 0 の場合は等金額へフォールバック（警告出力）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるため既存保有比率が閾値を超えるセクターの新規候補を除外。sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは警告して 1.0 にフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 銘柄ごとの発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - risk_based: 損切り率・リスク許容率に基づく単銘柄サイズ計算を実装。
    - 等金額/スコア配分: 資産比・max_utilization・lot_size（単元株、デフォルト 100）を考慮。
    - aggregate cap: 全銘柄合計コストが利用可能現金を超える場合にスケールダウンし、lot_size 単位で再配分するアルゴリズムを実装。cost_buffer による手数料・スリッページの保守的見積りを考慮。

- 解析・研究ユーティリティ
  - research/factor_research.py（ファクター計算モジュールの骨子）
    - DuckDB 接続を受け prices_daily / raw_financials を用いる設計で、Momentum / Value / Volatility / Liquidity 系の因子を計算する方針を実装（ファイルは途中まで実装）。

- 運用ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティ。stdout 出力（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーへ設定。
    - ログディレクトリは引数 > 環境変数 LOG_DIR > デフォルト logs/ の順で解決。ファイルハンドラは 30 日分を保持。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで cron 等からのリダイレクト運用に対応。

  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを提供。
    - psutil を使い、Windows では priority class、POSIX（Linux/Mac/FreeBSD）では nice 値を設定。アクセス権限がない場合は警告してスキップ。
    - set_cpu_affinity により最初の N コアに固定する機能を提供（引数検証あり）。

- モニタリング DB 初期化ユーティリティ
  - monitoring_db.init_monitoring_db を使用して監視テーブルが存在することを保証（冪等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（env/PAPER_TRADING_SQLITE_PATH または --db）からデータを集計し、稼働率 (uptime)、注文成功率(fill rate)、送信率(send rate)、P95 レイテンシなどを算出するレポート出力を提供。
    - デフォルトの合格基準（閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from / --to）をサポート。P95 計算、NULL ハンドリング、データ欠損時は N/A 表示を実装。

- CLI/モジュールのエントリポイントを複数提供
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
  - python -m kabusys.tools.paper_verification_report
  - run_monitoring.py, run_execution.py を直接実行可能

### Changed
- DB と実行環境の分離方針明確化
  - 監視モジュールは環境に関係なく監視用 sqlite_path（デフォルト: data/monitoring.db）を使用する設計。これにより監視データは paper/live に依存せず一元管理される。
  - 実行エンジンは paper_trading 環境の場合に限り専用の paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。

- .env 読み込みの取り扱い
  - 自動ロード時の優先順位を OS 環境 > .env.local > .env とし、OS の既存環境変数は保護（上書き禁止）する動作を採用。
  - .env のパースは export KEY=val 形式、クォート文字列とバックスラッシュエスケープ、インラインコメントの扱い（クォート無しの場合は '#' の前に空白がある時のみコメントと認識）に対応。

- ログ設定のデフォルトとフォールバック
  - LOG_LEVEL は引数 > 環境変数 > "INFO" の順で決定。ログディレクトリ作成に失敗した場合はファイル出力を無効化し、コンソール出力のみで継続。

### Fixed / Robustness
- run_monitoring.py のポーリング間隔取得
  - MONITOR_POLL_INTERVAL が不正（非整数、0 以下等）の場合、警告を出してデフォルト 60 秒にフォールバックするように実装。time.sleep に渡す不正値による例外を回避。

- process_priority / CPU affinity の例外ハンドリング
  - アクセス権限不足やプラットフォーム非対応時に例外を握りつぶして警告を出すようにし、プロセスの起動失敗を防ぐ。

- config_setup の対話式入力の堅牢化
  - EOFError / KeyboardInterrupt の扱いを明確化し、中断時に現在の変更を保存しない挙動を保証。

- validate_config の YAML 検証
  - PyYAML が未インストールの環境では YAML 検証をスキップして警告を出力するようにして依存性がない環境でも動作するように改良。

### Notes / Misc
- 一部モジュール（research/factor_research.py 等）は計算方針や定数が整備されており、DuckDB を前提としたファクター計算の実装を行う設計になっていますが、ファイル末尾は途中実装のままの箇所が存在します（今後の拡張対象）。
- 実運用前に .env の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定し、validate_config でチェックすることを推奨します。
- 本リリースではログ・プロセス優先度・停止フラグ（data/stop_requested.flag や data/execution.pid）など、運用面の制御を重視した設計が反映されています。

--- 

今後のリリースでは以下のような改善を想定しています（例）:
- factor_research の完全実装（全ファクターの SQL/Python 実装完了）
- strategy / execution 内の具体的な戦略実装と統合テスト
- 銘柄別 lot_size やコストモデルの拡張（手数料・スリッページモデルの詳細化）
- モニタリング・アラート（LINE 通知等）の強化と本番向けガードの追加

ご要望があれば、CHANGELOG の内容をリポジトリの実際のコミット履歴や日付に合わせて調整します。