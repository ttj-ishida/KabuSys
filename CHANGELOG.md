Unreleased
=========

- なし

[0.1.0] - 2026-04-19
====================

Added
-----
- 基本アプリケーションおよび CLI を追加。
  - パッケージエントリポイントとバージョンを定義:
    - src/kabusys/__init__.py (__version__ = "0.1.0")
- 起動スクリプト:
  - 実行エンジン起動スクリプトを追加（run_execution.py）。
    - KABUSYS_ENV による paper_trading の分離対応。paper_trading 時は専用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する想定。
    - 実行中は execution.pid ファイルを使い、data/stop_requested.flag による安全停止を実装。
    - スレッドで ExecutionEngine を起動し、停止フラグ検出でエンジン停止処理を行う。
  - 監視ループ起動スクリプトを追加（run_monitoring.py）。
    - SystemMonitor をポーリングするループを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計になっている。
- 環境設定 / 検証ツール:
  - 対話式 .env ウィザードを追加（config_setup.py）。
    - .env の読み込み・更新・書き出し機能、シークレット項目のマスク表示、保存確認を実装。
  - 設定検証 CLI を追加（validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証、live 環境向けの追加ガード（LINE 通知、Kill フラグ設定等）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- 環境設定読み込み / 管理:
  - .env 自動読込機構を追加（config.py）。
    - プロジェクトルート検出（.git または pyproject.toml 基準）、.env / .env.local を OS 環境変数を保護しつつ読み込む。
    - 高度な .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールなど）。
    - Settings クラスを提供し、各種環境変数をプロパティで安全に取得（例: duckdb_path, sqlite_path, paper_sqlite_path, paper_fill_mode, PID/kill flag path, thresholds, env 判定ユーティリティ等）。
- ログ・プロセスユーティリティ:
  - 統一ログ設定ユーティリティを追加（utils/logging_setup.py）。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを考慮。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（utils/process_priority.py）。
    - Windows / POSIX を吸収して優先度（high/normal/low）を設定。CPU コアピン留めも提供。権限不足や未サポート環境では警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）:
  - 銘柄選定・重み計算（portfolio/portfolio_builder.py）:
    - select_candidates: スコア降順・タイブレークロジック実装。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重（スコア合計が 0 の場合は警告して等配分へフォールバック）。
  - セクター制限・レジーム乗数（portfolio/risk_adjustment.py）:
    - apply_sector_cap: 既存保有に基づくセクター集中の除外ロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - 株数決定・リスク制限（portfolio/position_sizing.py）:
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に対応。lot_size の丸め、max_position_pct／max_utilization の上限、cost_buffer を用いた保守的推計と aggregate cap によるスケーリング・端数配分ロジックを実装。
- 実行系組立て（run_execution 内で利用）:
  - ExecutionEngine の初期化に必要なコンポーネントの組立（OrderRepository, OrderManager, RiskManager, Reconciler 等）コードが用意されている（実装は別ファイル群に依存）。
  - RiskManager のデフォルト設定（max_position_pct=20%, max_utilization=80%, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=20%）を導入し、initial_portfolio_value に broker.get_available_cash() を用いる。
- 監視 DB 初期化のためのフック（monitoring/monitoring_db.init_monitoring_db）が run スクリプトから呼び出されるようになっている。
- Paper Trading 検証レポートツールを追加（tools/paper_verification_report.py）。
  - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し、PASS/FAIL 判定 (閾値はファイル内定義)。
  - 日付フィルタ、P95 算出ユーティリティ、DB 存在チェック、SQLite クエリ保護（テーブル未存在時の例外捕捉）を実装。

Changed
-------
- なし（初期リリースとして新規追加が中心）。

Fixed
-----
- なし（初期リリースとして既知のバグ修正履歴はなし）。

Deprecated
----------
- なし。

Removed
-------
- なし。

Security
--------
- なし（セキュリティ修正履歴は未記載）。

Notes / 実装上の注記
-------------------
- .env の自動読み込みはプロジェクトルートが見つからない場合スキップされる設計。テスト時や特殊環境で自動読み込みを無効にするために KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を利用できる。
- run_monitoring は Monitoring 用の sqlite_path を環境に関わらず使用する旨がコメントに明記されており、本番監視と paper_trading などが DB を混在しないよう配慮されている。
- portfolio モジュールは純粋関数群として設計され、データベースアクセスを行わないためユニットテストが容易。
- factor_research モジュール（research/factor_research.py）はファクター計算の骨組みを実装。calc_momentum 等の計算ロジックは DuckDB を用いて prices_daily 等のテーブルを参照する想定（ファイル末尾で途中までの実装あり）。

今後の予定（提案）
-----------------
- factor_research の各ファクター（Value / Volatility / Liquidity）実装の完了と単体テスト追加。
- ExecutionEngine / BrokerClient 実装の結合テストと paper_trading の E2E 検証スイート整備。
- logging・プロセス優先度設定の更なるテスト（Windows / Linux / macOS）での挙動確認。
- config/*.yaml のテンプレート生成スクリプト（scripts/generate_config.py）の提供（validate_config の警告に対応）。

----- 
この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリースノートは開発履歴（git のコミットログ等）に基づいて更新してください。