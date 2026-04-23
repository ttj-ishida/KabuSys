CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
初期リリースとしての変更点をまとめています。

Unreleased
----------

(なし)

0.1.0 - 2026-04-23
-----------------

Added
- 初期リリースを追加。パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。
- 実行エントリスクリプト:
  - run_execution: ExecutionEngine 起動スクリプトを追加。プロセス優先度を High に設定し、ブローカークライアントの組み立て、OrderManager / RiskManager / Reconciler を初期化して ExecutionEngine をバックグラウンドスレッドで実行する。KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（既定: data/paper_trading.db）を使用して本番 DB と明確に分離する。停止判定は data/stop_requested.flag を監視し、data/execution.pid に PID を出力する仕様。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番用 sqlite_path を使用する仕様（監視テーブルの一貫性維持）。
- 設定関連 CLI:
  - config_setup: 対話式ウィザードで .env を生成/更新する CLI を追加。複数の設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、LINE 設定等）をサポート。`.env` の書き込みテンプレートは Git へのコミット禁止旨の注記を含む。
  - validate_config: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML がインストールされている場合）などを検証。`--strict` モードで警告を失敗扱いにできる。
- ユーティリティ:
  - config: 環境変数読み込みと Settings クラスを追加。プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み機能を実装（`.env` → `.env.local`、OS環境変数保護あり）。`.env` の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ改善: export プレフィックス対応、クォートされた値のバックスラッシュエスケープ対応、クォートなしの行でのインラインコメント処理を実装。
  - logging_setup: 統一ログ設定ユーティリティを追加。stdout 出力の StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。ログレベル・ログディレクトリの解決順を文書化。
  - process_priority: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS 等対応、psutil を利用）。CPU affinity 設定ヘルパも追加。
- Portfolio モジュール（純粋関数群）:
  - portfolio_builder: 候補選定 (select_candidates)、等重配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア合計が 0 の場合は等重にフォールバック。
  - risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を追加。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
  - position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を追加。allocation_method として "risk_based", "equal", "score" をサポート。単元株（lot_size）での丸め、max_position_pct による上限、available_cash に対する aggregate cap を実装。cost_buffer を用いた保守的コスト見積りとスケールダウンアルゴリズム（小数端数を lot 単位で復元する残差処理）を含む。
- Paper Trading 検証ツール:
  - tools.paper_verification_report: Paper Trading 用 SQLite を読み取り、システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポートを標準出力に出力するスクリプトを追加。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を判定。コマンドラインで期間指定（--from/--to）や DB パス指定（--db）可能。
- Research:
  - research.factor_research: DuckDB 接続を受けてファクター（Momentum, Value, Volatility, Liquidity）を計算するためのモジュールを追加（モメンタム計算等の基盤を含む）。DuckDB の prices_daily / raw_financials テーブルを参照する設計。

Changed
- 環境ロードの優先順位と保護:
  - OS 環境変数を保護しつつ .env/.env.local をロードする実装を導入。`.env.local` は `.env` の上書き用として優先的に読み込まれる。
- ログ出力:
  - コンソール出力は stderr ではなく stdout を使用するように変更（cron 等での単純なリダイレクトを想定）。
- DB パスの既定値を明確化:
  - DuckDB の既定: data/kabusys.duckdb、監視用 SQLite の既定: data/monitoring.db、paper trading 用 SQLite の既定: data/paper_trading.db を文書化。

Fixed
- .env パーサ:
  - export 付き行、クォート内のエスケープ、インラインコメントの扱いなどの不具合に対処。
- ポートフォリオ重み計算:
  - 全銘柄スコア合計が 0 の場合に明示的に等金額配分にフォールバックし、警告ログを出すよう修正。
- 実行／監視の停止挙動:
  - data/stop_requested.flag を使った停止検知ロジックを追加・整備。監視は検知後にループを抜けてクリーンアップするようになった。ExecutionEngine も停止フラグ検知で engine.stop() を呼び適切に終了を待つ。

Security
- .env ファイルの取り扱いに注意:
  - config_setup にて生成される .env テンプレートに「.env は絶対に Git にコミットしないこと」の注記を追加。
- シークレット取り扱い:
  - config_setup の対話入力でシークレット項目はマスクして表示。

Notes / Migration
- 環境変数の自動ロード:
  - 自動ロードを無効にする必要がある（例: テスト）場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR_POLL_INTERVAL:
  - 監視ポーリング間隔を変更したい場合は MONITOR_POLL_INTERVAL（秒、正の整数）を設定してください。不正な値を設定した場合はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE:
  - Paper Trading の動作モードは PAPER_FILL_MODE（instant, partial, never, reject）で設定可能。無効値は ValueError を発生させます。
- Kill Switch:
  - 本番稼働時は KILL_FLAG_CLEAR_ON_START を 0 のままにすることを推奨します（本番で 1 にすると起動時に Kill Switch が自動クリアされてしまうため危険）。

Usage examples
- 実行:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 環境ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

Acknowledgements
- 初期実装であり今後以下を予定:
  - research.factor_research の各ファクター計算の完成・テスト追加
  - ExecutionEngine / SystemMonitor の統合テスト、及び paper/live ブローカークライアントのモック/インテグレーションテスト強化
  - 各種設定のドキュメント化（README / Operation Guide）

---

以上。必要であればバージョン履歴の分割（Unreleased セクションの追加や過去バージョンの細分化）を行います。