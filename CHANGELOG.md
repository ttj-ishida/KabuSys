# Changelog

すべての注記は「Keep a Changelog」準拠の形式で記載しています。  
このプロジェクトはセマンティックバージョニングに従います。

なお、以下は提供されたコードベースから推測して作成した変更履歴です（実装の意図・新規追加点を中心にまとめています）。

## [0.1.0] - 2026-04-24

### Added
- 基本パッケージとバージョン情報を追加
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 設定管理
  - src/kabusys/config.py
    - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
    - 高度な .env パーサ実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いをサポート）。
    - 環境変数必須チェック用の _require ユーティリティ。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DuckDB/SQLite パス, paper trading 関連、監視閾値、環境種別 等）。
    - PAPER_FILL_MODE の検証、PAPER_TRADING_SQLITE_PATH 等の設定を追加。

- 環境設定ウィザード CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を初期作成・更新。
    - シークレット入力扱いや選択肢、デフォルト表示、保存確認を実装。
    - .env 書き込みテンプレートを提供（Git へコミットしない旨の注意文含む）。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - .env と config/*.yaml の検証ツール（--strict オプションで警告を失敗扱いにできる）。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML が無ければ警告）等を実装。
    - 本番 (live) 向けの追加ガード（LINE 通知設定チェック、KILL_FLAG_CLEAR_ON_START の警告）。

- 起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き (デフォルト 60 秒)。不正値時はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ検出、例外ハンドリング、リソースクローズ処理を実装。
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、専用の paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動／停止処理（stop フラグ / PID ファイル管理）を実装。
    - 起動時に stop フラグが立っている場合は起動せず終了する安全策を導入。

- ロギング基盤ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 既存ハンドラを安全に flush/close して再設定する実装。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX(nice) を抽象化）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates（スコア降順で上位 N を選択）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）を追加。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（既存ポジションのセクター露出を計算し、上限超過セクターの候補を除外）を実装。
    - calc_regime_multiplier（market レジームに応じたポジション乗数; bull/neutral/bear のマップと未知レジームのフォールバック）を実装。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes（risk_based / equal / score の割当方法、lot_size 単位丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り）を実装。
    - 割当結果のスケーリング時に残差処理（fractional remainder による追加 lot 単位配分）を実装。
  - src/kabusys/portfolio/__init__.py で主要関数をエクスポート。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite データベースからレポートを生成する CLI。
    - システム稼働率、注文成立率（Fill Rate）、送信率（Send Rate）、P95 レイテンシなどを集計し、閾値と比較して PASS/FAIL を判定。
    - 日付フィルタ (--from / --to) とカスタム DB パス (--db / PAPER_TRADING_SQLITE_PATH) をサポート。
    - p95 の計算、latency_ms の取り扱い、データ欠損時の N/A 表示を実装。

- 研究用ファクター計算（開始実装）
  - src/kabusys/research/factor_research.py
    - DuckDB 経由でモメンタム・ボラティリティ等のファクターを計算する設計。モジュール方針・定数と calc_momentum の骨子を追加（prices_daily / raw_financials テーブル参照、Zスコア正規化指針等）。
    - （ファイル末尾が途中で切れているが、設計と初期実装を含む。）

### Changed
- 環境変数読み込みの挙動設計
  - OS 環境変数を保護しつつ .env.local を .env より優先して上書きする仕様を採用（config.py）。
  - .env 読み込み関数に override / protected の概念を導入してテスト時や CI での柔軟性を確保。

- ログ出力先の標準化
  - setup_logging により全起動スクリプトで stdout（StreamHandler）を利用するように統一。これにより cron / systemd 等でリダイレクトを容易に。

### Fixed
- 起動/停止の安全性強化
  - run_execution.py / run_monitoring.py に Stop フラグ検出と安全な終了処理を実装（stop_requested.flag の検出、engine.stop 呼び出し、DB コネクションのクローズ）。

### Notes
- 本リリースはアーキテクチャの骨組み（設定管理、起動スクリプト、ログ基盤、優先度制御、ポートフォリオ構築ロジック、Paper Trading 検証ツール）を提供します。個別の実装（ExecutionEngine, SystemMonitor, BrokerClient 等）は別モジュールに依存しており、実動作の検証にはそれらの実装・外部サービス（kabuステーション、J-Quants 等）の設定が必要です。
- research/factor_research.py は未完の箇所が存在するため、ファクター計算の完全実装には追加の実装・テストが必要です。
- 一部機能は外部ライブラリ（psutil, duckdb, PyYAML 等）に依存します。環境により import エラーや機能制限が発生する可能性があるため、デプロイ前に依存関係を確認してください。

---

今後のリリース案（例）
- 0.2.0: ExecutionEngine と Broker クライアントの結合テスト、strategy 実装の追加、factor_research の完成
- 0.3.0: モニタリングアラート（LINE 通知）実装、スケーラビリティ改善、ドキュメント追加

（必要であればこの CHANGELOG を英語版やより細かなコミット単位の履歴へ展開します。）