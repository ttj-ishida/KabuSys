# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このリリースノートは、リポジトリ内のコードから機能追加・設計上の注意点を推測して作成しています。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本フレームワークと CLI ツールを追加
  - run_execution.py：ExecutionEngine 起動スクリプト
    - KABUSYS_ENV による paper_trading モード判別。
    - paper_trading の場合は専用 SQLite（data/paper_trading.db をデフォルト）へ記録し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを抽象化。
    - ExecutionEngine をデーモンスレッドで起動し、stop flag（data/stop_requested.flag）で安全に停止可能。
    - 実行中 PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py：SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知でループを終了し、例外発生時はログを残して次ポーリングへフォールバック。
  - validate_config.py：設定検証 CLI
    - .env および config/*.yaml の存在／基本妥当性検査。
    - --strict モードで警告を失敗扱いにできる。
  - config_setup.py：対話式 .env 作成ウィザード
    - 初期設定の対話式入力、既存 .env の読み込み、保存。
    - J-Quants / kabu API / DB パス / ログレベル等の主要設定項目をサポート。
  - tools/paper_verification_report.py：Paper Trading 検証レポート生成ツール
    - 稼働率、注文成立率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL を判定。
    - CLI で期間指定（--from / --to）および DB パス指定（--db）可能。

- 環境変数・設定読み込みの改善（config.py）
  - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml で検出）。
  - .env のパースが堅牢化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしのインラインコメント処理（スペース直前の # をコメントと認識）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
  - Settings クラスを導入し、各種設定（DB パス、PID パス、閾値、環境名、paper_trading 用設定など）をプロパティで取得・検証。
  - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject のみ許容）。

- ロギングの統一化ユーティリティ（utils/logging_setup.py）
  - setup_logging(app_name, log_dir, level) を提供。
  - コンソール（stdout）出力 + 日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）。
  - 既存ハンドラの二重登録防止、ログディレクトリ作成失敗時のフォールバックを実装。

- プロセス優先度 / CPU affinity ユーティリティ（utils/process_priority.py）
  - set_process_priority(level) で Windows / POSIX を透過して優先度設定。
  - set_cpu_affinity(cpu_count) により最初の N コアへピン留め（サポート環境に限定）。
  - 権限不足や未対応 OS は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール（kabusys/portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）
    - calc_equal_weights, calc_score_weights（スコア全ゼロ時は等金額にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: セクター集中を回避する候補フィルタ（unknown セクターは除外対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下倍率（bull/neutral/bear）
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分アルゴリズムを実装
    - 単元株（lot_size）で丸め、max_position_pct / max_utilization を考慮した aggregate cap スケーリング、cost_buffer を考慮した保守的見積り
    - fractional 残差に基づく追加配分ロジックを実装（再現性確保のためソート安定化）

- Research / ファクター計算雛形（research/factor_research.py）
  - モメンタム / MA200 / ATR / 出来高系などを想定した関数群の骨格を追加（DuckDB 参照設計）。
  - DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計方針。

### 変更 (Changed)
- データベースの取り扱い
  - 監視（monitoring）は実行環境にかかわらず本番 sqlite_path を使用するように決定（監視データの一元化）。
  - Execution は paper_trading の場合に専用 SQLite を使い本番 DB と完全分離する挙動を明確化。

- ログ出力先の挙動
  - StreamHandler は stdout を使用（stderr ではない）: cron/スケジューラ実行時のリダイレクトを容易にするため。

### 修正 (Fixed)
- 環境変数のロードにおける既存 OS 環境変数保護
  - .env の上書き時に OS 環境変数を保護するため protected 引数を利用（config.py 内処理）。
- ExecutionEngine / Monitoring の停止制御強化
  - 起動前に停止フラグが立っている場合に起動を中止するガードを追加。
  - 監視ループ・エンジン実行中ともに stop flag を検知して安全に終了するフローを実装。

### ドキュメント (Documentation)
- 各スクリプト・モジュールに docstring を追加し、使用方法や設計上の注意点を明記（例: config_setup の使い方、paper_verification_report の閾値説明、portfolio の設計参照ドキュメント記載）。

### 既知の問題 / ワーク・イン・プログレス (Known issues / WIP)
- research/factor_research.py は実装途中の痕跡（ファイル末尾が途中で切れている）あり。実データ処理ロジックや SQL の完成が必要。
- 一部の TODO コメントあり（例: position_sizing で銘柄別 lot_size 対応、risk_adjustment の price フォールバックなど）。
- 実環境での優先度設定や CPU affinity の適用は権限やプラットフォームに依存するため、実行時にログで許可エラーが発生する可能性あり。

---

今後の予定（推測）
- factor_research の完成および DuckDB を用いたファクター集計の実装完了
- ExecutionEngine / SystemMonitor の統合テストと運用向け安定化
- 追加のツール（バックテスト、パフォーマンス可視化等）の導入

（注）この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴や設計ノートに基づく正式な履歴は git ログ等をご参照ください。