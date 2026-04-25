# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

リンク先のリリースノート等があればここに追記してください。

## [Unreleased]

（現在のスナップショットでは未リリースの変更はありません）

## [0.1.0] - 2026-04-25

初回公開リリース。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを導入（__version__ = "0.1.0"）。
  - プロジェクトの基本構成（config/.env 自動読み込み、logging、プロセス管理、DB 接続、CLI ユーティリティ等）を実装。

- 実行系
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、および ExecutionEngine の起動とデーモンスレッド監視を実装。
    - 停止フラグ（data/stop_requested.flag）検出時にセーフに停止する仕組みを追加。
    - PID ファイル書き込み（data/execution.pid）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する挙動を明示。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了、KeyboardInterrupt ハンドリング、例外発生時はログ出力して次ポーリングに進む。

- 設定・検証・ウィザード
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート判定: .git または pyproject.toml が起点）。
    - .env のパースロジック（クォート、エスケープ、コメント処理）を備えた堅牢な実装。
    - Settings クラスで環境変数にアクセスする高レベル API を提供（J-Quants、kabu API、DB パス、監視閾値、環境判定など）。
    - PAPER_FILL_MODE のバリデーションや PAPER_TRADING_SQLITE_PATH のサポート等を追加。

  - config_setup.py
    - 対話式 .env 作成ウィザードを追加（python -m kabusys.config_setup）。
    - J-Quants、kabu API、DB パス、ログレベル、Kill Switch 設定など主要項目を対話的に入力・更新可能。
    - .env の読み書き、既存値の再利用、シークレット項目のマスク表示に対応。

  - validate_config.py
    - 設定検証用 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数の存在確認、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml の存在および YAML パース検証（PyYAML があれば実行）等。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス管理
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保存）を設定するユーティリティを追加。
    - LOG_DIR / LOG_LEVEL に応じた解決ロジック、既存ハンドラのクリア、ファイル出力失敗時のフォールバック動作を実装。

  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを追加。
    - Windows（psutil の優先度定数）と POSIX（nice 値）に対応。CPU affinity の設定機能も提供。
    - 権限不足や未対応 OS の場合は警告を出し安全にスキップ。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補銘柄選定（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を追加。
    - スコアが全て 0.0 の場合に等金額配分にフォールバックするロジックを実装。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。
    - apply_sector_cap は既存保有と売却予定銘柄を考慮したセクター別エクスポージャー計算を行う。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出ロジック（risk_based / equal / score）を追加。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）および残余配分ロジックを実装。
    - cost_buffer により手数料・スリッページを保守的に見積る機能を提供。

  - portfolio/__init__.py で上記関数群をエクスポート。

- 解析 / ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加（python -m kabusys.tools.paper_verification_report）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH / --db オプションで上書き可能）。

  - research/factor_research.py（モジュール骨子）
    - ファクター計算（Momentum, Value, Volatility, Liquidity）を行うモジュールの骨子を追加（DuckDB を利用）。
    - calc_momentum 等の関数が定義されている（実装途中の箇所あり）。

### 変更 (Changed)
- run_monitoring と run_execution の挙動で、起動直後にプロセス優先度を "high" に設定するよう統一。
- ログ出力は stdout を優先して設定（cron/Task Scheduler からのログ収集を想定）。
- .env の自動ロードはプロジェクトルートが特定できる場合のみ行う（CWD に依存しない挙動）。

### 修正 (Fixed)
- ログディレクトリ作成失敗時にはファイルハンドラ作成をスキップしてコンソール出力のみ継続する安全なフォールバックを実装。
- process_priority.set_process_priority は権限不足等で失敗した場合に例外を投げず警告でスキップするように改善。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- apply_sector_cap のエクスポージャー計算は price_map に 0.0 が含まれる場合に過少見積りとなる恐れがあり、将来的に前日終値等のフォールバックを検討する TODO が残っている。
- position_sizing は現状単元株数 lot_size を全銘柄共通で扱う。将来的に銘柄別 lot_map の導入を想定する TODO がある。
- validate_config の YAML ファイル検証は PyYAML がインストールされている場合のみ有効。未インストール時は警告を出してスキップする。
- set_process_priority / set_cpu_affinity はプラットフォームや権限に依存するため、環境によっては効果がないことがある（警告出力のみ）。
- research/factor_research.py は一部実装が未完（ファイル末尾で途切れた実装箇所あり）。ファクター計算の完全実装は今後の作業。

### 環境変数（主なもの）
- 必須/重要
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
- 環境切替 / 実行設定
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading 時のフィルモード
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite パス（デフォルト data/paper_trading.db）
- データベース / ログ
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
  - LOG_DIR / LOG_LEVEL
- 監視 / Kill Switch
  - KILL_FLAG_CLEAR_ON_START（0/1）
  - MONITOR_POLL_INTERVAL（monitoring ポーリング間隔、秒。デフォルト 60）

### CLI（主なコマンド）
- python -m kabusys.config_setup — .env 対話式ウィザード
- python -m kabusys.validate_config [--strict] — 設定検証
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH] — Paper Trading レポート生成

---

今後の予定 / TODO（抜粋）
- factor_research の各ファクター計算の完成。
- apply_sector_cap の価格フォールバックロジック追加。
- position_sizing の銘柄別 lot_size 対応（stocks マスタ連携）。
- より詳細な Reconciler / RiskManager のテストカバレッジ拡充。

<!--
参考: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)
-->