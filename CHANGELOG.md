Keep a Changelog
=================

すべての重要な変更点をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
------------

- （準備中）

[0.1.0] - 2026-04-23
-------------------

Added
- 基本パッケージの初回リリース。
- 実行用スクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成は BrokerClientFactory 経由。
    - ExecutionEngine は別スレッドで実行され、 data/stop_requested.flag の検知で安全に停止する。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行中はデータベース（SQLite / DuckDB）を開き、終了時に確実にクローズする。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視データは常に本番 DB に記録）。
    - data/stop_requested.flag を検知してループを終了する仕組みを実装。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理 & CLI
  - config.py
    - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env の読み込みルール: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（空白で区切られた #）に対応。
    - Settings クラスにアプリ全体で使用するプロパティを提供（DB パス、API トークン、Paper Trading 設定、監視しきい値等）。環境値の検証（有効値チェック、必須チェック等）を行う。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を追加。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新可能。シークレット値はマスク表示。保存前に確認プロンプトを表示。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パス親ディレクトリの有無チェック、config/*.yaml の存在とパースチェック（PyYAML が利用可能な場合）。
    - --strict モードで警告を失敗扱いにできる。
- ログ / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに stdout 出力と日次ローテーション（TimedRotatingFileHandler）を設定する setup_logging を追加。
    - LOG_DIR / LOG_LEVEL の解決順をサポート。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - set_process_priority() で Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定。
    - set_cpu_affinity() でプロセスを最初の N コアにピン留め（利用可能なコア数を超える指定時は全コア利用へフォールバック）。
    - psutil 権限不足や未サポート環境でも安全にフォールバックして警告を出す。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と重み計算（等分配 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）に基づき、新規候補を除外するロジック。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告を出して 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot_size）丸め、max_position_pct・max_utilization 等の制約適用、aggregate cap によるスケールダウンと端数配分ロジックを実装。
    - コストバッファ（cost_buffer）を考慮した保守的見積りをサポート。
- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ等の指標を集計して検証レポートを出力する CLI を追加。
    - デフォルト閾値（稼働率 99.0%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して PASS/FAIL 判定を行う。
    - --from/--to/--db オプションで期間・DB を指定可能。
- 研究用モジュール
  - research/factor_research.py（ファクター計算の骨組みを追加）
    - モメンタム / ボラティリティ / 流動性 / バリュー等のファクター計算方針を実装予定。DuckDB を受け取り prices_daily / raw_financials テーブルから計算する設計。

Changed
- パッケージ初期構成として各モジュールを分割し、明確な責務を設定（設定管理、ロギング、プロセス制御、ポートフォリオ構築、実行・監視スクリプト、ツール類）。

Fixed
- （初回リリースのため該当なし）

Security
- .env ファイルは生成時に Git にコミットしない旨を README ヘッダに明記（config_setup.py で .env に警告コメントを出力）。

Notes / 注意点
- 監視（run_monitoring）は意図的に KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。監視データは本番向けに取り扱う設計です。Paper Trading の監視を完全に分離したい場合は設定を調整してください。
- .env の自動読み込みはデフォルトで有効です。テスト時などで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- process_priority / cpu_affinity の設定は OS 権限に依存します。権限不足時でも起動は継続し、警告ログが出力されます。
- tools/paper_verification_report は SQLite テーブルのスキーマ（system_status / trade_logs / risk_logs 等）に依存します。対象 DB に必要なテーブルがない場合は該当指標は N/A 扱いとなります。

Authors
- KabuSys 開発チーム

References
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)