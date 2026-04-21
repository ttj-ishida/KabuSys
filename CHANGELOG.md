CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
タグ付け規約: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-04-21
--------------------

Added
- 初期リリースを追加。
- 実行・監視用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 専用 SQLite DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全分離。
    - エンジンは別スレッドで実行され、data/stop_requested.flag を監視して安全に停止可能。
    - 実行用 PID ファイルを data/execution.pid に出力する仕組みを想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視処理は KABUSYS_ENV に関わらず本番用 sqlite_path を使用して監視テーブルを初期化・更新。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - KeyboardInterrupt に対してもクリーンに終了。

- 設定管理
  - config.py: 環境変数自動読み込みと Settings クラスを実装。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を OS 環境変数に組み込む（既存の OS 環境変数は保護）。
    - .env パーサは quotes（'"/）や export プレフィックス、インラインコメントなどに対応。読み込み失敗時は警告を吐く。
    - 必須環境変数取得関数 _require を提供し、未設定時に明示的なエラーを送出。
    - 各種設定プロパティ（DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を整備。入力検証とデフォルト値を提供。

- 設定支援ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
    - 秘匿項目のマスク、選択肢・デフォルト提示、既存 .env の読み込みと Enter による再利用をサポート。
    - 保存前に入力内容を確認可能。
  - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの存在チェック（親ディレクトリの有無警告）、config/*.yaml の存在および PyYAML によるパース検証を実行。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。
    - stdout への StreamHandler と 日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - 既存ハンドラをクリアして重複を防止。ログレベル/ログディレクトリ解決ルールを明示。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ運用。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティを追加。
    - Windows / POSIX (Linux, Darwin, FreeBSD) を抽象化して優先度設定を試行。アクセス権限不足時は警告を出してスキップ。
    - set_cpu_affinity によりカレントプロセスを最初の N コアに固定する機能を提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。スコア合計が 0 の場合は等配分にフォールバックして警告。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中をチェックして上限超過セクターの新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をサポート、未知のレジームは 1.0 にフォールバックして警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき各銘柄の発注株数を計算。
    - 単元株（lot_size）や max_position_pct, max_utilization, cost_buffer（手数料・スリッページ見積り）を考慮した安全なスケーリングロジックを実装。aggregate cap 超過時はスケールダウンして端数は lot_size 単位で再配分。

- 研究・解析ユーティリティ
  - research/factor_research.py（作成途中を含む）:
    - モメンタム/ボラティリティ/流動性/バリュー等のファクター計算方針を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照して処理を行う設計。
    - 1M/3M/6M リターン、MA200 乖離、ATR、出来高指標などを計算するための定数と関数（calc_momentum 等）を準備。

- ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを計算し、パス/フェイル判定を行う。
    - デフォルト閾値（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms）を設定。
    - 日付フィルタ (--from/--to) と DB パス指定 (--db) をサポート。DB が存在しない場合はエラーメッセージを出力。

Changed
- 監視 DB 初期化の扱いを明確化: init_monitoring_db() を実行して監視用テーブルの存在を保証（冪等）するように全スクリプトで呼び出す。
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定するため set_process_priority("high") を呼び出すように統一。
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。

Fixed
- （初期リリースにつき明確なバグ修正履歴はなし。実運用でのフィードバックにより追って修正予定。）

Security
- 秘匿情報（J-Quants リフレッシュトークン、kabu API パスワード、LINE トークン等）は .env に保存する想定だが、config_setup の注意書きに「.env を絶対に Git にコミットしないこと」を明記。Settings._require により必須機密の未設定を検出して起動前に失敗させる。

Notes / 注意事項
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。無効な値は起動時に ValueError を送出。
- Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path を使用する仕様（監視テーブルは本番 DB に保存する想定）。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソール出力を継続できるよう設計されているため、権限・環境差異のある環境でも最低限のログは得られる。
- process_priority / set_cpu_affinity は権限や OS に依存するため、失敗時は警告を出して処理を継続する安全設計。

今後の予定（予定機能）
- research/factor_research.py の完全実装（各ファクター算出の SQL/ロジック完成）。
- テスト・CI の追加、静的型チェックの強化。
- ExecutionEngine 周りの詳細なエラーハンドリング、モニタリング拡張（アラート送信等）。

ライセンス・バージョン
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py の __version__ に準拠)

[Unreleased]: https://example.com/compare/v0.1.0...HEAD
[0.1.0]: https://example.com/releases/tag/v0.1.0