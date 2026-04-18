# Changelog

すべての変更は Keep a Changelog の慣例に従って記述します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

すべてのバージョンはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回リリース。KabuSys のコアユーティリティ、起動スクリプト、構成管理、ポートフォリオ構築ロジック、ペーパートレード検証ツール、リサーチ用ファクタ計算モジュールの骨格を含む。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db）を使用し、本番データと完全分離。MockBrokerClient の利用を想定。
    - エンジンは別スレッドで実行され、data/stop_requested.flag による外部停止をサポート。
    - 起動時にプロセス優先度を "high" に設定し、pid ファイル (data/execution.pid) を扱う。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 監視用 DB 接続初期化（monitoring テーブルの準備）を行う。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（設計上の意図）。

- 設定管理・セットアップ・検証
  - config.py
    - Settings クラスを実装。環境変数から各種設定を取得（J-Quants / kabu API / DB パス / 監視閾値 / 実行環境など）。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を採用し、.env/.env.local の自動ロードを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 各種バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py
    - .env の対話式ウィザード。初期作成・更新を支援する。
    - 秘匿項目は表示をマスク、既存値の再利用、保存前確認を実装。
  - validate_config.py
    - 起動前チェック用 CLI。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証、本番時の追加ガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純関数群・DB 非依存）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートして上位を選択。タイブレークは signal_rank を使用。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア正規化配分。全スコアが0 の場合は等金額にフォールバックし警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限をチェックし、上限超過のセクターの新規候補を除外。unknown セクターは制限適用外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知のレジームは警告のうえ 1.0 にフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based", "equal", "score" をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer による保守的見積り、価格欠損時のスキップなどを実装。
    - risk_based 方式では stop_loss_pct と risk_pct を用いたリスクベース算出を行う。

- ユーティリティ
  - utils.logging_setup
    - 共通ログ設定ユーティリティ。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続。デフォルト 30 日分保持。
  - utils.process_priority
    - Windows / POSIX（Linux, macOS 等）差分を吸収したプロセス優先度設定（high/normal/low）と CPU affinity 設定を提供。
    - アクセス権限不足や未対応 OS の場合でも安全にスキップし警告を出力。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプト。
    - system_status / trade_logs / risk_logs 等から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL を判定。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。
    - --from/--to/--db オプションをサポート。

- リサーチ（骨格）
  - research.factor_research
    - モメンタム / Value / Volatility / Liquidity 系ファクタ計算の設計方針と、モメンタム計算関数（calc_momentum）の骨格を実装（DuckDB 接続を受け取る設計）。※ファイル末尾は実装途中の箇所が存在（スニペットの切れ）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line: クォートあり／なし、エスケープ、インラインコメントの取り扱いを実装し、.env 読み込みの互換性を向上。

### Security
- .env を生成する config_setup において明確に「.env を絶対に Git にコミットしないこと」をコメントで強調。

### Notes / Important behaviors
- run_monitoring は「監視用テーブル初期化」を行いますが、監視用 SQLite パスとして Settings.sqlite_path（本番想定）を使用します。モニタリングデータを分離したい場合は環境設定でパスを変更してください。
- run_execution は paper_trading モードで別 DB（PAPER_TRADING_SQLITE_PATH）を使用するよう設計されています。実行環境の分離に注意してください。
- 自動で .env/.env.local を読み込む機能はテストや特殊ケースのため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化できます。
- 一部モジュール（research.factor_research など）は実装途中の箇所が存在します（今後の追加実装予定）。

---

今後の予定:
- factor_research の完全実装（各ファクタ計算の SQL 実装・正規化ユーティリティとの統合）
- ExecutionEngine / Broker クライアントの具体的実装およびテストカバレッジ拡充
- config/*.yaml のデフォルト生成スクリプト（scripts/generate_config.py）との連携強化
- 監視・アラートの LINE 通知連携実装（Settings の LINE 設定を利用）

（必要であればリリース日や内容の追記、項目の分類変更を行います。）