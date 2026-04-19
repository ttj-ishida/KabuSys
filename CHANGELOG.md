CHANGELOG
=========

すべての注目すべき変更点をこのファイルで記録します。
フォーマットは Keep a Changelog に準拠します。

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-04-19
-------------------

Added
- 実行/監視用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由してブローカークライアントを構築し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグファイル（data/stop_requested.flag）を検知すると安全に停止するロジックを実装。実行用 PID ファイル path をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db デフォルト）を使用する仕様。

- 設定・環境関連
  - config.py
    - 環境変数/ .env ファイルからの設定読み込みを統合する Settings クラスを追加。
    - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に .env/.env.local を読み込む（OS の環境変数を上書きしない挙動、.env.local は上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを抑止可能。
    - .env のパースでシングル/ダブルクォート、export プレフィックス、インラインコメント、エスケープシーケンスに対応。
    - Settings による入力検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と便利なプロパティを提供（is_live / is_paper / is_dev 等）。
  - config_setup.py
    - 対話式ウィザードを追加し .env の初期作成・更新を支援。既存値の読み込み、シークレットマスク表示、選択肢、保存確認などを実装。
  - validate_config.py
    - 起動前検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスのディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML 未導入時は警告で回避）など。
    - --strict オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（スコア降順、signal_rank によるタイブレーク）、等金額配分、スコア加重配分を提供。全てメモリ内純粋関数。
    - スコアが全て 0 の場合は等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック）を実装。未知レジームでの警告あり。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
    - lot_size（単元株）考慮、per-position 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りをサポート。
    - スケーリング時に端数扱い（lot 単位での切り捨て）と、残余キャッシュを用いた端数再配分アルゴリズムを実装。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。StreamHandler を stdout へ出力し、TimedRotatingFileHandler（日次ローテーション、30日保持）を logs/<app_name>.log に設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。既存ハンドラは再設定時にクリアする。
    - ログレベル・ログディレクトリの解決順を明記（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py
    - set_process_priority(level) で Windows/Linux/macOS の差分を吸収してプロセス優先度（nice / Windows priority class）を設定。AccessDenied 等を安全にハンドリングして警告ログを出す。
    - set_cpu_affinity(cpu_count) によりプロセスを指定コア数にピン留めする機能を追加。未対応環境や権限不足時は警告でスキップ。

- モニタリング DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を run スクリプトから呼び出し、監視用テーブルの存在を保証（冪等）。

- 解析 / リサーチ
  - research/factor_research.py（部分追加）
    - DuckDB 接続を受け取り、prices_daily / raw_financials を使って Momentum / Value / Volatility / Liquidity 等のファクターを計算するモジュールを追加（設計ドキュメントに基づいた純粋関数群を想定）。
    - モメンタム計算のための定数や窓長を定義（1M/3M/6M、MA200、ATR20 等）。（ファイル末尾で切れているが骨格を導入）

- ツール群
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から以下を集計:
      - システム稼働率（uptime_pct）、ポーリング数、エラー数
      - 注文成功率（Filled/Created）、送信率（Sent/Created）
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95） — P95 計算を含む
    - デフォルトの判定基準（しきい値）を定義し、PASS/FAIL 判定を行う。CLI オプション --from / --to / --db をサポート。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes / Implementation details
- 停止フラグ・Kill Switch
  - run_execution/run_monitoring はプロジェクト内 data/stop_requested.flag をチェックして安全に終了する仕組みを採用。Execution は検出時に engine.stop() を呼び出す。
  - Settings に kill_flag_clear_on_start などの Kill Switch 関連設定項目を用意。
- データベースの分離
  - Paper Trading 動作時は paper_sqlite_path を優先して使用し、監視用 DB と取引履歴の分離を行う設計。
- ログ出力
  - コンソールは stdout を使用（cron 等からのリダイレクトを想定）。
  - ファイルローテーションは日次で 30 日分保持。ログディレクトリ作成に失敗する環境でも起動可能。
- .env の取り扱い
  - .env の自動ロードはプロジェクトルートが特定できる場合にのみ行われる。自動ロードを無効化する環境変数を提供。
  - .env のパースは quote/escape/inline-comment を考慮した堅牢な実装。

Known issues / TODO
- research/factor_research.py の実装がファイル末尾で途中（calc_momentum の定義が途中で切れている） — 完全実装が必要。
- position_sizing の価格欠損（price が 0.0）の場合のフォールバックが TODO コメントで残されている（前日終値や取得原価などを用いる拡張を検討）。
- 将来的に単元株（lot_size）を銘柄ごとに持てるよう stocks マスタの導入を想定している。
- 一部外部ライブラリ（psutil, duckdb, PyYAML 等）への依存があるため、実行環境での導入確認が必要。

-----
配布バージョン: 0.1.0

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する際は差分・コミットログを参照して調整してください。）