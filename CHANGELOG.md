CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。   
フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 — 2026-04-19
-------------------

Added
- プロジェクトの初期リリース。
- 実行・監視用エントリポイントを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と完全分離。
    - プロセス優先度を "high" に設定、停止フラグ（data/stop_requested.flag）および PID ファイル管理を実装。
    - BrokerClientFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler を組み合わせてセッションをデーモンスレッドで実行し、安全に停止するためのループを実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視データを一元保存。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次回ポーリングへ継続。

- 設定管理・ウィザード・検証ツール
  - src/kabusys/config.py
    - 環境変数読み込み・ラッパー Settings を実装。
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）を追加。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを扱う堅牢な実装。
    - 各種設定プロパティ（DB パス、PID/kill flag パス、閾値、PAPER_FILL_MODE のバリデーション等）を提供。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。既存値の読み込み・マスク表示・検証・保存をサポート。
  - src/kabusys/validate_config.py
    - 起動前チェック CLI を提供（環境変数の有無・プレースホルダチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証、live 環境時の追加警告等）。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング・プロセスユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler（stderr ではなく stdout を使用）と、日次ローテーション（TimedRotatingFileHandler, 30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時にはファイルハンドラをスキップしてコンソールのみで継続する堅牢な挙動。
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加（Windows/Linux/他の POSIX 系サポート）。
    - psutil を用いて nice 値 / Windows 優先度を設定、失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) による CPU affinity 固定機能を追加（アクセス権限がなければ警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - シグナル選定と重み計算関数を追加:
      - select_candidates: スコア降順、同点は signal_rank によるタイブレーク。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0.0 の場合は等配分にフォールバックし WARNING を出力）。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - apply_sector_cap は既存ポジション金額を基にセクター上限を判定し、"unknown" セクターは制限の対象外とする設計。
    - calc_regime_multiplier は 'bull'/'neutral'/'bear' をマッピング、未知レジームは警告の上で 1.0 にフォールバック。
  - src/kabusys/portfolio/position_sizing.py
    - ポジションサイズ決定ロジックを実装（allocation_method: "risk_based" | "equal" | "score"）。
    - risk_based ではリスク許容率・ストップロスを考慮した株数算出、単元（lot_size）丸め、1銘柄上限・合計利用可能資金による集約キャップ、cost_buffer による保守的見積り、スケーリング時の残差分配を実装。
    - 価格欠損時のスキップやログ出力に配慮。

- Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を計算し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB 存在チェック、SQL 実行時の例外補足に対応。
    - CLI 引数 (--from, --to, --db) を提供。PAPER_TRADING_SQLITE_PATH 環境変数に対応。

- リサーチ（ファクター計算）初期実装
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの骨組みを追加（momentum/value/volatility/liquidity の設計と定数群）。
    - DuckDB 経由で prices_daily / raw_financials を参照する設計。calc_momentum の実装開始（以降の拡張を予定）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Requirements
- 依存（ランタイム）:
  - psutil: プロセス優先度・CPU affinity に使用（存在しない場合は該当機能は警告の上スキップ）。
  - duckdb: 分析用 DB アクセス。
  - PyYAML: validate_config の YAML 検証に利用（未インストール時はパース検証をスキップ）。
  - 標準ライブラリの sqlite3, logging, threading 等を使用。
- 環境変数の挙動:
  - 自動 .env ロードはプロジェクトルートが検出できる場合に有効。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - PAPER_FILL_MODE は instant/partial/never/reject のいずれかで、無効値は例外を送出。
  - KILL_FLAG_CLEAR_ON_START=1 は起動時に kill flag を自動クリア（本番では注意）。
  - MONITOR_POLL_INTERVAL は正の整数で指定。無効値はデフォルト 60 秒にフォールバック。
- 実行例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution

今後の予定（非網羅）
- factor_research の各種ファクター計算（完全実装）および正規化ユーティリティの統合。
- ExecutionEngine / Broker クライアント周りのテスト強化とエラー処理の拡充。
- 銘柄別 lot_size や手数料モデルのサポート拡張。