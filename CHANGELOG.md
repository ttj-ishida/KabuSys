CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/）に準拠して記載しています。  
バージョン番号はパッケージの __version__ に基づきます。

Unreleased
----------
- 今後の変更予定 / 開発中の項目をここに記載します。

[0.1.0] - 2026-04-18
--------------------
Added
- 初回公開リリース。
- 実行用エントリポイントを追加:
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレーディング用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止制御に data/stop_requested.flag、PID 管理に data/execution.pid を利用。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
    - ExecutionEngine の起動前に監視テーブルの冪等な初期化を行う（init_monitoring_db）。
    - リスク管理のデフォルト設定を RiskConfig として設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を利用する挙動（監視データの一元化）。
    - 停止制御にプロジェクト直下の data/stop_requested.flag を監視。停止時は安全に DB をクローズして終了。
    - 起動時にプロセス優先度を "high" に設定。

- 環境設定・検証用 CLI を追加:
  - config_setup.py
    - 対話式ウィザードで .env を生成・更新するツール。
    - J-Quants / kabu API / DB / ログレベル / Kill Switch 等の主要設定を対話的に入力できる。
    - 既存の .env があれば読み込み、Enter で既存値を再利用可能。保存前に内容確認を行う。
  - validate_config.py
    - .env と config/*.yaml の事前検証ツール。
    - 必須環境変数の未設定検出、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、YAML ファイルの存在と（PyYAML があれば）パース検証、本番環境用の追加ガードを実行。
    - --strict オプションで警告を FAIL 扱いにできる。

- 環境設定読み込み機構を追加:
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に自動で .env を読み込む機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
    - .env/.env.local の重ね合わせルール（OS 環境変数 > .env.local > .env）を実装。protected set により OS 環境変数の上書きを防止。
    - 環境変数のパースロジックはシングルクォート/ダブルクォート内のバックスラッシュエスケープやインラインコメントに対応。
    - Settings クラスを提供し、各種設定値（DB パス、PID/kill flag パス、しきい値、paper_fill_mode 等）をプロパティで取得可能にした。paper_fill_mode の妥当性チェックを実装。

- ポートフォリオ構築ライブラリを追加（pure functions）:
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコア降順選別（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等分配にフォールバックして警告出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中による候補除外ロジック（sell_codes による当日売却予定除外、"unknown" セクターは制限を適用しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear マッピング、未知レジームはフォールバックで 1.0 として警告）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に対応した株数計算。
    - risk_based の場合はリスク許容率とストップロスから base_shares を算出。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金の aggregate cap によるスケーリング（cost_buffer を考慮）。
    - スケーリング時は小数の端数（fractional remainder）に基づいて lot 単位で再配分する安定再現性のあるアルゴリズムを実装。
    - 価格欠損時の挙動（スキップ）についてログ出力。

- 実用ユーティリティを追加:
  - utils/logging_setup.py
    - 共通ロギング設定ユーティリティ。stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。ログレベルとログディレクトリの解決順を仕様化。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで継続。
  - utils/process_priority.py
    - Windows/Linux（POSIX）間の差分を吸収してプロセス優先度（high/normal/low）を設定可能。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を提供。
    - 権限不足などで設定できない場合は警告でスキップ。

- 監視・検証ツールを追加:
  - monitoring.monitoring_db.init_monitoring_db 呼び出しにより監視テーブルの存在を保証（起動スクリプトで冪等に初期化）。
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite のログから検証レポートを生成する CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計。
    - デフォルトの合格基準（稼働率>=99%、fill_rate>=90%、send_rate>=95%、P95<=200ms）を実装し、PASS/FAIL 判定を出力。
    - コマンドラインで期間指定（--from/--to）および --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を参照。

- 研究用モジュール（下流で DuckDB を用いるファクター計算）を追加（partial 実装のファイルを含む: research/factor_research.py）。
  - Momentum / MA200 / ATR / Liquidity 等のファクター計算設計に準拠するインターフェースと定数定義を含む（DuckDB 接続を受け取る設計）。

Changed
- パッケージ初期バージョンとして名前空間とエクスポートを定義: kabusys.__init__ に __version__ = "0.1.0" を追加。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数取り扱いにおいて、.env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。シークレットは対話式ウィザードでマスク表示するなど取り扱いに配慮。

Notes / Implementation details
- .env パーサはクォート内のバックスラッシュエスケープを解釈し、インラインコメントや export プレフィックスに対応します。
- run_monitoring と run_execution は起動時にプロセス優先度を設定し、停止フラグファイルの検出で安全に終了する制御フローを持ちます。
- Paper Trading と本番 DB を明確に分離する設計により、テスト中の誤発注やデータ混入リスクを低減しています。

References
- パッケージ内の CLI はそれぞれ `python -m kabusys.<module>` で実行できます（例: python -m kabusys.validate_config）。