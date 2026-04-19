CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠します。  
慣例: 重大な変更は Breaking Changes として明示します。

なお、本 CHANGELOG は提示されたソースコードから機能・挙動を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。本リリースでは自動売買システム「KabuSys」のコア起動スクリプト、設定管理、ポートフォリオ構築ロジック、ユーティリティ、検証ツール群を追加しています。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージメタデータを src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB を使用し MockBrokerClient を利用する仕組みをサポート。
    - エンジンはスレッド化してデーモンとして実行、外部 stop フラグ (data/stop_requested.flag) を監視して安全に停止可能。
    - execution.pid を PID 管理に使用。
    - 起動直後にプロセス優先度を "high" に設定。
    - duckdb と sqlite 両方の接続を使用。
    - RiskManager、OrderManager、Reconciler の組立てとデフォルト設定（rate_limit, circuit_breaker, max_drawdown など）を提供。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用して監視テーブルを初期化。
    - stop フラグ（data/stop_requested.flag）検知でループ終了。
    - 例外発生時もループ継続しログ出力でエラーを記録。

- 設定管理
  - config.py: 環境変数／.env の読み込みと Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
    - 自動 .env ロード順: OS 環境 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env のパースは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - Settings に多数のプロパティを提供（J-Quants / kabu / LINE / DB パス / モニタ閾値 / 環境判定等）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
    - is_live / is_paper / is_dev の便利プロパティ。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 主要な環境変数項目をインタラクティブに入力し .env を生成。
    - シークレット項目はマスク表示、既存値の再利用、保存確認等をサポート。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在（かつ PyYAML があればパース検証）を実施。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 設定未指定や KILL_FLAG_CLEAR_ON_START の警告等）。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルをスコア降順で選出。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装（全スコアが0の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（既存ポジションの時価ベースのセクター比率を計算して新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数配分方式（risk_based / equal / score）に基づく発注株数計算。単元株 rounding、max_position_pct、max_utilization、cost_buffer、aggregate cap スケーリング等に対応。

- ユーティリティ
  - utils/logging_setup.py:
    - 統一ロギング設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ自動作成、既存ハンドラのクリア、環境変数 LOG_LEVEL / LOG_DIR よる設定をサポート。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定。
    - psutil を使用し Windows の優先度クラス、POSIX の nice 値を切り替え。
    - CPU affinity 設定ユーティリティも追加（set_cpu_affinity）。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。

- 監視・DB 初期化
  - monitoring.monitoring_db.init_monitoring_db が呼び出されることにより、監視テーブルが存在することを保証（エンジンとモニタ両方で冪等に初期化）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）からレポートを生成。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ指標（avg/max/P95）等を算出。
    - デフォルト基準値（稼働率 >=99%、fill >=90%、send >=95%、P95 <=200ms）を用いた PASS/FAIL 判定を出力。

- 研究用ファクターモジュール（着手）
  - research/factor_research.py（モメンタム等のファクター計算の実装方針と一部定数を追加。DuckDB を利用して prices_daily / raw_financials を参照する設計を採用。実装の続きが必要な箇所あり）。

### 変更 (Changed)
- 初期設計としてのアーキテクチャ整備
  - 起動ユーティリティ（logging/setup、process priority）を統一し、各起動スクリプトが共通で利用する設計に変更。
  - DB 周りは duckdb（分析）と sqlite（監視・履歴）の使い分けを明確化。

### 修正 (Fixed)
- .env パース機能の堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント判定などの取り扱いを改善。

### 注意事項 / 既知の制限 (Known issues)
- research/factor_research.py はファイル末尾で計算ロジックが途中で切れており、完全実装が必要（提示コードの切断に依存）。
- Price の欠損（0.0）に対するフォールバックロジックは TODO コメントあり（現在は 0.0 を使うと過小見積りの懸念）。
- process_priority や CPU affinity の設定は権限不足やプラットフォーム差異により成功しない場合があり、それらは警告で扱われるに留まる。

---
脚注:
- 本 CHANGELOG は与えられたソースコードの内容から推測して作成しており、実際のリリース履歴やコミット履歴とは一致しない可能性があります。必要であれば、コミットログやリリースタグに基づく正確な CHANGELOG を生成します。