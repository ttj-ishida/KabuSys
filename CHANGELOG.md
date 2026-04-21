CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-21
--------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env 自動ロード機構を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と OS 環境変数保護（既存 OS 環境変数を上書きしない挙動）を実装。
  - .env の自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 高度な .env パーサ実装: export 前置, シングル/ダブルクォート内のバックスラッシュエスケープ, 行内コメントの扱い等に対応。
  - Settings クラスを実装し、環境変数から各種設定値を取得するプロパティを提供（J-Quants トークン、kabu API 設定、DB パス、Paper Trading 設定、監視閾値、ログレベル等）。
  - KABUSYS_ENV / LOG_LEVEL の入力チェックと enum 的バリデーションを実装。
  - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証（有効値: instant/partial/never/reject）を実装。

- .env 作成ウィザード CLI（src/kabusys/config_setup.py）
  - 対話式ウィザードで .env を作成・更新するツールを追加。
  - シークレット項目のマスク表示、選択肢・デフォルト表示、キャンセル時の安全な取り扱いを実装。
  - .env ファイル書き出しテンプレートを提供（Git にコミットしない旨のヘッダ付き）。

- 設定検証 CLI（src/kabusys/validate_config.py）
  - 必須環境変数や KABUSYS_ENV/LOG_LEVEL、DB パス、config/*.yaml の存在と YAML パース検証を行う CLI を追加。
  - --strict オプションで警告を FAIL 扱いにできる機能を追加。
  - 本番（live）環境向けの追加安全チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
  - 統一的なログ設定関数 setup_logging() を実装。
  - stdout へ出力する StreamHandler（stdout 使用）と、日次ローテーション（TimedRotatingFileHandler）を組み合わせて自動設定。
  - ログディレクトリ（LOG_DIR / デフォルト logs/）の自動作成、作成失敗時のフォールバック（ファイル出力をスキップしてコンソール出力のみ）を実装。
  - 既存ハンドラの安全なクローズ／置換、ログレベル解決優先順位（引数 > 環境変数 > デフォルト）を実装。
  - 日次ローテーションの保持期間は 30 日。

- プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収してプロセス優先度を設定する set_process_priority() を提供（high/normal/low）。
  - CPU コア固定の set_cpu_affinity() を提供（利用可能コア数を超える場合は全コアを使用）。
  - psutil を利用し、権限不足や未実装の環境では安全に警告してスキップする実装。

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine の起動スクリプトを実装。
  - 起動時にプロセス優先度を high に設定。
  - Paper Trading 環境では専用の SQLite（data/paper_trading.db）を使用して本番 DB と分離（Settings に基づく）。
  - BrokerClientFactory によるブローカークライアント生成（paper/live を自動選択）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
  - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）をサポートし、停止フラグ検知時に安全にエンジンを停止・終了する制御を実装。
  - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、initial_portfolio_value を broker.get_available_cash() から取得。

- 監視起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプトを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
  - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを一元化。
  - 起動時にプロセス優先度を high に設定、監視 DB 初期化（init_monitoring_db）と DuckDB 接続を行う。
  - 停止フラグファイル検知と例外のログ記録を含む堅牢なループ実装。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/）
  - portfolio_builder:
    - select_candidates: スコア降順・同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分とスコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジックを実装（売却予定は除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバックし警告。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算を実装。
    - 単元株（lot_size）での丸め、1 銘柄上限・全体上限(max_utilization)、手数料・スリッページ考慮の cost_buffer、aggregate cap によるスケーリングと残差の再配分ロジックを実装。
    - 価格欠損時のスキップやログ出力で堅牢化。

- Paper Trading 検証レポートツール（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレードの SQLite DB を読み取り、システム稼働率、注文成功率（Filled）、送信率（Sent）、リスク却下数、API レイテンシ（平均／最大／P95）等を集計してレポート出力する CLI を実装。
  - しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。
  - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。
  - P95 の計算、NULL 値・テーブル未存在時の安全なフォールバックを実装。

- 研究用ファクター計算モジュール（src/kabusys/research/factor_research.py）
  - Momentum（1M/3M/6M リターン、MA200乖離）、ATR/出来高等のファクターを計算する設計を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する方針を実装（実装途中でのコード断片あり）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- .env にシークレットを含める設計のため、config_setup にて .env を絶対に Git にコミットしない旨を明記。

Notes / Developer hints
- 実行スクリプトは stop flag（data/stop_requested.flag）と PID ファイルによる外部制御を前提にしており、運用時にはデータディレクトリの権限／存在確認を行ってください。
- logging_setup はログディレクトリ作成に失敗した場合でもプロセスが継続するよう設計されています。外部のログ収集を行う場合は LOG_DIR の設定を推奨します。
- position_sizing の lot_size は現状一律 100 を想定しており、将来的に銘柄別単元対応の拡張が予定されています（コメント参照）。
- research/factor_research.py は設計と一部実装が含まれていますが、完全実装に向けて追加の単体テストとテーブルスキーマ確認が必要です。

ライセンス、貢献方法等はプロジェクトの README を参照してください。