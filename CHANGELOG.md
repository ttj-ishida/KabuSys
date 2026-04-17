# Changelog

すべての注目すべき変更はこのファイルで管理します。フォーマットは Keep a Changelog に準拠します。

全般方針: ここにはコードベースから推測できる「追加された機能」「改善点」「挙動上の注意点」を記載しています。

## [0.1.0] - 2026-04-17

### Added
- パッケージ初期リリース（KabuSys 自動売買システム、バージョン 0.1.0）。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下や不正値は警告を出してデフォルトにフォールバック。
    - 停止管理: プロジェクトルート/data/stop_requested.flag によりループを終了。
    - 監視は KABUSYS_ENV に関係なく本番の sqlite_path を使用して初期化（監視テーブルを保証）。
    - 起動直後にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によりブローカークライアントを生成（paper/live に応じて Mock/実ブローカー）。
    - エンジンの PID 管理、停止フラグの検出による安全停止処理を実装。
    - 起動直後にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート判定ロジック: .git か pyproject.toml を探索）。
    - .env / .env.local の読み込み順序（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 環境変数パースの詳細な実装（export 形式、クォート内エスケープ、インラインコメント扱い等）。
    - Settings クラスを導入し、アプリケーション設定をプロパティ経由で取得できるようにした（多くの設定項目をプロパティ化: J-Quants / kabu / LINE / DB / 監視閾値 / system）。
    - PAPER_FILL_MODE の検証（有効値: instant|partial|never|reject）やパスの expanduser 対応などのバリデーションを実装。
    - KABUSYS_ENV の許容値検証 (development, paper_trading, live)。

- 設定補助ツール
  - config_setup.py
    - .env の対話式ウィザードを追加。よく使う設定項目を対話で作成・更新できる。
    - 既存 .env の読み込みとマスク表示（シークレット項目は ****）を提供。
    - 保存前に確認プロンプト、.env を上書きして書き出す機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリチェック、YAML ファイルの存在/パースチェック（PyYAML がない場合はパースチェックをスキップして警告）。
    - KABUSYS_ENV=live の場合に注意喚起（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）。
    - --strict オプションにより警告も失敗扱いにできる。

- 監視 / ペーパートレード検証
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite (デフォルト: data/paper_trading.db) から各種指標を集計し、検証レポートを生成する CLI を追加。
    - 集計指標: システム稼働率（system_status）、注文成功率/送信率（trade_logs）、リスク却下数（risk_logs）、API レイテンシ（平均・最大・P95）。
    - P95 近似実装、期間フィルタ (--from / --to)、DB パス override (--db) をサポート。
    - 合否判定の閾値を導入（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等ウエイト / スコア重み算出 (calc_equal_weights, calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap 実装（既存保有のセクター別時価計算、売却予定銘柄の除外、"unknown" セクターは制限対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier 実装（bull=1.0, neutral=0.7, bear=0.3、未知レジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数計算 calc_position_sizes 実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer による保守的な見積り、aggregate cap によるスケールダウン処理、端数配分ロジックを実装。
    - 価格欠損時のスキップやログ記録など堅牢性を考慮。

- 研究用モジュール
  - research/factor_research.py
    - DuckDB を用いた因子（Momentum / Volatility / Liquidity / Value 等）の計算実装（prices_daily / raw_financials テーブル参照）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率。データ不足時は None。
    - ボラティリティ等: ATR、平均売買代金、出来高比率等の計算ロジック（ウィンドウ幅・スキャン幅は定数化）。
    - 全関数は DuckDB 接続を受け取りスケーラブルに SQL を実行する設計。

- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を考慮した nice/HIGH_PRIORITY_CLASS の設定。
    - set_cpu_affinity を追加し、最初の N コアにプロセスをピン留め可能（権限不足や未対応環境では警告を出してスキップ）。
    - psutil の例外（AccessDenied 等）を捕捉して安全にフォールバック。

### Changed
- 初版 (0.1.0) のため、既存プロジェクトへの導入・統合を想定した実装が含まれる（設定 / DB パス / .env 自動ロード等の挙動に注意）。

### Notes / Migration / Usage
- .env 自動読み込みはデフォルトで有効。テストや特殊環境で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番起動時は KABUSYS_ENV を必ず確認してください（許容値: development, paper_trading, live）。live では特に LINE 通知設定や Kill Switch の扱いに注意が必要です。
- run_monitoring は監視データ用の sqlite_path を常に使用します（env に依存しない）。一方 run_execution は paper_trading 環境で paper_sqlite_path を使用して DB を分離します。
- MONITOR_POLL_INTERVAL は整数秒（1 以上）を指定してください。不正値や 0/負値はデフォルト 60 秒にフォールバックします。
- PAPER_FILL_MODE の値は instant|partial|never|reject のいずれかである必要があります。不正値は ValueError を発生させます。
- process priority / cpu affinity の設定は環境（OS・権限）に依存し、失敗した場合は警告をログ出力してスキップします。
- Paper Trading 検証レポートはデータ構造（system_status, trade_logs, risk_logs テーブル）に依存します。DB スキーマが異なる場合はレポート生成が失敗する可能性があります。

---

（この CHANGELOG はコードから推測して作成したものであり、実際のコミット履歴とは異なる場合があります。問題や追加の注記があればお知らせください。）