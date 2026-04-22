# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記載します。  
各リリースには主要な追加機能・変更点・バグ修正等を日本語でまとめています。

フォーマットの慣例:
- 追加: 新機能・新ファイル・新しい CLI など
- 変更: 既存挙動の改善・リファクタリング
- 修正: バグ修正
- 非推奨 / 削除 / セキュリティ: 必要に応じて記載

## [Unreleased]
- （現在未リリースの変更はここに記載されます）

## [0.1.0] - 2026-04-22

### 追加
- 全体
  - 初期公開版リリース。
  - パッケージメタ情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。

- 実行用ランナー / デーモン
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag の検出による安全停止。
    - Monitoring は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用の SQLite（data/paper_trading.db または PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離。
    - 実行用 PID ファイル管理（data/execution.pid）と停止フラグ検知による安全停止。
    - ExecutionEngine を別スレッドで動かす実行ループ。

- 設定 / 環境管理
  - config.py
    - 環境変数読み込み / Settings クラスを実装。
    - プロジェクトルート（.git または pyproject.toml）を元に .env 自動読み込みを行う仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースを強化（export 形式、シングル／ダブルクォート、エスケープ、インラインコメント処理など）。
    - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定など）を提供。入力値検証を含む（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。
  - config_setup.py
    - 対話式の .env 初期作成・更新ウィザードを追加。デフォルト値/選択肢やシークレット入力対応、保存確認機能を提供。
  - validate_config.py
    - 起動前設定検証 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）を実施。
    - --strict オプションにより警告も失敗扱い（exit code 1）にできる。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。
    - stdout への StreamHandler（標準出力）と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数 level/log_dir による解決優先順位と、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py
    - Windows / POSIX を吸収したプロセス優先度設定ユーティリティ（set_process_priority）。
    - CPU affinity を設定する set_cpu_affinity 関数を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を考慮して特定セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 銘柄ごとの注文株数計算 calc_position_sizes を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - lot_size（単元）丸め、1銘柄上限・ポートフォリオ総投下上限・cost_buffer を考慮した aggregate cap スケーリングロジックを実装。
    - 価格欠損時の挙動（ログ出力してスキップ）やスケールダウン時の残差処理（端数配分アルゴリズム）を実装。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH デフォルト: data/paper_trading.db）から検証レポートを生成する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下件数 等を集計し PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ（--from/--to）、閾値定義を含む。
  - tools パッケージ初期化ファイルを追加。

- リサーチ
  - research/factor_research.py
    - DuckDB 接続を受け取りファクター計算を行うための骨組み（モメンタム／ボラティリティ／Value 等の計算方針）を追加。モメンタム算出関数の実装開始（設計・定数定義を含む）。

- DB 初期化（監視用）
  - kabusys.monitoring.monitoring_db.init_monitoring_db を起動時に呼び出して監視テーブルの存在を保証（冪等）。

### 変更
- ログ出力先は stdout を優先（cron/スケジューラでの扱いを考慮）。
- .env の自動読み込みはプロジェクトルート検出に基づき行われるため、CWD に依存しない安定した挙動に改善。
- run_monitoring/run_execution は start-up 時にプロセス優先度を "high" に設定するように変更（set_process_priority 呼び出しを追加）。

### 修正（動作上の注意・堅牢化）
- 環境変数の整数パース時の堅牢化: MONITOR_POLL_INTERVAL が負や非整数を与えられた場合に警告を出してデフォルトにフォールバックする（run_monitoring._get_poll_interval）。
- logging_setup: ログディレクトリ作成に失敗した場合でもコンソール出力は継続するよう安全にフォールバック。
- process_priority, set_cpu_affinity: 権限不足や未対応機能の例外を捕捉し警告を出すことで起動失敗を防止。

### 既知の制限 / TODO
- research/factor_research.py は実装途中（ファイル末尾が切れている）であり、完全なファクター計算ロジックが未実装の可能性がある。
- position_sizing の価格フォールバック（price が欠損する場合の扱い）は TODO コメントあり（前日終値や取得原価などへのフォールバック検討）。
- 将来的な拡張: 銘柄ごとの lot_size を stocks マスタに持たせる設計へ拡張する旨の TODO。

### セキュリティ
- シークレット値（トークン・パスワード）の .env 対応は行われているが、.env を絶対に Git にコミットしない旨の注意書きを config_setup で明示。

---

注: この CHANGELOG はリポジトリ内のソースコード（src/kabusys 以下）から推測して作成しています。実際のリリースポリシーやバージョン管理ログ（git history）が存在する場合はそちらを優先してください。