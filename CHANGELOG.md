# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはコードベースから推測して自動生成した要約です。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージを追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を定義。

- 実行・監視起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により実行時に適切なブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、data/stop_requested.flag により安全に停止可能。
    - PID ファイル（data/execution.pid）を使用。
    - 監視用テーブルの初期化（init_monitoring_db）を行い冪等性を担保。
  - run_monitoring.py
    - SystemMonitor 用ポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。0以下や不正値はデフォルトにフォールバックし警告を出力。
    - 監視は環境にかかわらず本番の sqlite_path を使用して初期化（監視 DB の一貫性を確保）。
    - stop flag（data/stop_requested.flag）検知でループを抜ける。

- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動読み込みを無効化可能（テスト用途想定）。
    - .env の行パーサーを実装（export 句、クォート、エスケープ、インラインコメント処理を考慮）。
    - Settings クラスを提供し、各種環境変数のアクセス、バリデーション、およびデフォルト値を定義（J-Quants、kabu API、DuckDB/SQLite パス、Paper Trading 設定、監視閾値、KABUSYS_ENV/LOG_LEVEL の検証など）。
    - `paper_fill_mode`、`paper_sqlite_path`、`kill_flag_clear_on_start` など Paper/Monitoring に関する設定を追加。

- 設定支援 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成/更新するツールを提供。
    - 必須項目・任意項目のプロンプト、シークレット値のマスク表示、選択肢サポート、既存 .env の取り込み、最終確認後に .env を書き出す機能を実装。

  - validate_config.py
    - 起動前に .env および config/*.yaml の簡易検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML がない場合はスキップで警告）を実行。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ/プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するセットアップ関数 `setup_logging()` を追加。
    - ログレベル・ログディレクトリの解決順序を定義し、ディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定する `set_process_priority()` を追加（Windows の優先度定数/posix の nice 値に対応）。
    - CPU affinity を設定する `set_cpu_affinity()` を追加（指定コア数にプロセスを固定）。
    - 権限不足や未対応 OS の場合は警告を出し処理をスキップ。

- ポートフォリオ構築ユーティリティ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコアが全て0の場合は等金額にフォールバックする警告あり。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有額からセクターごとのエクスポージャーを計算し、上限超過セクターの新規候補を除外。unknown セクターは制限対象外。
    - 市場レジームに応じた資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear マップ、未知レジームは警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出ロジック（risk_based / equal / score）を実装。単元株（lot_size）で丸め、per-position と aggregate の上限を考慮し、available_cash を超える場合のスケーリングと端数処理（残差に基づく追加配分）を行う。
    - cost_buffer（手数料・スリッページ見積り係数）を考慮して保守的にコストを見積もる実装。
    - TODO コメントで価格欠損時のフォールバック処理拡張を明記。

- DuckDB 統合
  - DuckDB 接続を受け取る設計（Settings.duckdb_path に基づき run スクリプトで接続）。research, execution, monitoring などで分析用 DB を共有可能。

- Research / Factor 計算
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity などのファクター計算基盤の追加。DuckDB を利用して prices_daily / raw_financials テーブルを参照する設計。計算窓や定数（MA200、ATR、各種期間）を定義。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - コマンドライン引数 --from/--to/--db に対応。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づいて PASS/FAIL 判定を出力。
    - SQLite（デフォルト data/paper_trading.db）を参照して各種集計クエリを実行。db ファイルが存在しない場合はエラーメッセージを出力。

### Changed
- （初版なので過去バージョンからの変更はありません）

### Fixed
- （初版なのでバグ修正履歴はありません）

### Known issues / Notes
- position_sizing.calc_position_sizes において、価格データが欠損（0.0）だった場合のエクスポージャー過少見積りに関する TODO が残っている（前日終値や取得原価でのフォールバックを検討）。
- research/factor_research.py はファクター計算の主要処理を含むが、外部に依存しないテストや完全な実装の確認は必要（DuckDB のテーブルスキーマ依存）。
- .env パーサーは多くの実用例を考慮しているが、特殊なエスケープや複雑なシェル展開はサポート対象外。
- ログ出力ディレクトリ作成に失敗した場合はファイルログが無効になり、コンソール出力のみになる点に注意。

---

今後のリリースでは以下を想定しています（優先度順、推奨）:
- テストカバレッジの追加（ユニットテスト / インテグレーションテスト）。
- position_sizing の価格フォールバック実装。
- research モジュールの完全実装とベンチマーク。
- エラーレポート／アラート（LINE 通知等）の拡充。
- Docker / systemd など実運用向けデプロイメントサンプルの追加。