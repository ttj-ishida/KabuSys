# Changelog

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。  
このファイルでは、リポジトリのコードベースから推測できる追加機能・挙動・設定項目等をまとめています。

<!-- この節は将来の変更に備えたプレースホルダ -->
未リリース
---------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- パッケージ初期版を追加（バージョン: 0.1.0）。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して MockBrokerClient を利用する挙動をサポート。
    - エンジンはバックグラウンドスレッドで実行され、 data/stop_requested.flag の検知で停止する。
    - PID ファイルを書き込む（data/execution.pid を使用、Settings で上書き可）。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出す）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用。
    - stop フラグ（data/stop_requested.flag）でループを終了。
    - duckdb と sqlite のコネクションを利用。
- 環境設定関連:
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI。
    - デフォルト .env パス: プロジェクトルート/.env（対話後に README 的メッセージを表示）。
    - secret 項目は表示をマスクして入力を受け付ける。
  - validate_config.py
    - .env や config/*.yaml の設定不備を起動前に検出する CLI。
    - --strict オプションで警告も FAIL 扱いにできる。
    - 必須環境変数や DB パス、YAML パース（PyYAML が存在する場合）などを検査。
- 環境変数自動読み込み:
  - config.py にて .env/.env.local の自動読み込みを実装。
  - 読み込み順: OS 環境変数 > .env.local > .env。プロジェクトルートを .git または pyproject.toml から検出して適用。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパーサは export 形式やクォート・エスケープ、インラインコメントなどに対して堅牢に処理。
  - Settings クラスでアプリ設定をプロパティ経由で提供（例: duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path, CPU/MEM/DISK 閾値など）。
  - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
  - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
- ロギング・ユーティリティ:
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベルは引数 > LOG_LEVEL 環境変数 > デフォルト INFO の順で解決。
    - ログディレクトリは引数 > LOG_DIR 環境変数 > デフォルト logs/ の順で解決。ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度・CPU affinity ユーティリティ:
  - utils/process_priority.py を追加。
    - set_process_priority(level) で Windows / POSIX に対応してプロセス優先度を設定（psutil を使用）。例外時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め可能（存在しない環境や権限不足時は警告を出す）。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコア合計が 0 の場合は等重でフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャを計算して上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を返す（bull=1.0 / neutral=0.7 / bear=0.3、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes:
      - allocation_method による株数算出（risk_based / equal / score）。
      - risk_based: 損切り幅・risk_pct からポジションサイズを算出。
      - 株数は lot_size（デフォルト 100）で丸められる。
      - per-stock 上限（max_position_pct）、aggregate cap（available_cash）を考慮し、必要に応じて比率でスケールダウンして残差は優先度順に lot 単位で配分する。
      - cost_buffer を用いて手数料等を保守的に見積もる。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py を追加。
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標を集計して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）など。
    - コマンドライン引数で --from / --to（YYYY-MM-DD）および --db を指定可能。
    - デフォルト閾値を定義（例: 稼働率 >= 99.0%、P95 latency <= 200ms 等）と照合して PASS/FAIL 判定を表示。
- 研究用ファクター計算:
  - research/factor_research.py を追加（ファクター計算インフラ）。
    - Momentum, Value, Volatility, Liquidity 系の計算を想定。DuckDB 接続を受け取り prices_daily / raw_financials を参照して出力する設計（calc_momentum 等の関数の雛形あり）。
- パッケージメタ:
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - __all__ で主要サブパッケージをエクスポート。

Changed
- なし（初回リリースとして新規追加が中心）

Fixed
- なし（初回リリース）

Security
- なし特記事項。ただし .env を決して Git にコミットしないよう README 警告を .env 生成ロジック内に明記。

Notes / 運用上の注意（コードから推定）
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して挙動を制御することを推奨。
- run_monitoring は監視 DB（SQLite）を本番パスで開く設計であり、開発・検証と本番 DB の分離に注意（Execution は paper_trading の場合 DB を切り替える実装あり）。
- プロセス優先度・CPU affinity の設定は権限やプラットフォームに依存し、権限不足時は警告を出して安全にフォールバックする。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化するため、ログ保存場所のパーミッションを事前に確認すること。

参考: 主な環境変数（デフォルトを含む）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — デフォルト: logs/
- MONITOR_POLL_INTERVAL — デフォルト: 60（秒）
- PAPER_FILL_MODE — デフォルト: instant（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — デフォルト: 0
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード停止フラグ（1 で無効化）

もしリリースノートに追加したい細かな項目（例えばファイルパスの実際の既定値を変えた等）があれば、対象ファイルやコミット情報を教えてください。推定ではなく確定情報に基づいて CHANGELOG を調整します。