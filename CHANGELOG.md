# Changelog

すべての注記は Keep a Changelog の形式に従います。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-18

初回公開リリース。シンプルな日本株自動売買システムのコアユーティリティ、ランナー、ポートフォリオ構築ロジック、検証ツール群を追加。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - サブパッケージ: data, strategy, execution, monitoring（エクスポート）

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント抽象化、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動を行う。
    - 実行中の停止は data/stop_requested.flag により検知し、エンジン停止処理を行う。PID ファイル（data/execution.pid）を扱う。
    - プロセス優先度を High に設定する処理を組み込み（utils.process_priority）。

  - run_monitoring.py
    - SystemMonitor を用いたポーリング監視ループのエントリポイント。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知によりループ終了。check_once() 内の例外はログ出力して継続。

- 設定管理
  - config.py
    - .env 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。OS 環境変数優先、.env.local を優先的に上書き。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化。
    - Settings クラスを提供し、環境変数から各種設定を取得（duckdb/sqlite パス、KABU_API_*、J-Quants トークン、PID/kill flag 関連、閾値等）。
    - env 値（development/paper_trading/live）や LOG_LEVEL のバリデーション、PAPER_FILL_MODE の検証ロジック等を実装。
    - settings インスタンスをモジュールスコープで提供。

  - config_setup.py
    - .env 初期作成・更新の対話式ウィザード。
    - デフォルト値や秘密設定（マスク表示）に対応し、.env の読み書きを行う。
    - 作成した .env の保存を行い、次の手順として validate_config を推奨するメッセージを表示。

  - validate_config.py
    - 起動前の設定検証 CLI（python -m kabusys.validate_config）。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの検出、config/*.yaml の存在チェック（PyYAML 未インストール時はスキップ）等を行う。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング/プロセスユーティリティ
  - utils/logging_setup.py
    - setup_logging(app_name=...) によりルートロガーを統一設定。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日保持）のファイルハンドラを追加。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 環境変数 LOG_LEVEL/LOG_DIR を尊重。
  - utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定と CPU affinity 設定を提供。
    - set_process_priority("high"|"normal"|"low")、set_cpu_affinity(N)。
    - psutil の権限エラーや未実装機能は警告ログでスキップする堅牢性を持つ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア総和が 0 の場合は等配分にフォールバックして WARNING を出す。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中制限を適用して候補をフィルタ。sell_codes（当日売却予定）を除外して既存エクスポージャーを計算。
    - calc_regime_multiplier(): market_regime に応じた乗数を提供（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): risk_based / equal / score の allocation_method に対応した発注株数決定ロジック。
    - lot_size（単元）丸め、max_position_pct に基づく per-stock cap、available_cash を超える場合のスケールダウンと残余キャッシュを使った優先割当て機構を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる。

- 研究モジュール（DuckDB 参照）
  - research/factor_research.py（ファクター計算の骨格を実装）
    - Momentum/Value/Volatility/Liquidity のファクター計算方針をドキュメント化。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する設計。
    - calc_momentum の実装開始（コード途中まで含む）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計してレポート出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等。
    - デフォルト基準値（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）で PASS/FAIL 判定。
    - コマンドライン引数 --from/--to/--db に対応。

- データベース統合
  - duckdb 連携を多数のコンポーネントで使用（ExecutionEngine、monitoring、research 等）。
  - monitoring 用の SQLite 初期化ユーティリティ init_monitoring_db が呼び出される（冪等に初期化）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の自動読み込み時に OS 環境変数を保護（既存の OS 環境変数は上書きされない、.env.local は override=True だが protected により OS 値は保護される）。
- .env ウィザードはシークレット値をマスクして表示。なお .env ファイルは Git にコミットしない旨を README に明記することを推奨。

---

注記:
- 実行ファイル・CLI の主な起動方法:
  - 監視: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper レポート: python -m kabusys.tools.paper_verification_report
- 今後の改善候補:
  - research.calc_momentum 等のファクター関数の完成、ユニットテスト追加。
  - posssible: stocks マスタによる個別 lot_size サポート、価格欠損時のフォールバックロジック、より詳細なロギング/メトリクス出力。