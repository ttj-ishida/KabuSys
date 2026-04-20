# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」規約に準拠しています。  
バージョン番号は semantic versioning を想定しています。

## [Unreleased]

## [0.1.0] - 初回リリース
リリース日: 2026-04-20

### 追加 (Added)
- 全体
  - 初期バージョンをリリース。モジュール化された自動売買フレームワーク（KabuSys）のコア機能を実装。
  - パッケージメタ情報: __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。スレッドベースで ExecutionEngine を起動/監視し、停止フラグ (data/stop_requested.flag) を検知して安全に停止。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成（モック/本番の切替を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと ExecutionEngine への注入を実装。
    - 実行中 PID を data/execution.pid に記録するための pid_file サポート。
    - process prioritiy を「high」に設定するユーティリティ呼び出しを追加（優先度設定はプラットフォームに依存して可能な範囲で行う）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。監視ループ終了を示す停止フラグ (data/stop_requested.flag) を監視。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - Monitoring では KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（監視データは本番 DB に集約）。

- 設定管理 / CLI
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env/.env.local の読み込み順と上書きルール（OS 環境変数の保護）を実装。
    - .env の各行を堅牢にパースするユーティリティを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
    - Settings クラスを定義し、各種環境変数の取得とバリデーション (KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など) を提供。
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）・監視閾値・PID/kill flag パス等のプロパティを提供。

  - config_setup.py
    - 対話式の .env 作成・更新ウィザードを実装。標準的な設定項目（KABUSYS_ENV、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DB パス、LINE 設定等）をサポート。
    - 既存 .env の読み込み、シークレット項目のマスク表示、確認後の .env 書き出し機能を実装。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および（PyYAML があれば）パース検証を行う。
    - KABUSYS_ENV=live 時の追加警告（LINE 通知未設定、KILL_FLAG_CLEAR_ON_START の危険性など）を実装。
    - --strict オプションで警告を FAIL と扱うモードを提供。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全アプリケーションで共通利用できるログ設定ユーティリティを実装。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、デフォルト logs/<app_name>.log）を設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続するフォールバックを実装。
    - 既存ハンドラをクリアしてから再設定し、二重ハンドラ設定を防止。

  - utils/process_priority.py
    - Windows と POSIX（Linux/Mac 等）向けにプロセス優先度（nice / priority class）設定を抽象化したユーティリティを実装。
    - set_process_priority(level: "high"|"normal"|"low") と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナルの並べ替え（score 降順、signal_rank によるタイブレーク）select_candidates を実装。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額にフォールバック）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を適用し、上限セクターの新規候補を除外するロジックを実装（売却予定銘柄は除外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear）を返すユーティリティを実装。未知レジームは警告して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算実装。
    - ポジション単位上限、最大投入比率、lot_size（単元株）丸め、コストバッファ、aggregate キャップによるスケールダウンや端数配分ロジックを実装。
    - price 欠損時はスキップする挙動や、portfolio_value 0 のときのガードを実装。

- モニタリング / レポート
  - monitoring 側初期化呼び出し（init_monitoring_db）を各スクリプトで呼ぶように統一（監視テーブルの存在を保証、冪等）。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）等を集計してレポート出力。
    - デフォルトの閾値（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し、Pass/Fail 判定を出力。
    - --from / --to / --db オプションで期間・DB 指定が可能。DB 不存在時にエラーメッセージを出力。

- リサーチ（未完）
  - research/factor_research.py
    - ファクター計算（Momentum、Value、Volatility、Liquidity）実装の骨子を追加。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - 定数（期間等）と calc_momentum のドキュメントを追加。実装は継続中（ファイル末尾で途中）。

- パッケージ初期化
  - kabusys/__init__.py に __version__ と主要サブパッケージの __all__ を定義。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 注意点 / 既知の制限 (Known issues / Notes)
- run_monitoring は環境にかかわらず「本番 sqlite_path」を参照する設計。監視データの分離が必要な場合は運用上の注意を要する。
- process_priority / cpu_affinity の設定は OS 権限に依存する。権限不足の場合は警告を出してスキップする。
- portfolio.position_sizing において price が欠損（0.0）の場合、現状はスキップしているためエクスポージャーの過小見積りにつながる可能性がある（TODO コメントあり）。
- research/factor_research は一部実装途中の関数がある（今後の実装予定）。
- .env 自動ロードはプロジェクトルートの検出に依存する。プロジェクトルートが特定できない場合は自動ロードをスキップする。
- .env は決してリポジトリにコミットしないこと（config_setup のヘッダで明記）。

### セキュリティ (Security)
- 特になし（初回リリース）

---

今後の予定:
- research モジュールの完全実装（ファクター計算）とそれに基づくシグナル生成パイプラインの実装。
- テストカバレッジの充実、CI 用の設定追加。
- 監視・実行コンポーネントのより細かい分離（監視 DB のオプション化等）。