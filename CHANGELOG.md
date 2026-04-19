CHANGELOG
=========

すべての顕著な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注: 日付はリリース作成日です。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、および Paper Trading 検証ツールを追加しました。

### 追加 (Added)
- パッケージ情報
  - __version__ を 0.1.0 に設定。

- 起動用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用する実装。
    - BrokerClientFactory でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - プロセス優先度を "high" に設定（set_process_priority を利用）。
    - 停止フラグ (data/stop_requested.flag) と execution.pid の利用に対応。
    - duckdb 接続を受け取り分析用データベースと併用。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視 DB の初期化を行う init_monitoring_db を呼出）。
    - 停止フラグ (data/stop_requested.flag) を検知してクリーンに終了。

- 設定・環境管理
  - config.py
    - Settings クラスを実装し、環境変数から各種設定を提供（J-Quants / kabu API / LINE / DB パス / 監視しきい値など）。
    - .env 自動ロード機能を実装（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースロジック:
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
      - クォートなしの場合のインラインコメント処理（空白の直前にある # をコメントと判断）
    - 各種検証ロジック（env 値チェック、PAPER_FILL_MODE の検証等）を備える。
    - paper_trading 専用の DB パス、PID / kill flag などの設定を提供。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - 主要項目のプロンプト・既存値の読み込み・マスク表示（シークレット）・.env 書き出しを実装。

  - validate_config.py
    - 起動前に設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL 検査、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML が利用可能な場合は）パース検査、本番時のガードチェックを実装。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定する共通セットアップを追加。
    - LOG_LEVEL / LOG_DIR の解決順をサポート。既存ハンドラの重複登録を防ぐために一旦クリアして再構成する。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続。

  - utils/process_priority.py
    - psutil を使って Windows / POSIX（Linux/macOS/FreeBSD）間の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level)（"high"/"normal"/"low"）を実装。
    - set_cpu_affinity(cpu_count) で CPU affinity を設定するユーティリティを追加。
    - アクセス権限不足などの失敗時は警告を出してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合は等金額配分へフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装（既存保有・当日売却予定の除外、"unknown" セクターの扱いなど）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をサポート、未知のレジームは警告してフォールバック）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method: "risk_based", "equal", "score" をサポート。
    - 単元株 (lot_size) 丸め、1銘柄上限 (max_position_pct)、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）を考慮した配分を実装。
    - risk_based の場合はリスク許容率 (risk_pct) とストップロス幅 (stop_loss_pct) を用いた目標株数計算を行う。
    - aggregate cap 超過時はスケーリング後に残余キャッシュを用いて端数処理（lot 単位）を行うロジックを実装。

  - portfolio/__init__.py で上記関数群をエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite データ（デフォルト: data/paper_trading.db）を解析して検証レポートを生成する CLI を追加。
    - 指標:
      - システム稼働率（system_status テーブル）
      - 注文成功率 / 送信率 / 総注文数（trade_logs）
      - リスク却下数（risk_logs）
      - API レイテンシ（avg / max / P95）
    - P95 計算、期間フィルタ (--from / --to)、閾値を用いた PASS/FAIL 判定を実装（デフォルト閾値をソース内で定義）。
    - DB が存在しない場合の案内メッセージを追加。

- リサーチ（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨子を追加（Momentum, Value, Volatility, Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計。
    - calc_momentum の定義開始（1/3/6ヶ月リターン、MA200乖離など）、定数・設計方針を追加。※実装未完・続きあり（初期コミット時点では部分実装）。

### 変更 (Changed)
- なし（初回リリースのため新規追加中心）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 実装上の補足
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探索して行います。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数で間隔を変更できます（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックして警告を出します。
- run_execution は paper_trading 環境時に本番 DB と完全に分離するため paper_sqlite_path を使用します。RiskManager の initial_portfolio_value は broker.get_available_cash() に基づいて初期化します。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソール出力のみで起動を継続する設計です（ファイルハンドラはオプション扱い）。
- process_priority と CPU affinity の設定は権限や OS に依存し、失敗時はログに警告を出して処理をスキップします。
- research/factor_research は設計に沿った形で骨組みを追加していますが、完全実装は今後の作業対象です。

---

今後のリリースでは、factor_research の完全実装、ExecutionEngine / SystemMonitor の詳細実装（テスト・エラーケース対応）、および追加のユーティリティやドキュメント拡充を予定しています。