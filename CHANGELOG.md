# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
バージョンはパッケージ内の __version__ = "0.1.0" に基づき初期リリースとして記録しています。

## [0.1.0] - 2026-04-22

### Added
- 実行用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。プロセス優先度を高く設定して実行。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と分離して動作。
    - 停止制御: data/stop_requested.flag をチェックし、検出時にエンジンを停止。
    - 実行中は execution.pid を使用（PID ファイル機能）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - RiskManager のデフォルト設定を定義（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker_*、max_drawdown、initial_portfolio_value など）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず production の sqlite_path を使用する設計。
    - 停止制御: data/stop_requested.flag を検出するとループを終了。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env/.env.local の読み込み順序管理（OS 環境変数を保護）。
    - 高度な .env パーサ実装（export プレフィックス、引用符内バックスラッシュエスケープ、インラインコメント許容）。
    - Settings クラスを導入し、各種設定値（DB パス・API トークン・監視閾値・ログ設定など）をプロパティで提供。
    - PAPER_FILL_MODE（instant/partial/never/reject）などペーパートレード向け設定検証。
    - KABUSYS_ENV 値チェック（development/paper_trading/live）や LOG_LEVEL 検証。
  - config_setup.py: 対話式 .env 作成ウィザード（項目定義、既存 .env 読み込み、保存機能）。
  - validate_config.py: 設定検証 CLI（必須環境変数チェック、パス存在チェック、config/*.yaml の確認、KABUSYS_ENV=live 時の追加ガード）。--strict オプションで警告を FAIL 扱いに可能。

- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N 件を選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重。全スコアが 0 の場合は等配分にフォールバックし警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を元にセクター別エクスポージャ計算、超過セクターの候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。未知レジームは警告して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）スケーリング、cost_buffer を考慮した安全なスケーリングロジックを実装。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティ。stdout StreamHandler と TimedRotatingFileHandler（日次・30 日保持）をルートロガーへ設定。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
    - stdout を使用することで cron/スケジューラ実行時の扱いを考慮。
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティ（Windows / POSIX 差分吸収、権限不足等は警告してスキップ）。

- 分析/ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプト。SQLite の paper_trading DB（PAPER_TRADING_SQLITE_PATH）を読み、稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を算出して PASS/FAIL を判定する。
    - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ指定（--from/--to）に対応。

- research/factor_research.py：DuckDB 接続を受けて各種ファクター（Momentum / Value / Volatility / Liquidity）を計算するモジュール骨格を追加（prices_daily / raw_financials テーブル参照想定）。
  - （注）このファイルは途中で切れている箇所があり、実装が未完（WIP）の箇所あり。

### Changed
- ログの振る舞いを統一
  - すべての起動スクリプトは setup_logging を呼び出し、ログ出力は stdout とローテートファイルを併用する方針に統一。
- .env 読み込みルールの明確化
  - OS 環境変数を優先し、.env / .env.local のロード順・上書きルールをドキュメント化。
- run_monitoring の挙動
  - 監視は常に Settings.sqlite_path（本番用）を使用する設計になっていることを明記（paper_trading とは分離しない）。

### Fixed
- 環境変数パースの改善
  - .env パーサで export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの処理を強化。これにより特殊文字や引用を含むトークンが正しく読み込めるようになった。
- プロセス優先度 / CPU affinity のエラー処理を強化
  - 実行環境によっては特権不足や未サポート API が発生するため、例外を捕捉して警告に落とすように変更。これにより起動時の致命的失敗を抑制。

### Deprecated
- 特になし（初期リリース）

### Removed
- 特になし（初期リリース）

### Security
- 秘匿情報取り扱い
  - config_setup の出力ではシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_CHANNEL_ACCESS_TOKEN）はマスク表示される。README 等で .env を Git にコミットしない旨を明記。

### Notes / Known issues
- research/factor_research.py は途中で実装が途切れている（ファイル末尾に不完全な行が存在）。本モジュールは現状で未完のため、使用時は注意が必要。
- position_sizing の保守的見積りにおいて、open_prices に 0.0（欠損）がある場合はエクスポージャが過少見積りされる旨の TODO コメントあり。将来的に前日終値や取得原価によるフォールバックを検討する必要あり。
- apply_sector_cap は "unknown" セクターを除外せず上限適用しない仕様（ドメイン上の判断）。必要に応じて取り扱いを変更可能。
- validate_config は PyYAML がインストールされていない場合 YAML 検証をスキップして警告を出す。

----

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートとして公開する場合は、差分管理履歴（Git コミットメッセージ等）やプロジェクトのリリースポリシーに合わせて調整してください。