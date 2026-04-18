# CHANGELOG

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全てのリリースは semver を想定しています。

## [0.1.0] - 2026-04-18

### 追加
- 初回リリース: KabuSys ベース機能群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db をデフォルト）へ完全分離して記録。
    - BrokerClientFactory により本番/モック（Paper Trading）クライアントを切り替え。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル（data/execution.pid）出力機構に対応。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する設計（監視データは本番 DB を想定）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- 設定関連
  - config.py: アプリケーション設定管理クラス（Settings）を追加。
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env と .env.local の優先順位を実装（OS 環境変数を保護して上書き制御）。
    - .env の行パーサは export 形式、クォート（シングル/ダブル）のエスケープ、インラインコメント扱いを考慮。
    - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DUCKDB/SQLite パス, Paper Trading 関連, 監視閾値, ログレベル等）。
    - PAPER_FILL_MODE のバリデーションを実装（instant/partial/never/reject）。
    - KABUSYS_ENV のバリデーションを実装（development / paper_trading / live）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - ウィザードから .env の初期作成・更新を支援。シークレット項目はマスク表示。
    - デフォルト値、選択肢、説明を表示して保存可能。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DUCKDB/SQLITE パスの親ディレクトリ確認、config/*.yaml の存在と簡易パース検証（PyYAML の有無に応じて挙動を変える）。
    - KABUSYS_ENV=live のときに本番用ガード（LINE 通知設定や Kill Switch 設定の警告）を実行。
    - --strict オプションで警告を fail 扱いにできる。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順（同点は signal_rank 昇順）で候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比例配分（全スコアが 0 の場合は等配分にフォールバックし WARNING）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率に基づき新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 にフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
      - risk_based: 許容リスク（risk_pct）とストップロスで株数を算出。
      - equal/score: 重みと max_utilization を使った配分。
      - 単元株（lot_size）丸め、per-position 上限（max_position_pct）を考慮。
      - aggregate cap として利用可能現金 available_cash を超えた場合はスケールダウンし、残余で再配分（lot 単位）するロジックを実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
- ユーティリティ
  - utils.logging_setup: ログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみ）。
    - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。
    - stdout を使用することで Task Scheduler/cron との相性を配慮。
  - utils.process_priority: プロセス優先度 / CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX (Linux, Darwin, FreeBSD) の違いを吸収して set_process_priority を提供（high/normal/low）。
    - set_cpu_affinity により最初の N コアに固定可能（未指定は全コア）。
    - 権限不足や非対応環境では警告を出して安全にスキップ。
- モニタリング関連
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等初期化を実施（Execution 起動時にも保証）。
  - SystemMonitor を使用した監視チェックの1回実行 API（monitor.check_once）を使用。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime_pct), 注文成功率 (fill_rate), 送信率 (send_rate), レイテンシ (avg/max/P95), リスク却下数。
    - デフォルト閾値を定義し Pass/Fail を判定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 計算、期間フィルタ（--from/--to）、DB パス指定（--db）に対応。
- 研究用ファクター計算基盤
  - research.factor_research: DuckDB 接続を受け取り momentum, value, volatility, liquidity 等のファクターを計算するための基盤を実装（設計ドキュメントに基づく）。（注: ファイルは一部実装中）

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点 / 実装メモ
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップするため、パッケージ配布後や特殊環境では明示的に環境変数を設定してください。
- run_monitoring は監視 DB として Settings().sqlite_path（本番想定）を使用するため、監視データを分離したい場合は sqlite_path を別途設定してください。
- position_sizing の lot_size は現在グローバル共通（デフォルト 100）で、将来的に銘柄別対応を想定した拡張ポイントあり（TODO コメントあり）。
- 一部モジュールは外部依存（psutil, duckdb, PyYAML など）に依存します。環境に無い場合は機能が限定的になります（validate_config, logging のファイル出力等は警告でフォールバック）。

### セキュリティ
- .env ファイルは出力時に Git にコミットしない旨を README / ヘッダに明記。シークレット項目はウィザードでマスク表示。

---

今後の予定（例）
- factor_research の完全実装（ファクター計算の SQL 実装完了、正規化/結合ロジック）。
- ExecutionEngine / Reconciler / RiskManager の追加テスト & 性能改善。
- 銘柄別 lot_size 対応、手数料モデルの拡張。