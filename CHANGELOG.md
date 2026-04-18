CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠して記載しています。
リリース履歴はリポジトリ内のコード内容から推測して作成しています。

フォーマット:
- "Added", "Changed", "Fixed", "Removed", "Security" を主に使用。

[Unreleased]
-------------
（今後の変更をここに記載）

[0.1.0] - 2026-04-18
-------------------
初期リリース（コードベースから推測した主要機能・変更点）

Added
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用 CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を使ったブローカークライアント生成を行い、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 実行中の停止管理のための PID ファイル（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは環境に関わらず本番 sqlite_path を使用する設計。

- 設定管理・支援ツール
  - config.py: 環境変数および .env 自動読み込み機能を追加。
    - プロジェクトルートを .git / pyproject.toml から探索し、自動的に .env /.env.local をロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - 多数の設定プロパティを提供（J-Quants, kabu API, DB パス, PID/kill flag, 監視しきい値, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV の検証（development/paper_trading/live）を実装。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。
    - 必須項目・シークレット項目のマスク表示、既存 .env の読み込み、保存機能を備える。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース検証（PyYAML があればパースも実行）などをチェック。
    - --strict オプションで警告を致命的扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順・タイブレークに signal_rank を用いる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外するロジック（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を提供（未知レジームは警告と共にフォールバック 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer による保守的見積りを実装。

- リサーチ / ファクター計算
  - research.factor_research（設計方針・各種定数が実装）
    - Momentum/Value/Volatility/Liquidity 系ファクターを DuckDB の prices_daily / raw_financials を用いて計算する設計。モジュールは日付ウィンドウや ATR などの定数を含む（関数の途中実装あり）。

- ユーティリティ
  - utils.logging_setup: 統一ログ設定ユーティリティを追加。
    - コンソール出力は stdout、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils.process_priority: プロセス優先度設定・CPU affinity ユーティリティを追加。
    - Windows と POSIX (Linux/Mac/FreeBSD) を吸収して nice 値や HIGH_PRIORITY_CLASS を設定。権限不足等は警告でスキップ。
    - set_cpu_affinity で最初の N コアにプロセスを固定可能。

- モニタリング DB 初期化
  - monitoring.monitoring_db:init_monitoring_db を呼び出して監視用スキーマの冪等初期化を行う（起動スクリプトから使用）。

- Paper Trading 検証ツール
  - tools.paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（AVG / MAX / P95）を集計して PASS/FAIL 判定を行う。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms。
    - DB パスはコマンドラインオプション (--db) または環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

Changed
- ログ設計
  - stdout を標準出力に使う方針（cron 等でのリダイレクトを想定）。既存ハンドラの二重設定防止を実装。

Fixed / Improved
- .env パーサーの堅牢化（config._parse_env_line）
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント判定の改善を実装。
  - .env の自動読み込み順序は OS 環境変数 > .env.local > .env（.env.local は override=True）。

- 設定検証の耐障害性
  - validate_config は PyYAML が未インストールでも警告出力して YAML 検証をスキップするように変更。
  - DB ファイル親ディレクトリが存在しない場合は警告（起動時に自動作成される可能性がある旨を明記）。

- ExecutionEngine / RiskManager のデフォルト設定
  - RiskConfig によるデフォルト制約（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）をコード上で明示。

- ポジション算出のスケーリングと端数処理
  - aggregate cap 超過時のスケーリングと lot_size 単位での残差配分ロジックにより、可再現で安定した株数割当てを実現。

Removed
- （初期リリースのため該当なし）

Security
- 機密情報の扱いに配慮
  - config_setup にてシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE チャネルトークン等）はマスク表示を行い、.env ファイル生成時に Git へコミットしないことを明示。

Notes / 補足
- 設定・運用上の注意
  - run_monitoring は「監視用 DB を常に本番 sqlite_path で使う」設計になっているため、paper_trading 環境でも監視 DB が本番と共有される点に注意。実運用で分離が必要な場合は設定やコードの調整を検討してください。
  - 実行スクリプトは停止フラグ（data/stop_requested.flag や KILL_FLAG_PATH）と PID ファイルを用いた外部停止・監視連携を想定しているため、運用時にはこれらファイルの扱いルールを整備してください。

今後の改善候補（コードから推測）
- portfolio.position_sizing: 銘柄別の lot_size（マスタ参照）に対応する拡張。
- apply_sector_cap: 価格欠損（price == 0.0）時のフォールバック価格（前日終値等）を導入してエクスポージャー算出精度を改善。
- research.factor_research: Factor 計算関数群の完成（ファイル末尾に未完の関数実装が見られるため）。
- monitor と execution のログ運用・アラート（LINE）連携・監視ルールの実装強化。

--- 
（以上）