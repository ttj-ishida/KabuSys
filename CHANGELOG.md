# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
バージョン番号はパッケージ内部の __version__ に合わせています。

## [0.1.0] - 2026-04-24

### Added
- 初期リリース: KabuSys のコア機能群を実装。
  - 実行スクリプト
    - run_execution.py
      - ExecutionEngine 起動用エントリポイントを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path（既定: data/paper_trading.db）を使用し、本番 DB と分離して MockBrokerClient を利用する設計を採用。
      - 停止制御: data/stop_requested.flag を監視して安全に停止。起動時 pid ファイル (data/execution.pid) を扱う。
      - デフォルトでプロセス優先度を "high" に設定。
      - ExecutionEngine に渡す RiskManager のデフォルト設定を実装（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）。
    - run_monitoring.py
      - SystemMonitor 用ポーリングループを追加。
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視プロセスは環境に関わらず本番の sqlite_path を使用する設計。
      - 停止フラグ (data/stop_requested.flag) の検知でループ終了。
      - プロセス優先度を "high" に設定。
  - 設定・環境管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルートを .git や pyproject.toml で探索）。
      - .env / .env.local の読み込み順（OS環境 > .env.local > .env）と protected （OS 環境変数を上書き禁止）をサポート。
      - .env パースの強化: export プレフィックス・クォート・エスケープ・インラインコメントに対応。
      - 各種プロパティを提供（J-Quants, kabu API, LINE, DuckDB/SQLite パス, Paper Trading モード, 監視閾値等）。PAPER_FILL_MODE の妥当性チェックを実装（instant/partial/never/reject）。
    - config_setup.py
      - 対話式 .env 作成ウィザードを実装。既存 .env の読み込み・マスク表示・デフォルト利用・保存機能を提供。
      - 出力テンプレートで .env のサンプルを整形して保存。
    - validate_config.py
      - 起動前の設定検証 CLI を実装。必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ確認、config/*.yaml の存在・パース検査（PyYAML がある場合）。
      - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
      - --strict オプションで警告も失敗扱いにできる。
  - ロギング・プロセスユーティリティ
    - utils/logging_setup.py
      - 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）のファイル出力をサポート。
      - ログディレクトリ作成に失敗した場合はファイル出力を無効化して標準出力のみで継続。
      - ログレベル・ログディレクトリの優先解決順を実装（引数 > 環境変数 > デフォルト）。
    - utils/process_priority.py
      - クロスプラットフォームでプロセス優先度（high/normal/low）を設定するユーティリティを追加（Windows/Linux/macOS の違いを吸収）。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
      - アクセス権限エラー等を安全にハンドリング（警告出力してスキップ）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - select_candidates: スコア降順で候補選定（同点は signal_rank でタイブレーク）。
      - calc_equal_weights: 等金額配分を実装。
      - calc_score_weights: スコア加重配分を実装。全スコアが 0 の場合は等金額配分にフォールバックして警告。
    - portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限（max_sector_pct）に基づく候補フィルタリング。unknown セクターは適用除外。売却予定銘柄は exposure 計算から除外。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を実装（未知レジームは 1.0 でフォールバック）。
    - portfolio/position_sizing.py
      - calc_position_sizes: allocation_method により株数算出（"risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率、stop_loss_pct に基づく算出。
      - weight ベース配分では max_utilization・max_position_pct に従った上限処理を実装。
      - lot_size（既定 100）に基づく丸め、cost_buffer を考慮した保守的見積り、aggregate cap 超過時のスケールダウンと残差配分ロジックを実装。
  - 解析・リサーチ
    - research/factor_research.py（モジュール開始）
      - モメンタム等のファクター計算用ユーティリティの枠組みを実装（DuckDB 経由で prices_daily / raw_financials を参照）。計算窓や定数を定義（1M/3M/6M、MA200、ATR20 等）。
      - calc_momentum 関数の実装を開始（ファイル途中まで）。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツールを実装。SQLite （デフォルト: data/paper_trading.db）からデータを集約して稼働率・注文成功率・送信率・レイテンシ（P95）などを計算。
      - Pass/Fail の閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
      - 日付範囲フィルタ（--from/--to）や --db オプションをサポート。
  - パッケージメタ情報
    - kabusys/__init__.py に __version__ = "0.1.0" を設定。

### Changed
- N/A（初回リリースのためなし）

### Fixed
- N/A（初回リリースのためなし）

### Known limitations / Notes
- research/factor_research.calc_momentum はファイル末尾が途中で切れている（実装継続の余地あり）。
- 一部の DB / monitoring 周りの初期化（monitoring_db など）は本 CHANGELOG 対象ファイルで参照されているが詳細実装は別ファイルに分離されている。
- position_sizing の price 欠損時の挙動に TODO コメントあり（価格欠損時に exposure が過少見積りされる可能性）。
- プラットフォーム依存の操作（プロセス優先度設定・CPU affinity）は権限によって失敗する可能性があり、その場合は警告を出して処理を継続する設計。

---

今後の予定（短期）
- factor_research の完成（ファクター算出の SQL / 正規化処理の実装）。
- monitoring_db の詳細レビュー・追加メトリクス。
- テストカバレッジを追加して CLI /ウィザード / position sizing の挙動を厳密に検証。