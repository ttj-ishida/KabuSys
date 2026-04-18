CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

[Unreleased]
------------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション構成・起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離して動作する設計。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成。
    - Engine を別スレッドで起動し、data/stop_requested.flag を検出すると安全に停止する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視用 DB（SQLite）は Monitoring が環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。KeyboardInterrupt による終了処理も実装。

- 設定管理とユーティリティ
  - config.py
    - Settings クラスを導入し、環境変数から各種設定を取得する API を提供（DuckDB / SQLite パス、ログレベル、KABUSYS_ENV 判定、paper_trading 判定等）。
    - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。優先順位は OS 環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パースは export 形式やクォート・コメントを考慮して堅牢に実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など paper_trading 関連設定をサポート。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を追加。必須・任意項目やシークレットのマスク表示に対応。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在・パース（PyYAML があれば実行）等を検査。--strict モードで警告を FAIL 扱いにできる。
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）をルートロガーへ設定。既存ハンドラの二重登録を防止。
    - LOG_DIR 環境変数や引数でログ出力先を指定可能。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - プラットフォーム差分（Windows / POSIX）を吸収するプロセス優先度設定ユーティリティを追加。psutil を利用し、nice 値や Windows の優先度クラスを設定。失敗時は警告ログを出してスキップ。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足等は警告してスキップ）。

- ポートフォリオ構築関連モジュール (純粋関数群)
  - portfolio/portfolio_builder.py
    - 候補銘柄選定 select_candidates（スコア降順、signal_rank によるタイブレーク）。
    - 等金額配分 calc_equal_weights。
    - スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター時価比率が閾値を超える場合に新規候補を除外、"unknown" セクターは除外対象外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポートし未知のレジームは警告して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes を実装（allocation_method="risk_based"/"equal"/"score" をサポート）。
    - 単元株（lot_size）で丸め、per-position 上限、aggregate cap（利用可能現金 available_cash を超えた場合のスケーリングと端数処理）を実装。
    - cost_buffer を考慮した保守的見積りをサポート。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - SQLite の paper_trading DB（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）から統計を集計してレポート出力（稼働率、注文成功率、送信率、リスク却下数、レイテンシ指標: avg/max/P95）。
    - デフォルトの合否基準を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。
    - CLI で期間指定（--from/--to）や DB パス指定（--db）が可能。

- データ分析基盤（着手）
  - research/factor_research.py
    - DuckDB 接続を受け取り株価テーブル等からファクターを計算するための基盤を実装開始（モメンタム、MA200、ATR, ボラティリティ系の定数と calc_momentum の骨組みを含む）。（注: ファイル末尾で実装が途中で切れている箇所あり — 継続実装予定）

Changed
- 初期リリースのため過去変更はなし。

Fixed
- 初期リリースのためなし。

Deprecated
- 初期リリースのためなし。

Removed
- 初期リリースのためなし。

Security
- 特になし。

Notes / 詳細
- 環境変数の取り扱い
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
  - 推奨・任意: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など
  - .env の自動ロードはプロジェクトルートが検出できた場合にのみ実行され、既存 OS 環境変数は保護されます（.env.local は .env 上書き）。
- ログ設定
  - stdout (StreamHandler) を優先し、Task Scheduler / cron 等で stdout/stderr を一本化して扱えるように設計。
  - ファイル出力に失敗した場合でもサービスは継続するフェイルソフト設計。
- 実行制御
  - run_execution/run_monitoring はそれぞれ data/stop_requested.flag（プロジェクトルートの data ディレクトリ）を監視して外部から停止指示できる仕組みを持つ。
- paper_trading モード
  - paper_trading モードでは実際のブローカー API への発注を行わない Mock/専用実装を利用し、DB も paper_trading 用に分離されるため安全に検証が可能。

既知の制限 / TODO
- research/factor_research.py の実装が途中で終わっている箇所が存在します（calc_momentum の続き等）。今後の実装・テストが必要です。
- position_sizing の価格フォールバック（price が欠損した場合の扱い）について TODO コメントあり。前日終値等を用いたフォールバックを検討する必要があります。
- process_priority / set_cpu_affinity は権限・プラットフォーム依存の動作を含むため、利用環境によっては設定がスキップされます（ログで通知）。

--- 

以上。リリース履歴や注記の追加・修正を希望される場合は、追記したい変更点やリリース日をご指示ください。