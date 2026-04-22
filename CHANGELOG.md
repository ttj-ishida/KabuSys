# Changelog

すべての注目すべき変更を記載します。フォーマットは Keep a Changelog に準拠しています。

全般:
- 重大な API 変更や互換性に関する注意は各リリースノートに明記します。
- バージョン番号はパッケージの src/kabusys/__init__.py に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-22
初回リリース。以下の主要機能とユーティリティを追加しました。

### Added
- コアパッケージ構成
  - パッケージバージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
  - パッケージ構造: data, strategy, execution, monitoring などのサブパッケージをエクスポート。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - 環境変数 KABUSYS_ENV により paper_trading モードをサポート。paper_trading の場合は専用 SQLite（data/paper_trading.db / 環境変数 PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成を導入（本番/モック切替）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine をデーモンスレッドで起動。停止フラグ（data/stop_requested.flag）および pid ファイル（data/execution.pid）をサポート。
    - RiskConfig の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を導入。初期 portfolio value は broker.get_available_cash() から取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックして警告を出力。
    - Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視テーブルを操作。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了。

- 設定管理
  - config.py
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）を実装。OS 環境変数を保護するための protected オプションをサポート。
    - .env パースの堅牢化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメントの取り扱い等。
    - Settings クラスを追加し、J-Quants / kabuAPI / LINE / DB / 監視 / システム設定をプロパティ経由で提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の厳密チェックを実装。
    - paper_trading 用データベースパス（paper_sqlite_path）を提供。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新するツールを追加。
    - 各項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）を対話的に入力できる。
    - 秘匿項目はマスク表示。既存 .env の読み込み/再利用対応。
    - 最終確認後に .env を上書き保存する機能を提供。

  - validate_config.py
    - .env と config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在と PyYAML によるパースチェックを実施。
    - --strict モードで警告も失敗扱いにできる。
    - 本番環境 (KABUSYS_ENV=live) に関する追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。

- 監視・実行周りの DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を使用して監視テーブルの存在保証（冪等）を行うコードを各スクリプトから呼び出す。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ初期化関数 setup_logging を追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。
    - ログレベル決定ロジック（引数 > 環境変数 > デフォルト）やログディレクトリ自動作成とフォールバック動作を実装。
    - ファイルハンドラ作成失敗時はコンソール出力のみにフォールバック。

  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定 set_process_priority を追加（Windows, POSIX 対応／psutil 使用）。
    - CPU affinity を設定する set_cpu_affinity を追加（指定コア数による固定）。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で上位 N 件抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分を実装。スコア合計が 0 の場合は等配分にフォールバックして WARNING。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を実装（指定の max_sector_pct を超える既存エクスポージャがあるセクターは当日の新規候補を除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じて投下資金乗数を返す。未知レジームは 1.0 にフォールバックして警告。

  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・資産情報から銘柄ごとの発注株数を計算（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based モードではリスク許容率・ストップロス率を用いて株数を算出。
    - lot_size（単元株）に基づく丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料・スリッページ保守見積り）を考慮。
    - スケールダウン時の端数処理で remainder に基づく再配分を実装。

  - portfolio パッケージの __init__ で主要関数群をエクスポート。

- リサーチ・ファクター計算基盤
  - research/factor_research.py
    - DuckDB 接続を受け取って prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity 等のファクターを計算する方針でモジュールを追加。
    - 定数（モメンタム窓長、MA200、ATR 日数等）と関数 calc_momentum の骨組みを実装（営業日ベースの扱い、欠損時の None 処理等）。
    - （注）ファイルの後半は実装継続中の箇所あり（calc_momentum の実装途中で切れているため、今後の実装完了を予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で指定した SQLite DB を読み、system_status / trade_logs / risk_logs から各種指標を算出（稼働率、注文成功率、送信率、P95 レイテンシ等）。
    - P95 計算、閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 200 ms）を用いた PASS/FAIL 判定を実装。
    - 日付フィルタ（--from, --to）対応、DB 存在チェック、テーブル存在しない場合の安全なフォールバックを実装。

### Changed
- なし（初回リリースのため追加が主体）。

### Fixed
- なし（初回リリース）。

### Documentation
- 各スクリプト・モジュールに docstring を整備し、CLI の使い方や注意点（.env を絶対にコミットしない等）を明記。

### Notes / Known issues / TODO
- research/factor_research.py の一部実装が途中（calc_momentum の先頭以降が未完）。今後のリリースでファクター計算ロジックを完成させる予定。
- portfolio/position_sizing.py:
  - TODO: price が欠損（0.0）でエクスポージャが過少見積もられる問題。将来的には前日終値や取得原価等のフォールバックを導入予定。
  - TODO: 将来的に銘柄別単元（lot_size）を stocks マスタで扱う拡張を検討。
- run_monitoring.py は Monitoring の DB 接続に本番 sqlite_path を常に使用する設計（意図的）。運用上の注意として KABUSYS_ENV に依らず監視データは本番 DB に記録される点に留意してください。
- process_priority の設定は権限や OS に依存するため、失敗時はワーニングを出して安全にスキップする挙動としています。

---

今後の予定（例）
- research/factor_research の完遂（ファクター算出の SQL/サンプリング実装）。
- ExecutionEngine / RiskManager のより詳細なテストとドキュメントの整備。
- モジュール単位のユニットテスト追加と CI 設定。

もし CHANGELOG に追加したい具体的な差分（コミット単位や変更ファイルリスト）があれば、それに基づいてより詳細な履歴を作成できます。