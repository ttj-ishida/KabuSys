CHANGELOG
=========

すべての重要な変更を記載します。フォーマットは「Keep a Changelog」準拠です。

[Unreleased]
------------

- まだリリースされていない変更はここに記載します。

[0.1.0] - 2026-04-25
-------------------

Added
- 初回リリース: KabuSys 0.1.0 を公開。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper-trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用可能（BrokerClientFactory による抽象化）。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全に停止可能。実行中は data/execution.pid を扱う。
    - 依存コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler）の組み立てを行う。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1未満はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番用 sqlite_path を参照する設計。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、例外時のログ記録を実装。

- 設定管理
  - config.py: 環境変数／.env の自動ロードと Settings クラスを実装。
    - プロジェクトルート検出（.git / pyproject.toml を基準）により CWD に依存しない .env 自動読み込み。
    - .env と .env.local の読み込みルール（OS 環境変数は保護）。
    - .env のパース機能: export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメント扱い等に対応。
    - Settings クラスで各種設定プロパティ（DB パス、KABUSYS_ENV 判定、paper_fill_mode の妥当性検査等）を提供。
  - config_setup.py: 対話式の .env 作成・更新ウィザードを追加。
    - シークレット項目はマスク表示。既存 .env の読み込みと Enter による既存値再利用に対応。
    - 保存前の確認表示と .env ファイル書き出し処理を実装。

- 構成検証ツール
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証。
    - KABUSYS_ENV=live に対する追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコアが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター別エクスポージャーに基づく候補除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を実装（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応した発注株数計算を実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、コストバッファ考慮、残差を用いた追加配分ロジックを実装。

- 分析・レポート
  - tools/paper_verification_report.py:
    - ペーパートレード結果検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計。
    - 閾値（稼働率 99%、成功率 90% 等）に基づく PASS/FAIL 判定を実装。
    - 日付フィルタ（--from / --to）と DB パス解決（--db / 環境変数 / デフォルト）に対応。

- 研究用モジュール（基盤実装）
  - research/factor_research.py:
    - DuckDB 接続を用いたファクター計算基盤を実装（モメンタム等の定義と設計方針を含む）。
    - 計算パラメータ（窓幅、スキャンレンジ等）を定義。※一部ファイルは実装途中。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - 一貫したログ設定ユーティリティを追加。stdout へ StreamHandler、日次ローテート (TimedRotatingFileHandler) をファイル出力に設定（デフォルト logs/）。
    - LOG_DIR / LOG_LEVEL の解決ルール、ログディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度設定（Windows と POSIX(nice) の両対応）。
    - set_cpu_affinity による CPU ピン留め機能も提供。アクセス権限不足等での安全なフォールバックを実装。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- research/factor_research.py の一部は実装途中で切れている（calc_momentum の続きなど）。今後のリリースで完成予定。
- position_sizing の価格フォールバック（price が欠損時の扱い）は簡易実装。将来的に前日終値や取得原価でのフォールバックを検討。
- .env 自動ロードはプロジェクトルートが見つからない場合はスキップされるため、パッケージ化後の利用環境では環境変数設定に注意すること。

--- 

注記: この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際の開発履歴やコミットメッセージに基づくものではありません。