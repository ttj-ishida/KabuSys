CHANGELOG
=========

すべての注目すべき変更点はここに記載します。  
このファイルは「Keep a Changelog」準拠の形式で記載しています。

Unreleased
----------

- （未リリースの変更はここに記載）

0.1.0 - 2026-04-20
------------------

Added
- 初回リリース。KabuSys 自動売買フレームワークのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、検証ツール等を追加。
- 環境設定 / ロード
  - Settings クラスを追加（src/kabusys/config.py）。環境変数から設定値を取得するためのプロパティ群を提供。
  - .env 自動読み込み機構を追加（プロジェクトルート検出: .git / pyproject.toml を探索）。優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを強化（引用符対応、エスケープ、インラインコメント処理、export 形式サポート）。
  - デフォルト設定値を明記（例: DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、LOG_LEVEL=INFO 等）。
  - PAPER_FILL_MODE に対する検証（instant/partial/never/reject のみ許容）。

- 起動スクリプト / 実行
  - 実行エンジン起動スクリプト: run_execution.py を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler 等の組み立て、ExecutionEngine の起動ループを実装。
    - 停止フラグ（data/stop_requested.flag）の監視、PID ファイル書き出し（data/execution.pid 相当）対応。
    - プロセス優先度を起動時に "high" に設定。
  - 監視ループ起動スクリプト: run_monitoring.py を追加。
    - SystemMonitor インスタンスの初期化とポーリングループ実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知、例外発生時のロギングとリカバリ（次ポーリングへ継続）、KeyboardInterrupt のハンドリング。

- 設定支援 / 検証 CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。シークレットマスキング、選択肢提示、既存 .env 読み込み、.env への安全な書き出しを実装。
  - validate_config.py: 起動前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在チェック（PyYAML があればパース検証）。--strict モードで警告を FAIL 扱いに可能。ライブ環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START 設定などの警告）。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30世代保持）を設定。
    - LOG_DIR の自動作成、作成失敗時はファイルロギングをスキップしてコンソールのみで継続。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト。
  - utils/process_priority.py を追加。
    - Windows と POSIX を吸収したプロセス優先度設定（high/normal/low）。psutil を使い、権限不足等は警告を出してスキップ。
    - CPU affinity 設定ユーティリティも提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N 件を選択。タイブレークは signal_rank。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア加重配分（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック。既存ポジション評価と売却予定銘柄除外を考慮。unknown セクターは上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告して 1.0 を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数計算（risk_based / equal / score）。
      - リスクベースでは risk_pct, stop_loss_pct を使用、単元株（lot_size）丸め、1 銘柄上限・利用率上限を考慮。
      - 合計投下額が available_cash を超える場合はスケールダウンと remainder による追加配分ロジックを搭載。
      - cost_buffer を用いてスリッページ/手数料を保守的に見積もる。

- 解析 / 検証ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH で指定可）からデータを集計し、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）、リスク却下数等を算出してレポート出力。
    - デフォルトの合格基準を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）。欠損データ時の N/A ハンドリング。
    - コマンドラインで --from / --to / --db オプション対応。

- 研究用ファクター計算（開発中）
  - research/factor_research.py を追加（モメンタム / ボラティリティ / バリュー等の計算関数を設計）。DuckDB 接続を受け prices_daily / raw_financials を参照して計算する方針。実装は途中（ファイル末尾で切れている部分あり）。

- パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- ロギングの標準出力は stderr ではなく stdout を使用（cron 等からのリダイレクトを想定）。
- .env の読み込み挙動: .env と .env.local の優先度を明確化し、既存 OS 環境変数を保護するため protected キーを導入。

Fixed
- N/A（初回リリースのため既存のバグ修正履歴はなし）

Known issues / Notes
- research/factor_research.py の実装が途中で切れている箇所がある（ファイル末尾）。ファクター計算の完全実装は今後の作業。
- position_sizing の price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価のフォールバック導入を検討中（ソース内に TODO を記載）。
- process_priority/set_cpu_affinity は権限やプラットフォームにより動作しない場合があり、失敗時は警告を出してスキップする設計。

References
- 各モジュールの利用方法や CLI の使い方はソースコード中のドキュメンテーション（docstring / コメント）を参照してください。