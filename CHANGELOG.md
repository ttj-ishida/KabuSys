CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
https://keepachangelog.com/ja/1.0.0/

フォーマット:
- Unreleased: 今後の変更（現状なし）
- バージョン単位でのリリース履歴（下に初回リリースを記載）

Unreleased
----------
- なし

[0.1.0] - 2026-04-18
--------------------
Added
- 初回公開リリース。
- 基本アーキテクチャおよび起動スクリプトを追加:
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の際はペーパートレード用 DB を使用し MockBrokerClient を利用する設計。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）による安全停止に対応。
- 環境設定・検証ツール:
  - config_setup.py: 対話式 .env 作成ウィザード（.env の生成・更新を支援）。
  - validate_config.py: 起動前の環境変数・config/*.yaml の検証 CLI（--strict オプションで警告も失敗扱いに）。
  - config.py: 環境変数の自動読み込み（.env, .env.local の順、OS 環境変数は保護）、各種設定取得ラッパー（Settings クラス）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
- データベース関連:
  - 設定で DuckDB / SQLite のパスを扱うプロパティを実装（Settings.duckdb_path, Settings.sqlite_path, Settings.paper_sqlite_path 等）。Monitoring は環境に関わらず本番 sqlite_path を参照する挙動を明記。
- ポートフォリオ構築ライブラリ（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等金額／スコア重み計算(calc_equal_weights / calc_score_weights) を実装。スコア全零時のフォールバックロジックあり。
  - portfolio/risk_adjustment.py: セクター集中制限の適用(apply_sector_cap)、市場レジームに応じた投下資金乗数(calc_regime_multiplier) を実装。未知レジーム時のフォールバック動作を定義。
  - portfolio/position_sizing.py: 株数決定ロジック(calc_position_sizes)。risk_based / equal / score の各配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。
  - portfolio/__init__.py で公的 API をエクスポート。
- 実行系コンポーネントの組み立て物（Execution 側）:
  - ExecutionEngine 起動時の各種コンポーネント（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler）を統合する流れを実装（run_execution.py）。
  - RiskManager のデフォルト RiskConfig 値をサンプルとして組み込み（max_position_pct, max_utilization 等）。
- 監視関連:
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db）を両スクリプトで保障（冪等）。
- ユーティリティ:
  - utils/logging_setup.py: ルートロガーに StreamHandler(stdout) と 日次ローテーションの TimedRotatingFileHandler を設定する共通ユーティリティを追加。LOG_DIR/LOG_LEVEL の解決順やファイルハンドラ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: Windows/Linux/macOS を透過するプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）ユーティリティを実装。権限不足や未対応 OS の際は警告を出してスキップする設計。
- ツール:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ（--from / --to）、DB 指定（--db / 環境変数）に対応。稼働率、注文成功率、送信率、レイテンシ（P95 など）、リスク却下数等を集計し PASS/FAIL 判定基準を定義（閾値: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
- 研究用モジュール（部分実装）:
  - research/factor_research.py: DuckDB を用いた各種ファクター（Momentum、Value、Volatility、Liquidity）の計算方針および calc_momentum の枠組み（本ファイルは途中まで実装/設計コメント含む）。
- パッケージ情報:
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため過去との比較無し）。

Fixed
- なし（初回リリース）。

Security
- なし（特記事項なし）。ただし .env は Git にコミットしないことを README 等で強調する旨が config_setup に記載済み。

Notes / Usage highlights
- run_execution.py:
  - KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
  - 起動時に data/stop_requested.flag を検出すると起動を行わない、実行中は同フラグで停止できる。
  - 実行プロセスは優先度を "high" に変更しようとする（権限がない場合は警告）。
- run_monitoring.py:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能。1 秒未満や不正値はデフォルト 60 秒にフォールバックし警告を出す。
  - Monitoring は環境に関わらず本番の sqlite_path を使用する点に注意。
- 環境自動読み込み:
  - デフォルトでプロジェクトルート（.git か pyproject.toml を探索）から .env と .env.local を読み込む（OS 環境変数優先）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- PAPER_FILL_MODE:
  - Paper Trading のフィルモード設定（instant/partial/never/reject）をサポート。無効値は ValueError。
- logging_setup:
  - stdout を標準出力に使う設計（cron 等での使い勝手を考慮）。
  - 日次ローテーションで 30 日分保存。

既知の制限 / TODO
- research/factor_research.py は未完（calc_momentum の実装途中）。その他ファクター計算関数の実装が必要。
- position_sizing の price 欠損時のフォールバック（前日終値や原価など）は TODO コメントあり。
- 将来的に単元株（lot_size）を銘柄ごとに管理するための拡張を予定（stocks マスタ導入想定）。

ライセンス、貢献、ドキュメント
- README やドキュメントへの導線（.env 取り扱い、運用手順、監視・停止フラグの運用方法など）の整備を推奨。

---- End of CHANGELOG ----