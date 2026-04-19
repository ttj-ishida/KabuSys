CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記述しています。  
（コードベースから推測して作成しています。実際のコミット履歴ではありません）

Unreleased
----------

- 研究モジュールの拡張（進行中）
  - research/factor_research.py にファクター計算の骨組みと定数を追加。モメンタム（1M/3M/6M、MA200）、ATR、出来高系などの実装方針と定数が含まれるが、実装は途中のため追加作業が必要。

0.1.0 - 2026-04-19
-----------------

Added
- 基本パッケージ初期リリース（__version__ = 0.1.0）
  - パッケージのエクスポート定義を追加 (kabusys パッケージ)。
- 環境設定 / 設定ロード
  - src/kabusys/config.py: Settings クラスを追加。環境変数から各種設定（J-Quants / kabu API / DB パス / 環境種別 / ログレベル / 監視閾値など）を取得するプロパティを提供。
  - .env 自動読み込み実装: プロジェクトルート（.git または pyproject.toml）を検出し、.env/.env.local を OS 環境変数にマージ（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - PAPER_FILL_MODE（paper_trading 用の約定挙動）に対する入力検証を実装（有効値: instant/partial/never/reject）。
- CLI ツール
  - src/kabusys/config_setup.py: 対話式 .env ウィザードを追加。既存 .env 読み込み、シークレットマスク、.env の書き出しをサポート。
  - src/kabusys/validate_config.py: 起動前設定検証ツールを追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML がない場合は警告）などをチェック。--strict オプションで警告をエラー扱いにできる。
  - src/kabusys/tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH で DB を指定可能。
- 実行エントリ & 監視エントリ
  - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。停止フラグ（data/stop_requested.flag）を監視して安全に停止。
  - src/kabusys/run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバック。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグの検知、例外捕捉、DB/duckdb 接続の初期化・クローズ処理を実装。
- ログ & プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py: 共通ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせ、デフォルト logs/ ディレクトリ、ファイルローテーション 30 日分をサポート。LOG_DIR / LOG_LEVEL を尊重し既存ハンドラはクリアして再設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - src/kabusys/utils/process_priority.py: クロスプラットフォームでのプロセス優先度と CPU affinity 設定を追加。
    - set_process_priority(level): Windows（priority class）と POSIX（nice 値）に対応。無効な level は ValueError。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留め。cpu_count < 1 の場合は ValueError。実行環境で権限がない場合は警告してスキップ。
- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア全 zero の場合は等金額へフォールバック（警告）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限に基づく候補除外ロジック（unknown セクターは制限適用外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear のマッピング、未知はフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り、残余による追加配分ロジックなどを実装。
  - パッケージエクスポートを src/kabusys/portfolio/__init__.py に追加。
- データベース初期化（監視用）
  - run 系スクリプトから呼ばれる init_monitoring_db 接続フック（監視テーブルの冪等な初期化）の利用箇所を追加（sqlite3 接続経由）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（初期リリース）

Breaking Changes / 注意点
- Settings のプロパティは入力値検証を行います。例えば:
  - KABUSYS_ENV に不正な値を渡すと ValueError が送出されます（有効値: development / paper_trading / live）。
  - PAPER_FILL_MODE は限定された文字列のみ許容されます（instant/partial/never/reject）。不正値は ValueError。
- process_priority.set_process_priority(level) は無効な level 指定で ValueError を送出します。
- process_priority.set_cpu_affinity(cpu_count) は cpu_count < 1 を受け付けず ValueError を送出します。
- run_monitoring は監視 DB に settings.sqlite_path を常に使用します（環境に関わらず本番 sqlite_path を参照する設計）。
- .env の自動読み込みは既存 OS 環境変数を保護するため .env.local の上書きでも OS 環境変数を上書きしません。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

既知の制限 / TODO
- research/factor_research.py は実装途中（関数 calc_momentum の途中で切れている）。追加のファクター実装・テストが必要。
- position_sizing の price フォールバック（価格欠損時の扱い）は TODO コメントあり。前日終値等のフォールバックが未実装。
- ファイル I/O（ログディレクトリ作成や DB ファイルの存在）に関する権限やエラーは実行時に警告されるが、運用ドキュメントでの明記が必要。

---

この CHANGELOG はコードの内容から推測して作成しています。実際のリリースノートやコミット履歴がある場合はそちらを優先してください。