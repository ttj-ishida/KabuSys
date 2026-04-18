# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現行バージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 初回リリース
最初の公開バージョン。自動売買システム KabuSys のコア CLI・ユーティリティ・ポートフォリオ構築ロジック・モニタリング周りを実装しています。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor をポーリングする常駐監視ループを追加。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能。
    - 停止制御はプロジェクト直下の data/stop_requested.flag ファイルで行う。
    - 監視用 DB の初期化（init_monitoring_db）と DuckDB との接続を行う。
    - 起動時にプロセス優先度を high に設定。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（挙動に注意）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB に記録して本番 DB と分離する。
    - 起動時にプロセス優先度を high に設定。停止フラグ（data/stop_requested.flag）でエンジンを安全に停止可能。
    - 実行中 PID を data/execution.pid に書き込む想定の PID ファイルに対応。

- 設定と環境読み込み
  - kabusys.config.Settings を実装
    - .env / .env.local の自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 環境変数の取得ラッパー、デフォルト値、検証（KABUSYS_ENV, LOG_LEVEL 等）。
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH 等のパス解決。
    - PAPER_FILL_MODE（"instant"|"partial"|"never"|"reject"）を検証。
    - 各種監視しきい値（CPU/MEM/DISK）等の設定プロパティを提供。

- 設定改善ツール
  - kabusys.config_setup: 対話式ウィザードで .env ファイルを作成・更新する CLI を追加。
    - J-Quants / kabu API / DB パス / LINE 通知等の必須/任意項目を対話形式で設定。
    - .env ファイル書き込みテンプレートを提供。
  - kabusys.validate_config: 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在確認、YAML ファイルのパースチェック（PyYAML がある場合）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - kabusys.utils.logging_setup.setup_logging
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。
    - LOG_DIR 環境変数や引数でログ保存先を指定可能。ログローテーション 30 日分保持。
    - 既存ハンドラのクリア処理で二重設定を防止。
  - kabusys.utils.process_priority
    - set_process_priority(level) により Windows / POSIX を抽象化してプロセス優先度設定を行う。安全に失敗をハンドルして警告を出す。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアに固定可能（権限不足時は警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（タイブレークに signal_rank を使用）。
    - calc_equal_weights / calc_score_weights: 等比率・スコア正規化配分。全スコアが 0 の場合は等分にフォールバック。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限により新規候補のフィルタリングを行う（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づいて発注株数を計算。単元株（lot_size）で丸め、per-position と aggregate のキャップを適用、available_cash を超過する場合はスケールダウンして残差分を再配分するロジックを実装。
  - これらの関数は DB 参照を行わない純粋関数として実装され、ユニットテストしやすい設計。

- 解析・レポート
  - kabusys.tools.paper_verification_report
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 指標: 稼働率 (uptime)、注文成立率（fill rate）、送信率（send rate）、P95 レイテンシなど。閾値判定による PASS/FAIL を表示。
    - コマンド例:
      - python -m kabusys.tools.paper_verification_report
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- DuckDB 統合
  - 起動スクリプトや一部モジュールで DuckDB 接続を使用。データ分析用途の duckdb ファイルパスは DUCKDB_PATH（デフォルト data/kabusys.duckdb）。

- その他
  - パッケージバージョンを __version__ = "0.1.0" として設定。
  - kabusys.research.factor_research のモジュール骨子（モメンタム等のファクター計算ロジックの実装開始）。（一部実装途中）

### 変更 (Changed)
- ログ出力
  - StreamHandler を stdout に向ける設計に変更（stderr ではなく）。cron/Task Scheduler 等で stdout/stderr を統一してリダイレクトする運用を想定。

### 注意事項 / 破壊的変更 (BREAKING CHANGES)
- 監視 DB の取り扱い
  - run_monitoring は KABUSYS_ENV に依存せず「本番 sqlite_path」を使用する仕様になっています（意図的な設計）。開発やペーパートレード環境で監視ループを動かす場合は sqlite_path の環境変数設定に注意してください。
- ペーパートレード DB の分離
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用しており、本番の monitoring DB と完全分離されます。既存の DB パス運用がある場合は環境変数を適切に設定してください。

### 修正 (Fixed)
- .env パーサ
  - export KEY=val 形式とシングル／ダブルクォート内のバックスラッシュエスケープに対応する .env パーサを実装し、自動ロード処理を安定化。
  - デフォルトの読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護する仕組みを導入。

### セキュリティ (Security)
- 機密値は config_setup の対話で「secret」扱い（表示はマスク）を行うなどの配慮を追加。ただし .env 自体は常に機密情報を含むため、Git 等へのコミットは厳禁。

---

既知の改善候補（今後の予定）
- position_sizing: 各銘柄ごとの lot_size をマスタで管理する拡張（現状は全銘柄共通 lot_size）。
- risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値等）を使う改善。
- research.factor_research: ファクター計算ロジックの完成（現在一部実装途中）。
- 監視/実行のユニットテスト・統合テスト強化と、Docker / systemd ユニットのサポート。

---

参考: 主な環境変数とデフォルト
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング間隔）
- KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

お問い合わせや不明点があれば、どの箇所をより詳細に書き出すか指示してください。