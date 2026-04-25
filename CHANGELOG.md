CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-25
-------------------

初期リリース — KabuSys の基本機能群を実装しました。主な追加点・設計上の注意点は以下の通りです。

Added
- パッケージメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定管理
  - .env ファイルの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装。以下に対応:
    - export プレフィックス（export KEY=...）
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォートなし行のインラインコメント（直前が空白/タブの場合）処理
  - Settings クラスを提供し、アプリケーションで利用する各種設定値へプロパティ経由でアクセス可能に:
    - J-Quants / kabu API / LINE / DB パス（DuckDB / SQLite / Paper Trading 用 SQLite）
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値限定）
    - 監視・Kill Switch 関連設定（pid_path, kill_flag_path, kill_flag_clear_on_start）
    - システムしきい値（CPU/MEM/DISK）

- 設定ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup.py）を追加。既存 .env の読み込み、秘匿項目のマスク表示、保存機能を提供。
  - 設定検証ツール（validate_config.py）を実装:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック
    - DB パス（親ディレクトリ存在チェック）の検査
    - config/*.yaml の存在確認および（PyYAML が入っていれば）パース検証
    - live 環境向けの追加ガード（LINE 設定、KILL_FLAG_CLEAR_ON_START の警告）
    - --strict オプションで警告を FAIL 扱いにできる

- 実行 / 監視エントリポイント
  - run_execution.py:
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を "high" にセット。
    - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用し、本番 DB と分離（MockBrokerClient を利用する設計を想定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - 起動時に停止フラグが既に存在する場合は起動せず終了。
  - run_monitoring.py:
    - SystemMonitor ポーリングループ起動スクリプトを追加。プロセス優先度を "high" にセット。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告表示してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（意図的な分離）。
    - stop_requested.flag による停止検知、KeyboardInterrupt による終了処理あり。
    - SQLite / DuckDB コネクションを使用し、監視 DB の初期化（init_monitoring_db）を行う。

- ロギング / プロセス管理ユーティリティ
  - logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを実装。
    - 既存ハンドラは一度 flush/close してから削除し、二重設定を防止。
    - ログレベル / ログディレクトリの解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（set_process_priority）を実装。アクセス権限不足等の失敗は警告でスキップ。
    - CPU affinity を設定する set_cpu_affinity を実装（利用可能コア数に応じた安全な処理）。
    - サポート外プラットフォームでは警告を出してスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap を実装（当日売却予定銘柄を除外、"unknown" セクターを除外対象にしない）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - 複数の allocation_method に対応した株数算出（risk_based / equal / score）。
    - 単元株丸め (lot_size)、per-stock 上限・aggregate cap、cost_buffer による保守的見積り、スケーリングロジック（端数配分の再配分）を実装。
  - portfolio/__init__.py でエクスポートを統一。

- リサーチ / ファクター計算
  - research/factor_research.py（ファイル途中まで実装）:
    - Momentum, Value, Volatility, Liquidity といったファクター群を DuckDB の prices_daily / raw_financials テーブルから計算する設計。
    - calc_momentum の骨格（パラメータ定義、説明、日数定数など）を実装（関数は途中: 実装継続を想定）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを実装。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出し、閾値に基づく PASS/FAIL 判定を実施。
    - デフォルトの DB パスは data/paper_trading.db。引数で期間/DB を指定可能。
    - P95 計算、日付フィルタの適用、SQLite のテーブル欠如時のフォールバック（OperationalError 捕捉）を実装。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルが存在することを保証（冪等）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 注意事項
- 設定・運用に関する重要な挙動:
  - run_monitoring は環境にかかわらず Settings.sqlite_path（本番用の SQLite）を使用する設計になっています。監視データを別 DB に分離したい場合は運用ルールで対応してください。
  - paper_trading 実行時は run_execution が paper 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用するため、本番 DB と記録は分離されます。
  - process_priority / cpu_affinity の設定は環境（権限・OS）によって失敗する可能性があり、その場合は警告を出して処理をスキップします。
  - .env の取り扱い: 生成した .env を決してリポジトリにコミットしないでください（config_setup がヘッダでも注意喚起）。

今後の予定（例）
- research/factor_research の残り実装（各ファクター計算の SQL/Python 実装完了）。
- ExecutionEngine / SystemMonitor のユニットテスト強化、End-to-end テスト。
- broker クライアント（Mock / Live）のテストカバレッジ拡充。
- Windows/Linux 固有の挙動に関するドキュメント整備（プロセス優先度・ファイルパス等）。

---