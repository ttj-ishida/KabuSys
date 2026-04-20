CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-20
-----------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコア機能を実装。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - ブローカークライアントの抽象化（BrokerClientFactory）を導入し、実運用／モックの切替を想定。
    - Engine の起動・停止制御（PID ファイル、stop フラグ監視、デーモンスレッド実行）を実装。
    - RiskManager, OrderManager, Reconciler, OrderRepository 等の組み立てロジックを実装し、デフォルトパラメータ（例: max_position_pct, max_utilization, 初期ポートフォリオ値等）を設定。
- 監視スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の不正値はデフォルトにフォールバックして警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを抜ける仕組みを実装。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。
- 設定関連
  - config.py: 環境変数/.env の読み込みと Settings クラスを実装。  
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml）を行い、.env と .env.local の読み込み順を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複数の設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）、入力検証（有効値チェック）を実施。
    - paper_trading 用 DB パスや PID / kill flag 関連の設定を提供。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（CLI）。既存 .env 読み込み、シークレットマスク、保存機能を備える。
  - validate_config.py: 起動前に設定不備を検出する CLI を追加。必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML 利用時）、本番向け追加ガードを実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限の apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。未知のレジームはフォールバックで乗数 1.0 を返し警告を出力。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。  
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。
- ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを実装。  
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
    - LOG_LEVEL / LOG_DIR / 引数による柔軟な設定解決。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティを実装。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足時は警告を出して安全にスキップ。
- データベース連携
  - 初期化関数 init_monitoring_db 呼び出しにより監視用テーブルを冪等に準備（run_monitoring/run_execution で利用）。
  - DuckDB 接続を用いた分析用 DB（duckdb_path）と SQLite（monitoring / paper_trading）を併用する設計。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs などのテーブルから稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を算出し、Pass/Fail 判定（閾値はソース内で定義）を行う。--from/--to/--db オプションをサポート。
- 研究用モジュール（骨組み）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、MA、ATR、流動性等の計算仕様・定数を定義）。（実装の続きあり）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- position_sizing の TODO: 価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨の注記あり。
- run_monitoring は監視データを本番 sqlite_path に書き込むため、開発環境での実行時は注意が必要。
- .env は絶対に Git にコミットしない旨を config_setup に明記。
- research/factor_research.py はファイル末尾で実装が途中で切れている（更なる実装・テストが必要）。

Acknowledgements
- 本リリースは初期実装のため、ユニットテストや追加の例外処理、細かい堅牢化（外部 API エラーリトライ、DB トランザクション管理等）が今後の改善候補です。