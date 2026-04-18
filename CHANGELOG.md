# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリース日はコミット時点の想定日付を使用しています。

## [Unreleased]
- （現在差分なし。次回リリースに向けた変更をここに記載してください）

## [0.1.0] - 2026-04-18

初回リリース。自動売買システム KabuSys の基盤機能を提供します。主要な追加点と実装概要は以下のとおりです。

### Added
- コアパッケージ構成
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。
  - モジュール群をエクスポート（data, strategy, execution, monitoring など）。

- 実行・監視ランナー
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の Paper Trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（本番/モック切替対応）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）の検知により安全に停止可能。
    - 実行 PID を data/execution.pid に書き出す仕組み（pid_file を利用）。
    - RiskManager のデフォルト設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, max_drawdown=0.20 等）を実装。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する挙動を実装。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
    - check_once() の例外をハンドルして次ポーリングへ継続。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサは export 形式、クォート値、エスケープ、コメント処理に対応。
    - Settings クラスを追加し、アプリケーション設定（J-Quants トークン、kabu API パスワード、DB パス、PID ファイルパス、閾値、環境種別など）をプロパティとして提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）や KABUSYS_ENV のバリデーションを実装。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘匿項目のマスク表示、既存 .env の読み込み、選択肢・デフォルト提示、保存前の確認を実装。
    - .env の書式をテンプレートで出力。

  - validate_config.py
    - 起動前検証用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）を実装。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）。
    - --strict モードをサポート（警告も FAIL 扱い）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガー設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）を設定。
    - ログレベルの解決順とログディレクトリの解決順を提供。ファイル出力に失敗した場合はコンソールのみで継続。
    - 日次ローテーションで 30 日分保持。
  - utils/process_priority.py
    - プラットフォームを抽象化したプロセス優先度設定（Windows・POSIX）を追加。psutil を使用。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足等で失敗した場合は警告を出して継続。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限を行う apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - レジーム乗数マップ（bull=1.0, neutral=0.7, bear=0.3）を導入。未知のレジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、手数料・スリッページ想定用 cost_buffer、利用可能現金に従うスケーリングロジックを含む。
    - risk_based では損切り率 stop_loss_pct を使ってリスク単位からポジションサイズを算出。
    - aggregate cap 超過時のスケールダウンと残差に基づく再配分ロジックを実装。

- 研究・ファクター計算（骨組み）
  - research/factor_research.py
    - モメンタム等のファクター計算モジュールを追加（設計方針、定数、関数定義の骨組み。一部実装が続くことを示唆）。
    - DuckDB 接続を想定し、prices_daily / raw_financials テーブルを参照して計算する設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、P95 レイテンシ、リスク却下数 等を計算・出力。
    - デフォルトの閾値を定義（稼働率 >= 99%, fill_rate >= 90%, send_rate >= 95%, P95 <= 200ms）し、PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と DB パス指定 (--db) をサポート。
    - p95 計算ユーティリティを実装。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が起動時に呼ばれ、監視テーブル群の存在を冪等的に保証。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Limitations / TODO
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があることを注記。将来的に前日終値などのフォールバックを検討する旨の TODO を残しています。
- position_sizing:
  - 現在 lot_size は全銘柄共通の固定値（デフォルト 100）として扱う。将来的には銘柄別 lot_size を stocks マスタに持たせる拡張が想定されています（TODO コメントあり）。
- research/factor_research.py:
  - ファクター計算モジュールは設計と一部処理が含まれており、完全実装は継続中（コード内に未完の箇所あり）。
- 自動ロードされる .env 処理はプロジェクトルート検出に依存するため、配布後の動作やテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を使えるよう配慮しています。

---

（補足）この CHANGELOG は与えられたコードベースの内容から実装意図を推測して作成しています。追加のコミット履歴やリリース方針がある場合は、それに合わせてエントリを調整してください。