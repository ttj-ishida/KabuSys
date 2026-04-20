# CHANGELOG

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

履歴のフォーマット:
- バージョン見出しは [X.Y.Z]（日付付き）
- 主要カテゴリ: Added, Changed, Fixed, Removed, Security

## [Unreleased]
（今後の変更をここに記載）

---

## [0.1.0] - 2026-04-20

初回リリース。自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、設定ツール、ポートフォリオ構築ロジックおよび検証ツールを含みます。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading DB（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで実行。
    - 停止制御: プロジェクトルートの data/stop_requested.flag を検知すると安全に停止する。
    - 起動プロセス ID を data/execution.pid に記録する（Engine に渡す）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正な値はデフォルトにフォールバックしログで警告。
    - 停止制御: パッケージルートの data/stop_requested.flag を検知してループを終了。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視テーブルを記録。

- 設定管理・検証・ウィザード
  - config.py
    - 環境変数・.env の読み込みロジックを実装。
    - 自動ロード順: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を起点に探索。
    - .env のパースはシングル/ダブルクォートやバックスラッシュエスケープ、行頭の `export `、行内コメントの扱い等に対応。
    - 必須/オプション設定のプロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）を提供。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - 環境モード (KABUSYS_ENV) の検証（development, paper_trading, live）。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新するツール。
    - デフォルト値・選択肢・シークレット扱い（表示マスク）のサポート、保存前の確認プロンプトを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml（存在する場合）の妥当性をチェックする CLI。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML があれば実施）、本番時のガードチェック（LINE 設定・KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict オプションで警告を FAIL 扱いにする機能。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 全スクリプトで共通に利用する logging の初期化ユーティリティを追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler、デフォルト logs/<app_name>.log、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装し、ハンドラの二重登録を防止するため既存ハンドラをクリア。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - プラットフォーム差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティを追加。
    - set_process_priority("high"|"normal"|"low") を提供。アクセス権限がない場合は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにピン留めする機能を実装（対応不可の場合は警告を出してスキップ）。

- ポートフォリオ構築ロジック（純粋関数群：DB非依存）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で上位 N を選定。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化による重み付け。全スコアが 0.0 の場合は等金額配分にフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 同一セクターの既存エクスポージャが閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
      - リスクベースでは risk_pct, stop_loss_pct を使用してポジションサイズを計算。
      - 単元株（lot_size）で丸め、銘柄ごとの最大上限（max_position_pct）を考慮。
      - aggregate cap（available_cash）を超える場合はスケールダウンし、lot_size 単位で残差配分を行うアルゴリズムを実装。
      - cost_buffer（スリッページ・手数料見積）を加味して保守的にコストを見積もる。

- 研究/分析ユーティリティ
  - research/factor_research.py
    - DuckDB 接続を受け、Momentum / Value / Volatility / Liquidity 等のファクター計算を行う基盤を実装（prices_daily, raw_financials テーブル参照）。モメンタム計算関数のスケルトン/定数を含む（関数は DuckDB 接続を受け取り日次指標を返す設計）。

- ユーティリティスクリプト
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB を解析して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）, 注文成功率（fill rate）, 送信率（send rate）, レイテンシ（avg/max/P95）等を算出。
    - デフォルト閾値: 稼働率 >= 99.0%, 成功率 >= 90.0%, 送信率 >= 95.0%, P95 <= 200 ms。
    - --from/--to/--db オプションに対応。PAPER_TRADING_SQLITE_PATH 環境変数を優先的に参照。

- DB 初期化ユーティリティ
  - monitoring/monitoring_db.init_monitoring_db を各起動スクリプトから呼び出して監視用テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Migration
- .env は決してリポジトリにコミットしないでください（config_setup.py でも注釈あり）。
- 自動で .env を読み込む挙動は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途等）。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかでなければなりません。不正値は ValueError を返します。
- MONITOR_POLL_INTERVAL は正の整数で指定してください。不正値や 0 以下はデフォルト 60 秒にフォールバックします。
- 本番運用時（KABUSYS_ENV=live）は validate_config による事前チェックを強く推奨します（--strict オプションで警告を失敗扱いにできます）。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。環境変数 LOG_DIR により変更可能です。ログディレクトリ作成失敗時は標準出力のみで継続します。

---

（以降のリリースはここに追記してください）