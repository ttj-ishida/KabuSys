CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.

フォーマット
-----------
- セクションは主に Added / Changed / Fixed / Removed を使用しています。
- バージョンと日付を付記しています（yyyy-mm-dd）。
- 推測に基づく変更点記載があります。実装の振る舞いを元にまとめました。

Unreleased
----------
（今後のリリースで記載）

v0.1.0 — 2026-04-18
-------------------

Added
-----
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を追加。
- 実行スクリプト:
  - run_execution: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離して動作する。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を常に同じ場所で管理）。
- 設定管理:
  - config: .env の自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml）。.env/.env.local の読み込み優先順位を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化に対応。
  - Settings クラスを追加し、環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）をプロパティで型変換・バリデーションして取得可能に。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等のペーパートレード向け設定をサポート。
- 設定 / 検証 CLI:
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を追加。
  - validate_config: .env および config/*.yaml を検証する CLI を追加。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ:
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全て0 の場合は等分配にフォールバックして警告を出す。
  - portfolio.risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。レジームマップ（bull/neutral/bear）とフォールバック動作を提供。
  - portfolio.position_sizing: allocation_method（risk_based / equal / score）に基づく株数計算を実装。単元株（lot_size）丸め、1銘柄上限・aggregate キャップ、コストバッファを考慮したスケーリングと残余配分ロジックを実装。
  - package の __init__ による公開インターフェースを整備。
- ツール:
  - tools.paper_verification_report: ペーパートレードの検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し PASS/FAIL 判定を行う。期間フィルタ(--from/--to)や DB パス指定(--db)に対応。デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90% 等）。
- ユーティリティ:
  - utils.logging_setup: ルートロガーを統一的に設定するユーティリティを追加。stdout ストリームハンドラと日次ローテーションの TimedRotatingFileHandler を設定。ログディレクトリ自動作成、LOG_DIR / LOG_LEVEL の環境変数検出、既存ハンドラのクリア処理を実装。
  - utils.process_priority: クロスプラットフォーム（Windows / POSIX）でプロセス優先度と CPU affinity を設定するユーティリティを追加。set_process_priority("high"|"normal"|"low")、set_cpu_affinity(n) を提供。権限不足や未対応プラットフォームでは警告を出してスキップする安全設計。
- データ処理:
  - research.factor_research: ファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、流動性等を DuckDB 経由で計算する設計。関数は DuckDB 接続と prices_daily 等のテーブルを参照する仕様）。（ファイルは途中まで実装/切出しあり）
- パッケージ情報:
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
-------
- （初リリースのため該当なし）

Fixed
-----
- .env パーサーの堅牢化:
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装し、クォート内のインラインコメントを無視するよう改善。
  - クォートなしの値で '#' をコメントとして扱う条件を厳密化（直前がスペースまたはタブの場合のみ）。
  - _load_env_file にて既存 OS 環境変数を保護する protected 引数を導入し、.env.local の上書きルールを明確化。
- run_execution / run_monitoring の安全停止:
  - プロジェクトの data/stop_requested.flag（および実行用の execution.pid）を用いた外部からの停止フラグ検出を実装。停止フラグ検知時に安全にループを抜ける／実行エンジンを停止する処理を追加。
- DB 分離:
  - Paper Trading 実行時は paper_sqlite_path を使用するようにして、本番 monitoring DB とデータを完全分離するよう実装。
- ロギングの既存ハンドラ重複防止:
  - setup_logging() は既存ハンドラを flush/close してから削除し、二重出力を防ぐ。

Removed
-------
- （初リリースのため該当なし）

Notes / 実装上の注意
-------------------
- run_monitoring は Monitoring の DB 接続に Settings.sqlite_path（本番用 path）を常に使用する実装。開発環境/ペーパートレード環境でも監視データは指定の sqlite_path に保存される点に注意してください。
- process_priority や CPU affinity の設定はプラットフォームや権限に依存します。権限不足の場合は警告ログが出て処理をスキップします。
- position_sizing の aggregate スケーリングでは lot_size（例: 100）単位の丸めを行います。価格が欠損（0 や None）の場合はその銘柄をスキップする設計です（将来的にフォールバック価格を導入する余地あり）。
- validate_config は PyYAML がインストールされていない場合、config/*.yaml の内容検証をスキップして警告を出します。
- .env 自動読み込みはプロジェクトルート検出に依存します。パッケージ配布後や特殊な環境で期待通りに検出できない場合は、明示的に環境変数を設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の改善候補（例）
--------------------
- factor_research の完全実装（ファクター正規化／Zスコア等）と単体テストの追加。
- execution エンジンの詳細実装（注文フロー、再試行、永続化）と監視の連携強化。
- position_sizing の銘柄別 lot_size 対応（stocks マスタからの取込み）。
- ログの構造化（JSON）やメトリクス出力（Prometheus 互換）対応。
- .env パーサーに対するユニットテストの追加。

--- 
（以上）