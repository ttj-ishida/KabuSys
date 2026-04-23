# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、以下はコードベースから推測して作成した初期リリースの変更履歴です（推測に基づく説明を含みます）。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - パッケージ初期リリース。バージョンは `kabusys.__version__ = "0.1.0"` に設定。

- 実行・監視スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用してペーパートレード専用 DB（デフォルト: data/paper_trading.db）に分離して記録する振る舞いをサポート（BrokerClientFactory により実体を生成）。
    - プロセス優先度を最初に "high" に設定する仕組みを組み込み（utils.process_priority）。
    - SQLite（本番または paper_trading 用）と DuckDB への接続確立と監視テーブル初期化を実施。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag を監視して安全に停止する制御を実装。
    - 起動時の PID を data/execution.pid に記録する仕組み（pid_file パスの注入）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。例外発生時は例外ログを残して次のポーリングまで継続。

- 設定管理
  - config.py
    - 環境変数・.env 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
    - .env パーサは `export KEY=val`、クォート、バックスラッシュエスケープ、コメント処理等に対応。
    - Settings クラスを提供。J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定などのプロパティを提供し、バリデーションを実施（例: KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の有効値検証など）。
    - settings = Settings() をモジュールレベルでエクスポート。

  - config_setup.py
    - インタラクティブな .env 作成ウィザードを追加。既存 .env を読み込み、対話式に編集・保存できる。
    - 保存時に .env に書き出すテンプレートを提供（機密項目はマスク表示）。

  - validate_config.py
    - 起動前チェック用 CLI を追加（python -m kabusys.validate_config）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パス親ディレクトリ存在チェック、config/*.yaml の存在と YAML パース（PyYAML がある場合）などを実行。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定と重み計算の純粋関数群を提供。
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア合計が 0 の場合は等金額へフォールバック、警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有のセクター比率が閾値を超える場合、新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を提供（"bull"/"neutral"/"bear" マッピング。未知レジームは 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - 株数計算ロジックを実装（risk_based / equal / score の allocation_method をサポート）。
    - 単元株丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケールダウンと残余分の割当ロジック）などを実装。
    - 手数料・スリッページ用の cost_buffer を想定した保守的コスト見積りを反映。

  - portfolio/__init__.py
    - 上記関数群をパッケージ公開。

- モニタリング / データベース
  - monitoring_db の初期化呼び出しを run_execution/run_monitoring から行い、監視テーブルの冪等初期化を保証（init_monitoring_db を使用）。

- ロギングとプロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを提供。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。

  - utils/process_priority.py
    - プロセス優先度（nice / Windows 優先度）設定関数 set_process_priority を実装。プラットフォーム差分を吸収。
    - CPU affinity を先頭 N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms 等）に基づいて PASS/FAIL を判定。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) をサポート。
    - P95 計算や latency の AVG/MAX/P95 を出力。

- リサーチ（骨組み）
  - research/factor_research.py（途中実装）
    - ファクター計算用モジュールを追加（モメンタム、ボラティリティ、Value、Liquidity 等を想定）。DuckDB 接続を受けて prices_daily / raw_financials から計算する設計。
    - 設計方針や定数（期間長）を定義。関数 calc_momentum の実装が開始されている（ファイル途中まで）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 機密情報取り扱いに関する注意を .env テンプレートに明記（.env を絶対に Git にコミットしない旨）。

---

注記（実装上の注意点・推測）
- config の自動 .env ロードはプロジェクトルート検出に依存するため、配布後も動作するように __file__ ベースで親ディレクトリを探索する実装になっています。テスト時などで自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定できます。
- run_monitoring は明示的に「監視は本番 sqlite_path を使用する」とコメントにあり、環境にかかわらず production monitoring DB を参照する意図があります。運用時は注意してください。
- PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の環境変数にはバリデーションがあり、不正値は ValueError を送出するため起動時の設定確認が必要です。
- いくつかの箇所で「将来的拡張（TODO）」が残されています（例: position_sizing の銘柄別 lot_size 拡張や price フォールバックロジックなど）。

もし特定の変更点（ファイルごとの差分やリリースノート向け要約）をより詳細に反映したい場合は、対象のコミットメッセージや差分情報を提供してください。