# CHANGELOG

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。重要な変更点・追加機能を日本語で記載しています。

全般的な注意:
- バージョンはパッケージの __version__ に合わせて v0.1.0 としています。
- 記載はソースコードの内容から推測してまとめています（実装の説明やデフォルト値を含みます）。

## [Unreleased]

## [0.1.0] - 2026-04-17
Added
- 初期リリースを追加。
- CLI / ツール
  - config_setup: 対話式ウィザードで .env を作成・更新する CLI を追加（python -m kabusys.config_setup）。項目定義、既存 .env 読み込み、保存機能を提供。
  - validate_config: 起動前に環境変数・設定ファイルを検証する CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス存在確認、config/*.yaml のパース検証（PyYAML 利用可）および本番環境向けの保護チェックを実施。--strict オプションで警告も失敗と扱う。
  - tools.paper_verification_report: ペーパートレード用 SQLite DB から集計レポートを出力するツールを追加（python -m kabusys.tools.paper_verification_report）。期間フィルタ、P95 レイテンシ等を算出し、PASS/FAIL 判定を行う。
- 実行系エントリポイント
  - run_execution: ExecutionEngine を起動するスクリプトを追加。プロセス優先度を「high」に設定して起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）に完全分離して記録する。エンジンはバックグラウンドスレッドで run_session を実行し、data/stop_requested.flag に応答して安全に停止する。PID ファイル出力先の指定あり。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境にかかわらず本番 sqlite_path（data/monitoring.db 等のデフォルト）を使用し、停止フラグファイルでループを終了する。
- 設定関連
  - config.Settings: 環境変数アクセスをラップする Settings クラスを追加。J-Quants / kabu / LINE / DB パス / 監視閾値 / システムフラグ等をプロパティで提供。KABUSYS_ENV の検証や PAPER_FILL_MODE のバリデーション等を実装。is_live / is_paper / is_dev 等のヘルパーも提供。
  - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を自動読み込み。OS 環境変数は保護（上書き禁止）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - .env パーサ: export KEY=val、クォート／エスケープ、インラインコメントの解釈などに対応する堅牢なパース処理を実装。
- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア全てが 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数を返す calc_regime_multiplier を実装。regime に応じたデフォルト乗数（bull:1.0, neutral:0.7, bear:0.3）。未知レジームは 1.0 にフォールバックして警告。
  - portfolio.position_sizing: 各銘柄の発注株数を計算する calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。単元株（lot_size）、リスクパラメータ（risk_pct, stop_loss_pct）、最大ポジション比率、投下資金上限（max_utilization）、cost_buffer による保守的見積り、aggregate cap によるスケーリングと残差のロット単位再配分を含む。
- リサーチ / ファクター計算
  - research.factor_research: DuckDB 接続を受け取り prices_daily 等のテーブルからファクターを計算するモジュールを追加。以下を実装:
    - calc_momentum: mom_1m / mom_3m / mom_6m と 200 日移動平均乖離 ma200_dev を計算。ウィンドウ内データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率等を計算（true_range の NULL 伝播を厳密に扱う）。
  - 設計方針として DuckDB と prices_daily / raw_financials のみを参照し、外部 API にはアクセスしない。
- ユーティリティ
  - utils.process_priority: cross-platform（Windows / POSIX）でプロセス優先度と CPU affinity を扱うユーティリティを追加。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限や未対応プラットフォーム時は警告を出して安全にスキップ。
- 監視データベース初期化
  - monitoring.monitoring_db.init_monitoring_db を run_execution/run_monitoring 側で呼び出し、監視テーブルが存在することを保証（冪等的）。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 補足
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
- 実行スクリプトは stop_requested.flag（data/stop_requested.flag）や execution.pid 等のファイルでプロセス制御を行う設計になっており、安全シャットダウンに対応しています。
- paper_trading 環境では本番 DB と完全分離するよう設計されています（MockBrokerClient + 専用 SQLite）。
- MONITOR_POLL_INTERVAL は環境変数で監視ポーリング間隔を上書きできます（不正な値はデフォルト 60 秒にフォールバック）。
- .env の自動読み込みはプロジェクトルート検出に成功した場合のみ行われます。プロジェクトルート検出は __file__ から親ディレクトリを探索して .git または pyproject.toml を探す方式です。

開発／運用者向け推奨
- 本番環境（KABUSYS_ENV=live）では validate_config を実行して各種警告・設定を確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きあり）。
- process priority / cpu affinity の設定は権限によっては失敗するため、ログの警告を確認してください。

--- 

（以降のリリースでは、本 CHANGELOG を更新し、Added / Changed / Fixed を明示してください。）