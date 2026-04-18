CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従って記載しています。
タグ付け規約: なし（初版リリース: 0.1.0）

Unreleased
----------
（現時点のワーキングツリーに未リリースの変更はありません。）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本フレームワークを実装（初期リリース）。
  - パッケージ情報:
    - バージョン: `kabusys.__version__ == "0.1.0"`。

- 実行スクリプト:
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 停止はプロジェクト内 data/stop_requested.flag を監視して行う。
    - 監視は KABUSYS_ENV にかかわらず本番の SQLite パスを使用する挙動を採用。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用専用 SQLite DB（既定: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用して実際の/モックのブローカークライアントを生成（環境に応じて切替）。
    - ExecutionEngine を別スレッドで起動し、data/stop_requested.flag を監視して優雅に停止する仕組み。
    - PID ファイル管理（data/execution.pid）に対応。
    - 起動時にプロセス優先度を "high" に設定する。

- 設定管理:
  - config.py
    - 環境変数/.env/.env.local の自動読み込みを実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
    - .env パーサを実装: コメント/`export ` プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを導入し、各種設定（DB パス、API トークン、監視閾値、ログレベルなど）をプロパティ経由で取得可能に。
    - `paper_fill_mode`（Paper Trading の約定振る舞い）の検証ロジックを追加（有効値: instant/partial/never/reject）。
    - 環境（development/paper_trading/live）やログレベルの検証を含む。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 秘匿項目はマスクして表示。既存 .env の読み込みと Enter による再利用に対応。
    - デフォルト値、選択肢、説明文を提示してユーザー入力を促す。
    - ファイル書き出し時にテンプレート形式で保存。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の未設定検出、置き換えプレースホルダの警告、DB パスの親ディレクトリ存在チェック、config/*.yaml の有無および（PyYAML があれば）パース検証を実施。
    - `--strict` オプションにより警告を FAIL 扱いにできる。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ロギング/プロセス管理ユーティリティ:
  - utils/logging_setup.py
    - 全起動スクリプトで共通利用できるログ設定ユーティリティを追加。
    - stdout への StreamHandler（標準出力）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重設定を防止。
    - 環境変数 `LOG_DIR` / `LOG_LEVEL` による上書きに対応。ディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

  - utils/process_priority.py
    - プロセス優先度（high/normal/low）および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の定数差分を吸収し、権限不足や未対応環境では警告を出してスキップする堅牢性を実装。
    - set_cpu_affinity により最初の N コアに固定する機能を提供。

- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバック（警告ログ）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有のセクター別時価を計算し上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear、未知レジームは 1.0 にフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）での丸め、1 銘柄上限・集計上限（available_cash）・コストバッファを考慮したスケーリングロジック、残余キャッシュを利用した端数配分アルゴリズムを実装。
    - 価格欠損時のスキップやログ出力を含む。

- 分析/検証ツール:
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - データソースは paper_trading 用 SQLite（環境変数 PAPER_TRADING_SQLITE_PATH または --db オプション）。
    - レポートはシステム稼働率、注文成功率（Filled/Created）、送信率、リスク却下数、API レイテンシ（AVG/MAX/P95）を出力。
    - PASS/FAIL 判定基準（稼働率 99% 以上、成立率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200ms）を定義。
    - 日付フィルタ（--from/--to）に対応。

- データベース/共通:
  - duckdb との統合を想定した接続利用箇所を追加（Execution/Monitoring/Research 等で使用）。
  - 監視テーブルを初期化する init_monitoring_db を呼び出して冪等に監視テーブル存在を保証。

- リサーチ:
  - research/factor_research.py（モジュール導入）
    - モメンタム、移動平均乖離率、ATR、流動性等のファクター計算を行う設計を追加（DuckDB を利用し prices_daily/raw_financials を参照する方針）。
    - 設計ドキュメント参照箇所と定数（窓長等）を定義。モメンタム算出関数 calc_momentum の骨格を実装（途中ファイル末尾までの実装あり）。

Changed
- 初回公開のため該当なし（初版）。

Fixed
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Notes / 補足
- .env の自動読み込みは OS 環境変数を尊重する（既存キーは上書きされない）。`.env.local` は `.env` の後に上書きロードされ、OS 環境変数を保護する仕組みを持つ。
- run_monitoring と run_execution はどちらも起動時にプロセス優先度を上げる処理を行うため、実行環境での権限（nice の変更や Windows の優先度変更）に注意すること。
- paper_trading モードは本番 DB と完全に分離する設計を目指している。運用時は PAPER_TRADING_SQLITE_PATH の設定を確認すること。