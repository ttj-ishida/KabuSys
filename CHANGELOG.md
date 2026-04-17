# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

※このCHANGELOGは与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回リリース。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト / デーモン類
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を検知してループを終了。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
    - SQLite と DuckDB 接続を確立し、監視用 DB 初期化を呼び出す。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite（data/paper_trading.db または環境変数指定）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler など必要コンポーネントを組み立て、ExecutionEngine を別スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）検知時に Engine.stop() を呼び出して安全に終了。
    - 実行 PID を data/execution.pid に保存する想定（pid_file 引数）。

- 設定と環境変数管理
  - config.py:
    - .env/.env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースは export 形式やクォート、バックスラッシュエスケープ、インラインコメント（クォートなしで直前が空白の `#`）を考慮して堅牢に実装。
    - Settings クラスを提供し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等のプロパティを環境変数から取得するユーティリティを実装。
    - PAPER_FILL_MODE の有効値検証（"instant" | "partial" | "never" | "reject"）や、PAPER_TRADING_SQLITE_PATH 等のデフォルトパスをサポート。
    - env 値（KABUSYS_ENV）や LOG_LEVEL の検証を行い、不正な値は例外を送出。

  - config_setup.py:
    - 対話式ウィザードで .env ファイルを生成/更新する CLI を実装（python -m kabusys.config_setup）。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE の設定等）を対話的に入力し .env を書き出す機能。
    - 既存 .env 読み込み、シークレット値マスク表示、デフォルト提示、キャンセル処理等に対応。

  - validate_config.py:
    - 起動前の設定検証 CLI を実装（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）など。
    - --strict オプションで警告も失敗扱い（exit(1)）にできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）で選択する実装。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし警告）。

  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有比率に基づくセクター上限（max_sector_pct）適用。売却予定銘柄はエクスポージャー計算から除外。unknown セクターは適用対象外。
    - calc_regime_multiplier: market レジーム（"bull","neutral","bear"）に対する投下資金乗数を返却。未知レジームはフォールバックして 1.0。

  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じた株数算出を実装（"risk_based", "equal", "score"）。
    - risk_based: risk_pct, stop_loss_pct を使ってポジションサイズ計算。
    - equal/score: weight ベースの配分、max_position_pct による per-stock 上限、lot_size（単元）で丸め。
    - aggregate cap: 全銘柄合計が available_cash を超える場合のスケーリング、cost_buffer を考慮した保守的見積り、残差分の lot_size 単位での追加配分などを実装。
    - lot_size 固定（デフォルト 100）を想定し将来の拡張（銘柄別単元）に注意書きあり。

- 監視 / 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を SQLite のテーブル（system_status, trade_logs, risk_logs）から集計してレポート出力。閾値（例: 稼働率 >= 99%）に基づく PASS/FAIL 判定を実装。
    - P95 計算、日付フィルタの ISO8601 変換、DB ファイル存在チェックに対応。

- 研究用ファクター計算
  - research/factor_research.py:
    - DuckDB 接続を受け取り、prices_daily などを参照して Momentum / Volatility 等のファクター計算関数を実装（calc_momentum, calc_volatility 等の設計と SQL 実装の一部）。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR、平均売買代金、出来高比率等を計算。ウィンドウ不足時は None を返す設計。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows と POSIX 系（Linux, Darwin, FreeBSD）の差を吸収して優先度（high/normal/low）を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を追加（最初の N コアに固定、エラー時は警告を出してスキップ）。

### 変更 (Changed)
- なし（初回リリースのため過去の変更はありません）

### 修正 (Fixed)
- なし（初回リリース）

### 注意事項 / 備考
- .env は絶対に Git にコミットしない旨の注記が config_setup の出力に含まれています。
- monitoring 部分は実行環境の KABUSYS_ENV にかかわらず本番の sqlite_path を使う仕様になっているため、テスト時に意図せず本番 DB を操作しないよう環境やパス設定に注意が必要です（run_execution は paper_trading 環境時に専用 DB を使用する）。
- config の自動ロードはプロジェクトルートが特定できない場合はスキップされます。テスト環境などで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- PAPER_FILL_MODE の不正な値や KABUSYS_ENV / LOG_LEVEL の不正値は Settings プロパティで例外を投げるため、起動前に validate_config での確認を推奨します。
- position_sizing の計算には lot_size の関係上、price が欠損（0.0）だと算出がスキップされたりエクスポージャー過小評価になる旨の TODO コメントがあります。価格欠損時のフォールバック処理は将来の改善点です。

---

（このCHANGELOGは手元のソースから推測して作成しています。実際の変更履歴と差異がある場合は適宜更新してください。）