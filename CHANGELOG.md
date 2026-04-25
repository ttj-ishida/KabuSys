CHANGELOG
=========

全般
----
- 本ドキュメントは Keep a Changelog の形式に準拠しています。
- バージョンはパッケージの __version__（現在 0.1.0）に基づき記載しています。
- 以下は、与えられたコードベースの内容から推測してまとめた初期リリース（0.1.0）の変更点です。

[0.1.0] - 初期リリース
--------------------

Added
-----
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag を監視して安全にループ終了。
    - Monitoring は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して DB に接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。
    - 実行スレッドをデーモンで起動し、停止フラグ検知時に安全に停止要求を送る。

- 設定・環境管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml を基準に探索）。
    - .env のパースは export 付き記述、引用符で囲まれた値、インラインコメント等に対応。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定 等）。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START などの専用設定をサポート。
    - settings インスタンスをグローバルに提供。

  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - シークレット値マスク、選択肢提示、既存 .env 読み込み、最終確認・保存機能を備える。

  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数・パス・config/*.yaml の存在と YAML パース等をチェック）。
    - --strict オプションにより警告を FAIL 扱いにできる。
    - 本番（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定や Kill Flag 設定の警告）を実装。

- ユーティリティ
  - utils/logging_setup.py
    - アプリケーション共通のログ設定ユーティリティを追加。
    - コンソール出力は stdout を使用、日次ローテーション（TimedRotatingFileHandler）でログファイルを保存（デフォルト logs/、30日保持）。
    - ログレベル・ログディレクトリの解決優先順を実装。

  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度と CPU affinity の設定を行うユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応。psutil による実装で失敗時は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア降順＋タイブレーク）および等金額・スコア重み計算を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（売却予定銘柄除外、"unknown" セクターは無視）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告後 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate キャップ、cost_buffer（手数料・スリッページ見積もり）を考慮したスケーリングロジックを実装。
    - 不足価格データの取り扱いや再配置での端数処理（残差に基づく追加割当）を実装。

- 研究用ファクター計算（部分実装）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 系のファクター算出方針と各種定数を追加（DuckDB の prices_daily / raw_financials を参照する設計）。
    - calc_momentum 関数の骨組みと定数が導入済（実装はファイル末尾で続く模様）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で上書き可）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定する基準値（稼働率 99%、成立率 90% 等）を定義。
    - 日付フィルタ、各種集計クエリ、P95 計算、出力整形を実装。

- パッケージ初期化
  - __init__.py にてパッケージ名・バージョンと主要サブパッケージの __all__ を定義。

Changed
-------
- デフォルト設定・実行上の注意点の明示化
  - ポーリング間隔のデフォルトは 60 秒。MONITOR_POLL_INTERVAL の不正値時は警告を出してデフォルトにフォールバック。
  - logging_setup: ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソール出力のみを継続。
  - process_priority: 権限不足や未対応 OS の場合は警告を出して処理をスキップ。

Fixed
-----
- 起動時の安全機構を強化
  - run_execution/run_monitoring で停止フラグや PID 管理を利用し、安全に停止・再起動できるようにした。
  - run_execution で paper_trading 実行時に本番 DB と分離して専用 SQLite を使用することで誤操作リスクを低減。

Notes / Behaviour
-----------------
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Settings.api 等の必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は未設定時に ValueError を送出する仕様のため、起動前に validate_config の実行を推奨。
- paper_verification_report のしきい値はコード中の定数で定義されており、必要に応じて調整可能。
- DuckDB / SQLite のパスやログ出力先は環境変数で上書き可能（DUCKDB_PATH, SQLITE_PATH, LOG_DIR 等）。

Acknowledgements / TODO（コード内に記載の今後の改善点）
-----------------------------------------------------
- portfolio.position_sizing:
  - lot_size を銘柄ごとに持たせる設計への拡張（stocks マスタ参照）を検討中。
  - price が欠損（0.0）時のフォールバック価格（前日終値など）を導入検討。
- research.factor_research:
  - calc_momentum 等の関数実装の続き・テストが必要。
- ロギング・ハンドラ作成失敗時の挙動確認や、より厳密なエラーハンドリングを強化予定。

ライセンス・その他
-----------------
- 本 CHANGELOG はコードベースの静的解析から推測した内容に基づいて作成しています。実際のコミット履歴やリリースノートを持つ場合は、それらに合わせて調整してください。