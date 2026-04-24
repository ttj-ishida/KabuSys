# Changelog

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」を準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-24
初回リリース

### 追加 (Added)
- コアパッケージ基盤の実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0
  - パッケージエクスポート: data, strategy, execution, monitoring 等のモジュールをエクスポート

- 実行・監視用エントリポイントスクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供
    - KABUSYS_ENV により paper_trading モード時は paper_trading 用の専用 SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用
    - BrokerClientFactory によるブローカクライアント生成（paper_trading 時は MockBrokerClient を使用する設計）
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag（停止フラグ）で終了制御
    - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を扱う
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は環境に関係なく本番用 sqlite_path を使用する設計
    - 停止フラグ（data/stop_requested.flag）検出でループ終了、KeyboardInterrupt に対応
    - 起動時にプロセス優先度を "high" に設定

- 設定管理
  - config.py
    - Settings クラスで環境変数を一元管理（J-Quants / kabuAPI / DB パス / 監視パラメータ等）
    - .env 自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を探索）
    - .env/.env.local の読み込み順と上書きポリシーの実装（OS 環境変数は保護）
    - .env 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG 関連など多数の環境変数をサポート
    - 環境値の検証（有効値チェック、例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）

- 設定関連 CLI
  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザード
    - デフォルト値・選択肢・シークレット入力（マスク）に対応
    - .env の読み込み・確認・保存をサポート
  - validate_config.py
    - 起動前の設定検証ツール（必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の値検査、DB パス/設定ファイル存在チェック等）
    - --strict オプションにより警告を失敗扱いにできる
    - PyYAML が無い場合は config/*.yaml のパース検証をスキップして警告表示

- ポートフォリオ構築・リスク制御・ポジションサイジング（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定
    - calc_equal_weights, calc_score_weights: 重み計算（スコアが全て 0.0 の場合は等金額にフォールバック）
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存ポジションに基づく排除）
    - calc_regime_multiplier: レジームに基づく投下資金乗数（bull/neutral/bear をマップ）
  - portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数を決定（allocation_method: risk_based / equal / score）
    - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap スケールダウン処理
    - スケールダウン時の残差処理（lot 単位での再配分）を実装

- ユーティリティ
  - utils/logging_setup.py
    - 統一ロギング設定ユーティリティを追加
    - stdout へ出力する StreamHandler と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーへ設定
    - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラの一掃、ファイル出力失敗時のフォールバック挙動を実装
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定を提供
    - psutil による実装で、権限不足時は警告を出してスキップ

- 監視/検証ツール
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトで呼び出し、監視テーブルの初期化を保証（冪等）
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加
    - 系列指標: 稼働率(uptime)、注文成功率(fill rate)、送信率(send rate)、API レイテンシ（avg/max/P95）
    - PASS/FAIL の閾値を定義（稼働率 99%、fill rate 90%、send rate 95%、P95 latency 200ms）
    - --from/--to/--db オプションをサポート
    - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

- リサーチ（ファクター計算）モジュール（初期実装）
  - research/factor_research.py
    - モメンタム / Value / Volatility / Liquidity などのファクター計算を行う設計
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針
    - （注）ファイルは途中実装であり、以降の計算ロジック実装が必要

### 変更 (Changed)
- （初回リリースのため履歴無し）

### 修正 (Fixed)
- （初回リリースのため履歴無し）

### 削除 (Removed)
- （初回リリースのため履歴無し）

### 注記 (Notes / Known issues / TODO)
- research/factor_research.py は途中で終了しており、完全なファクター計算ロジックは未実装です。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過小評価される可能性があり、将来的に前日終値や取得原価のフォールバックを検討する旨コメントあり。
- position_sizing モジュールでは現状すべての銘柄が同一 lot_size を想定。将来的に銘柄別 lot_size のサポートを予定する TODO が記載されています。
- .env パーサは複数の引用符エスケープ・インラインコメント規則に対応していますが、特殊ケースの取り扱いに対してさらにテストが必要です。
- 実運用時は KABUSYS_ENV、LINE_*、KILL_FLAG_CLEAR_ON_START 等の設定に注意してください（validate_config でチェック可能）。

---

この CHANGELOG はコードベースから推測して作成しています。細かい実装意図や外部インターフェース変更（公開 API 等）がある場合は、実際のコミット履歴や設計文書に基づいて更新してください。