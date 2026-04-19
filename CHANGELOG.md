CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
詳細: https://keepachangelog.com/ja/

Unreleased
---------
- 現在なし

[0.1.0] - 2026-04-19
-------------------
初期リリース — KabuSys のコア機能を実装しました。

Added
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル (data/stop_requested.flag) を検知して安全に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB と MockBrokerClient を使用し、本番 DB と分離（デフォルト data/paper_trading.db）。停止フラグ、PID ファイル管理、デーモンスレッドでの実行制御に対応。

- 設定管理
  - config.py: 環境変数と .env ファイルの読み込み機能を実装。プロジェクトルート自動検出（.git または pyproject.toml を基準）、.env / .env.local の読み込み順序を実装。引用符付き値、export プレフィックス、インラインコメントの取り扱いに対応。各種設定プロパティ（DBパス、PAPER_FILL_MODE、KABUSYS_ENV、閾値等）を提供。
  - config_setup.py: .env 作成/更新の対話式ウィザードを追加（python -m kabusys.config_setup）。既存値読込・マスク表示・保存機能を備える。

- 設定検証ツール
  - validate_config.py: .env と config/*.yaml の検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DBパス・YAML の存在・パース検査、live 環境向けガード等を実装。--strict オプションで警告を FAIL 扱いにできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py: root ロガーの統一設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートされた TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を追加。LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップ。

- プロセス制御ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム向けプロセス優先度設定・CPU affinity ユーティリティを追加。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、権限不足等の例外は警告でスキップする安全設計。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（score 降順、signal_rank タイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等分にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバック（1.0）しログ警告を出力。
  - portfolio/position_sizing.py: 株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。損切り率・リスク率に基づく算出、単元株（lot_size）丸め、総投下金額が利用可能現金を超える場合のスケーリングと残差処理（lot 単位での再配分）を実装。cost_buffer による保守的コスト見積りに対応。

- 解析/レポートツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。期間フィルタ指定（--from / --to / --db）に対応し、稼働率・注文成功率・送信率・P95 レイテンシ等の指標を算出して PASS/FAIL 判定（閾値はソース内定義）を行う。P95 計算、データ存在チェック、SQLite 操作の例外ハンドリングを実装。

- research
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（Momentum / Value / Volatility / Liquidity 計算方針と定数群）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。注: 実装はファイル末尾で継続予定（モジュール骨格の追加）。

- パッケージ設定
  - __init__.py: パッケージバージョン __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に追加。

Changed
- 監視・実行の DB 接続方針
  - 監視（monitoring）は KABUSYS_ENV に依存せず常に本番用 sqlite_path を使用して監視データを記録するように明示。
  - 実行（execution）は paper_trading モード時に paper_sqlite_path を使用して本番データと分離。

- ログ出力のデフォルトを stdout に統一
  - ログの StreamHandler は stderr ではなく stdout を使用する方針に変更（cron/task scheduler 等でのリダイレクトに配慮）。

Fixed
- 環境変数パーサの強化
  - .env パーサで export プレフィックス、引用符内のバックスラッシュエスケープ、行内コメントの扱いなどを適切に処理するよう改良。

- ポーリング間隔の安全化
  - MONITOR_POLL_INTERVAL の解析で 0 以下や非整数を検出した場合はデフォルトにフォールバックし、time.sleep に渡す不正値を防止。

- 起動・停止の安全性向上
  - run_execution.py で起動前に停止フラグが既に立っていた場合は起動せず即時終了するようにし、実行中は停止フラグで安全に engine.stop() を呼ぶよう調整。
  - init_monitoring_db() を起動時に呼び冪等性を保証（監視テーブルが存在することを担保）。

Security
- なし

Deprecated
- なし

Removed
- なし

Notes / Migration
- .env 自動読み込みはデフォルトで有効だが、テスト環境などで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING_SQLITE_PATH を使用することでペーパートレードのデータを本番監視 DB から完全に分離できます。ペーパートレードの検証やレポート作成時は tools/paper_verification_report.py を利用してください。
- ログ出力先・レベルは LOG_DIR / LOG_LEVEL 環境変数で上書き可能です。

---

今後の予定（例）
- research/factor_research.py のファクター実装完了（Momentum, ATR, など）
- ExecutionEngine / Broker クライアント周りの統合テストとドキュメント整備
- 単体テスト・CI 設定の追加

---