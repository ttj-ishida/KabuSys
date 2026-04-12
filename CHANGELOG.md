# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在の日付: 2026-04-12

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-12
初回リリース。

### Added
- 全体
  - パッケージ初版を追加。パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージ初期化情報（src/kabusys/__init__.py）を追加。

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセス起動時にプロセス優先度を "high" に設定。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録。
    - sqlite3 / duckdb 接続と初期化（init_monitoring_db）を行い、例外時はログを残してループ継続するフェイルセーフ実装。

  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）へ記録して本番 DB と分離。
    - プロセス優先度を "high" に設定。
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立ててセッションを実行。

- 設定管理
  - config.py:
    - .env 自動読み込み機能を追加（プロジェクトルートの .env と .env.local を読み込む。OS 環境変数を優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - .env パースの細かい取り扱いを実装（export プレフィクス、クォート内エスケープ、インラインコメント規則など）。
    - Settings クラスを導入し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供。
    - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の値検証を実装（不正値は ValueError を送出）。
    - 各種デフォルト（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等）を明示。

- モジュール: portfolio
  - portfolio_builder.py:
    - select_candidates: BUY シグナルのスコアソートと上位 N 選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア正規化による重み計算（全スコア 0 の場合は等金額へフォールバック）。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック。既存保有を元に上限超過セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - position_sizing.py:
    - calc_position_sizes: 各銘柄の発注株数算出。allocation_method("risk_based" / "equal" / "score")、ロット丸め、per-position 上限、aggregate cap とスケーリング（cost_buffer を考慮）、残差処理（lot 単位での追加配分）を実装。

- ユーティリティ
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティ（権限不足や未対応 OS は警告ログ）。
    - set_cpu_affinity: カレントプロセスの CPU affinity を最初の N コアに固定するユーティリティ（引数チェック、権限エラー処理あり）。

- Research
  - research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を参照するファクター計算を実装（1M/3M/6M リターン、MA200 乖離、ATR、平均売買代金、PER/ROE 等）。
  - research/feature_exploration.py:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算。
    - calc_ic: スピアマンランク相関（IC）計算（欠損やデータ不足時の安全処理）。
    - factor_summary, rank: 基本統計量とランク付けユーティリティ。
  - research パッケージで zscore_normalize（kabusys.data.stats）を再公開。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポートを生成する CLI ツールを追加。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - --from / --to / --db オプションをサポート。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値を用いた PASS/FAIL 判定（閾値はソース内で定義）。
    - DB のテーブル欠損時に安全に N/A を表示する実装。

- AI
  - ai/news_nlp.py:
    - OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング機能を追加。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST -> UTC に変換）・記事集約・バッチ（最大 20 コード / チャンク）での API 呼び出し実装。
    - 429/ネットワーク断/5xx に対する指数的バックオフのリトライ方針、レスポンス検証、スコアクリッピング（±1.0）、ai_scores テーブルへの安全な更新戦略（部分失敗時に既存スコアを保護）を設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- config._parse_env_line にてクォート内のバックスラッシュエスケープやインラインコメント処理を改善し、.env パースの堅牢性を向上。
- paper_verification_report: DB テーブルが存在しない場合でも例外を吸収して N/A を返すフォールバックを実装。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー未設定時に明確なエラー（ValueError）を送出し、キーの未設定で誤動作しないように保護。
- .env 自動読み込み時に OS 環境変数を保護（.env.local でも OS 環境変数の上書きを防ぐ保護リストを導入）。

---

注意事項 / 既知の設計上メモ
- run_monitoring は「監視」目的のため KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計となっており、テスト環境での誤使用に注意が必要です（これは意図的な設計）。  
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過小評価される点は TODO コメントで言及されており、将来的にフォールバック価格（前日終値等）の導入を検討する必要があります。  
- position_sizing.calc_position_sizes は現状すべての銘柄で単一の lot_size（デフォルト 100）を使用する設計。将来的に銘柄別 lot_size を受け取る拡張が想定されている。  
- research と ai モジュールは DuckDB テーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等）を前提としているため、該当テーブルが存在しない場合は一部機能がデグレードします（レポートツールではその場合 N/A 表示）。  

この CHANGELOG はコードベースのソース記載内容から推測して作成しています。実際のリリースノートや運用ルールに合わせて必要に応じて修正してください。