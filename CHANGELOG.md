CHANGELOG
=========

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
（コードベースから推測して作成した変更履歴です）

Unreleased
----------
- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-19
-------------------
初回公開リリース。主要な機能追加とユーティリティを含みます。

### 追加 (Added)
- 実行エントリ
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に完全分離して記録する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番 sqlite_path を使用する挙動を採用。
- 設定管理・セットアップ
  - config.py: 環境変数/​.env 読み込みと Settings クラスを実装。プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込みをサポート。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - config_setup.py: インタラクティブな .env ウィザードを追加（対話式で .env を作成・更新）。
  - validate_config.py: 起動前の設定検証 CLI を追加。--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。stdout 出力（StreamHandler）と日次ローテーションのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をフォールバック。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。アクセス権限不足や未対応 OS 時は警告を出して安全にスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights)を実装。全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
  - portfolio/position_sizing.py: position sizing（risk_based / equal / score）実装。lot_size（単元）丸め、max_position_pct/ max_utilization/ cost_buffer による aggregate cap、スケーリングと端数配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier) を実装。未知レジームはフォールバック (1.0)。
  - portfolio/__init__.py: 上記 API をエクスポート。
- モニタリング / 実行の DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視テーブルの存在を保証（冪等）。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。コマンドライン引数で期間指定、DB パス指定が可能。
- 研究用モジュール（部分実装）
  - research/factor_research.py: DuckDB 接続を受けてファクター（Momentum 等）を計算するための基盤を追加（モメンタム計算のインターフェースや定数を定義）。DuckDB の prices_daily / raw_financials を参照する設計。

### 変更 (Changed)
- 実行・監視起動時の振る舞い
  - run_execution: 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っている場合は起動を中止するロジックを追加。
  - run_monitoring: 停止フラグ検知で安全にループを抜ける設計。check_once() 内で例外が発生してもループ継続（ログ出力して次ポーリングへ）。
- 環境変数パースの堅牢化
  - config._parse_env_line: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォートなしは '#' の直前が空白/タブ時のみコメントとみなす）など多数のケースを扱うよう改良。
  - .env 読み込み順序を OS 環境 > .env.local > .env と明確化。既存 OS 環境を保護する機能を実装。
- ロギングのデフォルトと挙動
  - logging_setup: stdout へ出力（stderr ではない）することで cron 等でのリダイレクトを考慮。ログディレクトリ作成に失敗してもプロセスが継続するよう安全にフォールバック。
- process_priority の安全策
  - 権限不足やプラットフォーム差分で例外を握りつぶし警告ログで通知するよう改善（起動スクリプト冒頭で優先度を "high" に設定する習慣を採用）。

### 修正 (Fixed)
- .env 読み込み時のファイル読み込み失敗での警告強化（warning を出力し処理継続）。
- paper_verification_report:
  - P95 パーセンタイル計算ロジックを実装（空データ対応で None を返す）。
  - DB が存在しない場合のエラーメッセージと使用方法の案内を追加。
- settings の各プロパティで不正値に対して明示的な例外を投げる（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。

### ドキュメント（コード内コメント）改善 (Documentation)
- 各モジュールに使用例・設計方針・注意点を詳細に追記（PortfolioConstruction.md / StrategyModel.md への言及、将来の拡張 TODO 等）。
- config_setup と validate_config にコマンド使用例を追記。

### 既知の制限 / 注意点 (Known issues & Notes)
- monitoring は KABUSYS_ENV に関わらず settings.sqlite_path（本番 DB）を参照する設計になっているため、開発環境での運用時は監視 DB の分離に注意が必要。
- position_sizing の price が欠損（0.0）の場合、現在はスキップするのみ。将来的に前日終値や取得価格でのフォールバックを検討する旨コメントあり。
- research/factor_research.py はモジュールの先頭部分が実装されているが、関数の完全実装が継続中（抜粋あり）。

メンテナンス履歴や今後の変更予定はリポジトリの issue / pull request を参照してください。