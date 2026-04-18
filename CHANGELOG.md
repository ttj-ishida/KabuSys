CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。
このファイルでは日本語で変更点を要約しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-18
--------------------

Added
- 初回公開リリース (0.1.0)。
- 実行用エントリスクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading の際は専用のペーパートレード用 SQLite（data/paper_trading.db を既定）と MockBrokerClient を利用する。プロセス優先度を "high" に設定し、停止フラグ (data/stop_requested.flag) や実行 PID ファイル (data/execution.pid) を扱う。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用する旨を明示。
- 設定・環境関連:
  - config.py: .env 自動ロード機能（.env, .env.local の順）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、.git / pyproject.toml を基準にプロジェクトルートを探索するロジックを実装。環境変数の取得用 Settings クラスを提供（DB パス、ログ設定、paper_trading の切替、監視閾値等）。
  - config_setup.py: 対話式 .env ウィザード。既存 .env の読み込み・更新、秘密値のマスク、保存テンプレートをサポート。
  - validate_config.py: 起動前チェック CLI。必須環境変数や config/*.yaml、DB パス、KABUSYS_ENV の整合性、production における注意点（LINE 通知未設定など）を検証。--strict モードで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py: 統一されたログ設定ユーティリティ。stdout 出力の StreamHandler と 日次ローテーション（TimedRotatingFileHandler）でのファイル出力（logs/<app_name>.log、30 日保持）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定。Windows / POSIX (Linux, Darwin, FreeBSD) に対応し、権限不足等の失敗は警告でスキップする。
- ポートフォリオ構築モジュール:
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコアが全て 0 の場合は等金額にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py: セクターキャップ適用 (apply_sector_cap)、市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py: position sizing 実装。allocation_method="risk_based" / "equal" / "score" をサポート。損切り率、単元株(lot_size)、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap 時のスケールダウンと端数処理（lot 単位での分配）を実装。
  - portfolio/__init__.py で上記 API を公開。
- 解析・検証ツール:
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を行う。閾値はソース内の定数で管理（稼働率 99% など）。--from/--to/--db で期間・DB 指定可能。
- 研究用モジュール:
  - research/factor_research.py: ファクター計算モジュール（Momentum, Value, Volatility, Liquidity）を追加（DuckDB を用いた prices_daily / raw_financials 参照の方針を明記）。モメンタム計算関数の雛形を含む（将来的な拡張対象）。

Changed
- なし（初回リリースのため該当なし）

Fixed
- なし（初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- .env ファイルは絶対に Git へコミットしないことを README コメントで明示（config_setup のテンプレートにも記載）。
- Settings._require により一部の機密値は未設定時に起動前に検出して明示的なエラーを出す（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

Notes / Important behavior
- 監視（run_monitoring）は "環境にかかわらず本番 sqlite_path を使用する" という挙動に注意。ペーパートレード時の監視記録を本番 DB に混ぜたくない場合は設定を調整する必要がある。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離するよう設計されている。
- .env の自動ロードはデフォルトで有効。テストや特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- process_priority / CPU affinity の設定は OS 権限に依存するため、失敗しても警告ログを出力して継続する設計。
- ログは既定で stdout に出力され、logs/<app_name>.log に日次ローテートでファイル出力される（logs ディレクトリ作成に失敗するとファイル出力は無効化）。

今後の予定（例）
- factor_research の完全実装（各指標の SQL 実装と Z スコア正規化の統合）
- Strategy/Execution 周りの統合テスト、BrokerClient の具体実装（kabuステーション向け）
- config/*.yaml の雛形生成ツールやサンプルの充実

---

（この CHANGELOG はコードベースの内容に基づき推測して作成されています。実際のリリースノートとして用いる場合は差分・コミットログを参照して調整してください。）