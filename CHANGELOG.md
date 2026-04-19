# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠します。  

注: コードベースから推測して作成した CHANGELOG です。実際の変更履歴やリリース日付は適宜調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期実装を追加
  - パッケージ情報: kabusys/__init__.py にバージョン 0.1.0 を設定。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離する挙動を実装。
    - BrokerClientFactory 経由でブローカークライアントを作成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンをスレッドで実行。停止フラグ（data/stop_requested.flag）検出時に安全に停止。
    - PID ファイル（data/execution.pid）管理。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に保存）。
    - 停止フラグ検出時にループを終了し、例外発生時も次のポーリングまで待機する堅牢化処理。
- 設定管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルート自動検出: .git または pyproject.toml）。
    - .env のパースロジックを実装（export 付き行、シングル/ダブルクォート、インラインコメントの取り扱い等をサポート）。
    - 環境変数取得用 Settings クラスを実装（各種プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - 設定値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）と便利な is_live/is_paper/is_dev プロパティを提供。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - config_setup.py
    - 対話式 .env 作成・更新ウィザードを追加。既存 .env 読込、シークレットマスク、選択肢、保存確認をサポート。
    - .env 書き込みテンプレートには注意書きを付与（.env を Git にコミットしない旨）。
  - validate_config.py
    - 起動前検証用 CLI を追加。必須環境変数やパス、config/*.yaml の存在・YAML パース（PyYAML が無い場合はスキップ）をチェック。
    - --strict オプションで警告を FAIL 扱いにできる。
- ログ設定ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。root ロガーを統一設定（stdout StreamHandler と TimedRotatingFileHandler（1日ローテーション、30日保持）を追加）。
    - ログディレクトリを自動作成（失敗時はファイル出力を無効化して stdout のみで継続）。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）。
- プロセス優先度 / CPU affinity ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（Windows / POSIX の差分を吸収）。失敗時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装（指定コア数にピン留め、未対応/権限不足時はスキップ）。
- Portfolio 構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates()、等分配 calc_equal_weights()、スコア加重 calc_score_weights() を実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中上限チェック（既存ポジション時価を元に除外判定、"unknown" セクターは除外しない）。
    - calc_regime_multiplier(): 市場レジームに応じた乗数（bull/neutral/bear）を実装（未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に対応した株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金に合わせてスケールダウン）を考慮。
    - cost_buffer を使った保守的コスト見積もり、端数処理（再配分アルゴリズム）を実装。
    - 将来的な拡張点（銘柄別 lot_size の導入）を TODO コメントで記載。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計し、PASS/FAIL 判定を出力するレポート生成スクリプトを追加。
    - P95 計算、日付フィルタ、DB 存在チェック、エラーハンドリングを実装。
    - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）を定義。
- Research
  - research/factor_research.py
    - ファクター計算モジュール（モメンタム／バリュー／ボラティリティ／流動性）用の設計と一部実装（定数、calc_momentum の冒頭）を追加。DuckDB を用いた prices_daily/raw_financials 参照を前提。
- パッケージエクスポート
  - portfolio パッケージ __all__ を統一して主要関数をエクスポート。

### Changed
- ログ出力ポリシー
  - ロガーの StreamHandler は stdout を使用するよう明示（cron/Task Scheduler 等でのリダイレクト性を向上）。
- DB 初期化
  - run_execution/run_monitoring 共に init_monitoring_db(sqlite_conn) を呼び出して監視テーブルが存在することを保証（冪等）。

### Fixed
- 環境変数パースの頑健性向上
  - .env パーサで export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの扱い等を改善して実運用での .env 設定をより安定化。

### Notes / Known issues / TODO
- research/factor_research.py は途中でファイルが切れている（calc_momentum 実装の続きが必要）。実際のファクター計算ロジックは未完。
- apply_sector_cap():
  - price_map に価格が欠損（0.0）の場合、TODO コメントでフォールバック価格（前日終値など）導入検討を示している。現在は過少見積りのリスクあり。
- calc_score_weights():
  - 全銘柄スコアが 0.0 の場合は等金額配分にフォールバックし、WARNING を記録。
- calc_position_sizes():
  - 将来の拡張として銘柄別 lot_size を導入予定（現在は全銘柄同一 lot_size 想定）。
- run_monitoring:
  - 監視は常に本番 sqlite_path を使用する設計のため、環境設定ミスに注意（監視 DB を分離したい場合は設定やコードの変更が必要）。
- 権限や環境によっては process priority / cpu affinity の設定が失敗することがある（警告を出してスキップする実装）。

---

履歴の補足:
- この CHANGELOG はコードベースの現状から「初期公開相当の 0.1.0 リリース」を想定して作成しています。実際の開発履歴や日付、リリース番号はプロジェクト運用に合わせて更新してください。