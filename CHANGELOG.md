CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

0.1.0 - 2026-04-19
------------------

Added
- 初回リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。KABUSYS_ENV が paper_trading の場合は MockBrokerClient / paper_trading 用 SQLite を使用して本番 DB と分離する挙動を実装。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止は data/stop_requested.flag と実行中のスレッド監視で制御。
    - 実行時の PID ファイルを data/execution.pid に保存する仕組みを想定。
    - RiskManager の既定設定（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を追加。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔 60 秒、環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明示。
    - 停止は data/stop_requested.flag による検知でループを終了。
- 設定管理
  - config.py: Settings クラスを追加。環境変数から各種設定（J-Quants トークン、kabuAPI パスワード、DB パス、PID/kill flag パス、閾値など）を取得するユーティリティを提供。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の妥当性検証。
    - .env の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - export 形式やシークレット入力、既存 .env の読み込みをサポート。
- 設定検証
  - validate_config.py: .env や config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config YAML の存在とパース検証（PyYAML が未インストール時は警告）、本番環境向けの追加警告など。
    - --strict オプションで警告もエラー扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガー設定ユーティリティを追加。
    - stdout へ StreamHandler、日次ローテート（30世代保持）のファイルハンドラを設定（logs/<app_name>.log）。
    - LOG_DIR, LOG_LEVEL, 引数での上書きをサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows/Linux(Mac 等) を抽象化して nice / priority を設定。権限不足時は警告してスキップ。
    - set_cpu_affinity により最初 N コアにピン止めする機能を提供。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナルの候補選定・重み計算（等分配・スコア加重）。
    - スコア全ゼロ時は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクター集中制限の適用と市場レジームに応じた投下資金乗数計算を実装。
    - apply_sector_cap: 既存保有・価格情報に基づくセクター上限チェック（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: "bull"/"neutral"/"bear" のマップ（未知はフォールバック 1.0）。
    - 実装内に価格欠損時の注意（TODO コメント）あり。
  - portfolio/position_sizing.py: 実際の株数決定ロジック（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-position および aggregate cap、cost_buffer（手数料・スリッページ見積）によるスケール調整、残余分の優先割当ロジックを実装。
    - 銘柄別 lot_size 拡張の TODO コメントあり。
  - portfolio/__init__.py で公開 API をまとめてエクスポート。
- データ解析・研究
  - research/factor_research.py: ファクター計算モジュールを追加（Momentum/Value/Volatility/Liquidity の設計・定数定義、DuckDB 接続を受ける設計）。
    - calc_momentum 等の関数が用意され、prices_daily / raw_financials を参照する設計。
    - 実装は一部（calc_momentum の途中）で未完の箇所が含まれる（今後の実装予定を示唆）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）。
    - 指標と閾値（デフォルト）:
      - 稼働率 (uptime) >= 99.0%
      - 注文成功率 (fill rate) >= 90.0%
      - 送信率 (send rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - クエリは trade_logs / system_status / risk_logs を参照し、欠損テーブルは graceful に扱う。
- その他
  - パッケージ初期化 (src/kabusys/__init__.py) にて __version__="0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / Known limitations
- research.calc_momentum の実装が途中で中断されている箇所が存在する（今後実装予定）。
- 一部の関数で価格欠損時のフォールバック処理が未実装（コメントに TODO があり、将来的に前日終値や取得原価を利用する方針）。
- 単元株（lot_size）を銘柄毎に管理する拡張は未実装。現状は全銘柄共通の lot_size が使われる。
- .env パースは比較的堅牢に実装されている（export 対応、引用符内のエスケープ処理、インラインコメント処理等）が、特殊なケースは注意が必要。

今後の予定（参考）
- research モジュールの完全実装（ファクター計算の SQL 実装を含む）。
- ブローカークライアント（BrokerClientFactory）や ExecutionEngine 周りの詳細実装の追加・テストカバレッジ向上。
- 銘柄別単元管理、価格フォールバックロジックの導入。

--- 

この CHANGELOG はコードベースの現在の状態から推測して作成しています。実際のリリースノートに反映する際は、コミット履歴やリリース担当者の確認に基づいて調整してください。