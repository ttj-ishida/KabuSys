# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
※日付はリリース日です。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 全体
  - 初回リリース。日本株自動売買フレームワーク「KabuSys」の基本コンポーネントを実装。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 起動 / 実行
  - run_monitoring.py: SystemMonitor を定期的にポーリングする監視ループの起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知による安全な終了処理を実装。
    - 監視は環境にかかわらず本番用の SQLite パスを使用する仕様（Settings の sqlite_path）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に完全分離して記録。
    - PID ファイル管理、停止フラグ検知、スレッド実行によるセッション管理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込み。

- 設定管理 / CLI
  - config.py: Settings クラスを実装。環境変数から各種設定値を取得・検証するプロパティを提供（DB パス、API トークン、PAPER_FILL_MODE、KABUSYS_ENV 等）。
  - config_setup.py: 対話式ウィザードにより .env ファイルを初期作成/更新する CLI を追加。項目定義とテンプレート書き出しを実装。
  - validate_config.py: .env と config/*.yaml の設定検証 CLI を追加。必須環境変数チェック、パス確認、YAML の存在/パース検証（PyYAML 有無に応じて）や本番環境向けのガードチェックを提供。

- ユーティリティ
  - utils/process_priority.py:
    - カレントプロセスの優先度（Windows / POSIX の差分吸収）を設定する `set_process_priority(level)` を実装。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装。
    - 権限やプラットフォーム未対応時にログで警告して安全にフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 `select_candidates`、等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中上限の適用 `apply_sector_cap`、市場レジームに応じた乗数 `calc_regime_multiplier` を実装。
  - portfolio/position_sizing.py:
    - 発注株数計算 `calc_position_sizes` を実装。allocation_method（risk_based / equal / score）、lot_size 丸め、max_position_pct / max_utilization、cost_buffer に基づく aggregate cap とスケーリングロジックを実装。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - DuckDB を用いたファクター計算（モメンタム、ボラティリティ等）を実装。`calc_momentum` / `calc_volatility` により prices_daily 等のテーブルを参照してファクターを算出。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を出力。
    - デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

### 変更 (Changed)
- .env 自動ロード
  - プロジェクトルートを .git / pyproject.toml から探索して自動的に .env / .env.local を読み込む仕組みを導入。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ロード時には既存 OS 環境変数を保護するための protected キーセットを利用。

- .env パーサ
  - export KEY=val 形式、クォートされた値（シングル/ダブル、バックスラッシュエスケープ対応）、インラインコメントの扱いなどをサポートする堅牢なパーサを実装。

- Settings のバリデーション
  - `PAPER_FILL_MODE` の有効値チェック（instant / partial / never / reject）を追加。無効値は ValueError。
  - `KABUSYS_ENV`、`LOG_LEVEL` の許容値チェックを実装（不正値は ValueError）。
  - is_live / is_paper / is_dev の便宜プロパティを追加。

- run_monitoring.py
  - 無効な MONITOR_POLL_INTERVAL の値（0 以下や非整数）を検出してデフォルトにフォールバックし、警告ログを出すように変更。
  - check_once() 実行中の例外を捕捉してログ出力し、ループを継続する堅牢化。

- run_execution.py
  - paper_trading モード時に paper_trading 用 SQLite を使用するよう分離。
  - RiskManager の既定設定（max_position_pct, max_utilization 等）を導入し、初期ポートフォリオ値は broker.get_available_cash() から取得。

- ポートフォリオ / 配分ロジック
  - `calc_score_weights` は全スコアが 0 の場合に等金額配分へフォールバックして警告を出すように変更。
  - `apply_sector_cap` は "unknown" セクターを上限適用外とし、当日売却予定銘柄をエクスポージャ計算から除外する挙動を追加。
  - `calc_position_sizes` の aggregate スケーリングにおける残余ロジックを改善し、lot_size 単位での追加配分を公平に行う処理を追加。

- utils/process_priority.py
  - Windows と POSIX の差分を吸収する実装にし、未対応 OS や権限不足時には警告を出してスキップするように変更。

- validate_config.py
  - PyYAML の有無を検出し、YAML が使えない場合はパース検証をスキップして警告を出す挙動を追加。
  - 本番環境（KABUSYS_ENV=live）向けの追加チェック（LINE トークン、KILL_FLAG_CLEAR_ON_START）を強化。

### 修正 (Fixed)
- 起動時のプロセス優先度設定で権限不足や未対応プラットフォームにより例外が発生した場合、例外を捕捉して警告ログを出すようにしてクラッシュを防止。
- .env 読み込みでファイルアクセスエラーが発生した場合に警告を出してスキップする安全ハンドリングを追加。
- Paper verification レポートの各クエリで必要テーブルや列が存在しない（OperationalError）場合に個別にフォールバックし、レポート全体が失敗しないように修正。

### 廃止 (Deprecated)
- なし

### セキュリティ (Security)
- なし

Notes:
- 多くのモジュールは「副作用なし（純粋関数）」で設計されており、単体テストや差分検証が容易です（portfolio/*, research/* など）。
- 今後の改善候補として、銘柄ごとの lot_size をマスタで管理する拡張や、価格取得のフォールバック（前日終値など）を検討するための TODO コメントをコード内に残しています。