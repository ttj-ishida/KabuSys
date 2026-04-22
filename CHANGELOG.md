# Changelog

すべての重要な変更をこのファイルに記録します。  
形式は「Keep a Changelog」に準拠し、セマンティック・バージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-04-22
初回公開リリース。以下の主要機能とユーティリティを追加しました。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし警告を出力。
    - 停止制御にプロジェクトルート/data/stop_requested.flag を利用。
    - Monitoring は環境 (KABUSYS_ENV) にかかわらず本番の sqlite_path を使用する旨を明記。
    - ログ設定・プロセス優先度設定・DB 初期化（SQLite, DuckDB）を実施し、例外発生時にもループを継続して次回ポーリングまで待機する耐障害性を持つ。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db へ記録して本番 DB と分離。
    - 起動時にプロセス優先度を high に設定。
    - 停止フラグ管理（stop_requested.flag）および PID ファイル管理を行い、エンジンは別スレッドで実行され、フラグ検知で安全に停止する仕組みを備える。
    - 依存コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立てて起動。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
    - .env ファイルのパース実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント取り扱いなどに対応）。
    - Settings クラスを実装し、J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値 / ログ等をプロパティで提供。環境変数の必須チェックを行う _require を提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証を実装。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。既存値の再利用、シークレット値のマスク表示、確認後ファイル書き込みを行う。
  - validate_config.py
    - 起動前に .env と config/*.yaml の検証を行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在とパースチェック（PyYAML が無い場合は警告）を行う。
    - --strict モードで警告も失敗扱いにできる。

- ポートフォリオ構築 (pure functions, メモリ内計算)
  - portfolio.portfolio_builder
    - 銘柄選定 (select_candidates)、等分配 (calc_equal_weights)、スコア分配 (calc_score_weights) を実装。
    - 同点処理やスコアが全てゼロの場合のフォールバック等の挙動を明記。
  - portfolio.risk_adjustment
    - セクター集中制限適用 (apply_sector_cap) を実装。既存ポジションのセクター別時価を計算して上限を超えるセクターから候補を除外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear / 未知はフォールバック）。
  - portfolio.position_sizing
    - 株数決定ロジック calc_position_sizes を実装。allocation_method に応じた計算（risk_based / equal / score）と lot_size による丸め、aggregate cap によるスケールダウンロジック（残差配分アルゴリズム含む）を提供。

- ユーティリティ
  - utils.logging_setup
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / 引数による上書きに対応。
  - utils.process_priority
    - クロスプラットフォーム（Windows / POSIX）でプロセス優先度を設定するユーティリティ（set_process_priority）を追加。CPU affinity 設定ユーティリティも提供。
    - 権限不足や未サポート環境では警告を出力して安全にスキップ。
  - __init__.py
    - パッケージバージョン __version__ = "0.1.0" を追加。

- ツール
  - tools.paper_verification_report
    - Paper Trading 用の検証レポート生成スクリプトを追加。期間指定（--from/--to）や DB 指定（--db）をサポート。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどを算出し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）に基づいて PASS/FAIL 判定を行う。
    - SQLite のテーブル未存在時にも例外吸収して報告できるように実装。

- 研究モジュール（研究用ファクター計算）
  - research.factor_research
    - Momentum 等のファクター計算基盤を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。モメンタム指標 (mom_1m/mom_3m/mom_6m)、MA200 乖離率、ATR 等の計算方針を実装（関数 calc_momentum の実装開始）。
    - 設計方針として、外部 API に依存せず DuckDB と SQL/Python の組合せで算出する方針を導入。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 既知の問題 (Notes / Known issues)
- monitoring は KABUSYS_ENV にかかわらず sqlite_path（デフォルト: data/monitoring.db）を使用するため、paper_trading と監視 DB が分離されていない点に注意。paper_trading の実行データは Execution 側で paper_sqlite_path（data/paper_trading.db）を使って分離する設計。
- .env 自動読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では自動ロードがスキップされる可能性がある（その場合は環境変数を明示的に設定してください）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- position_sizing の将来課題:
  - lot_size を銘柄別に持たせる拡張（現在は全銘柄共通の lot_size 想定）を TODO として残しています。
  - apply_sector_cap の価格欠損（price が 0）の場合にエクスポージャーが過少見積りとなる問題を注記（将来的にフォールバック価格導入を検討）。
- research.factor_research の calc_momentum はファイル末尾で未完（スニペットが途中で切れている）ため、完全実装が必要。
- process_priority / set_cpu_affinity は権限や OS により動作しない場合があり、その際は警告ログを出してスキップします。
- logging_setup はログディレクトリの作成に失敗した場合、ファイルログが無効化される旨を標準エラーに出力します。

---

今後予定:
- factor_research の完全実装（Momentum の SQL 実行部完了、他ファクターの実装）
- ExecutionEngine / RiskManager の詳細なテストと paper_trading 用モックの充実
- config/*.yaml のテンプレ生成スクリプトと CI による自動検証の追加

---
保持方針: 重要なリリースごとに CHANGELOG を更新してください（Added / Changed / Fixed / Deprecated / Removed / Security）。
