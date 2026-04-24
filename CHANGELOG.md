CHANGELOG
=========

すべての重要な変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）の形式に準拠して記載しています。

Unreleased
----------

（現在の差分はすべて 0.1.0 として初回リリースに含まれています。将来の変更はここに追加してください。）

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アプリケーション構成とバージョン
  - パッケージバージョンを __version__ = "0.1.0" として追加。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクトの data/stop_requested.flag により判定。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する点を明確化。
    - 起動時にプロセス優先度を "high" に設定。
    - SQLite / DuckDB 接続の初期化、例外時のログ出力、正しいクローズ処理を実装。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（BrokerClientFactory 経由）を使用し、
      Paper Trading 用 DB（デフォルト data/paper_trading.db）へ記録することで本番 DB と完全分離。
    - engine を別スレッドで起動し、stop flag による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定・環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートの .env / .env.local を環境変数と適切にマージ）。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD オプションを追加（テスト用途）。
    - .env パースロジックはクォート、エスケープ、インラインコメント等に対応。
    - Settings クラスを導入し、各種環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、PID_FILE_PATH、各種閾値やフラグ等）をプロパティ経由で取得できるようにした。
    - 環境値の検証（有効な KABUSYS_ENV 値、LOG_LEVEL、PAPER_FILL_MODE の有効値など）を実装。

- 設定補助ツール / 検証
  - config_setup.py
    - .env の対話式ウィザードを追加。既存 .env 読み込み、各項目の入力（選択肢・マスク・デフォルト）、確認・保存をサポート。
    - .env ファイルの生成テンプレートを追加（重要な注意書きとセクション分け）。
  - validate_config.py
    - 起動前に環境変数・config/*.yaml の妥当性を検証する CLI を追加。
    - 必須 env の未設定検出、プレースホルダ値検出、YAML パーサ（PyYAML）有無に応じた挙動、KABUSYS_ENV=live 向け追加警告（LINE 設定や Kill Switch 設定）を実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテート（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 等の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバック処理を実装。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定（Windows の priority class、POSIX の nice）を提供。
    - CPU affinity を最初の N コアに固定するユーティリティも提供。
    - アクセス権限や未実装関数に対する安全な警告処理を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順 + signal_rank タイブレーク）。
    - 等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコア0 の場合は等金額にフォールバック）を追加。
  - portfolio/risk_adjustment.py
    - セクター集中上限チェック（apply_sector_cap）を追加。既存保有のセクター暴露に基づき当日新規候補を除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）を追加（bull/neutral/bear をマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数決定ロジックを追加。allocation_method による分岐（risk_based / equal / score）や
      単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash を超える場合のスケーリングと残差分配）を実装。
    - cost_buffer（手数料・スリッページの保守的見積り）を考慮。

- リサーチ・ファクター計算（基盤）
  - research/factor_research.py
    - モメンタムや移動平均乖離、ATR、流動性等のファクター計算基盤を追加（DuckDB 接続を受け、prices_daily / raw_financials を想定）。
    - 関数群と定数（期間）を定義。設計方針として外部 API に依存せず DuckDB + SQL/Python で計算する方式を採用。
    - （ファイルは途中まで実装。モメンタム計算の開始処理が含まれているが、完全実装は今後の作業想定。）

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 指標: システム稼働率、注文成功率（fill）、送信率（send）、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - CLI で期間指定（--from / --to）および DB 指定（--db、環境変数 PAPER_TRADING_SQLITE_PATH を優先）をサポート。
    - パス/閾値（稼働率 99%、fill 90%、send 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を起動スクリプトから呼ぶことで、監視テーブルが存在することを保証（冪等）。

Fixed
- .env パーサの強化
  - クォートあり／なしの処理、バックスラッシュエスケープ、インラインコメントの扱い、export プレフィックス対応などを実装し、.env 読み込みの堅牢性を向上。

- ログセットアップの堅牢化
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時にフォールバックして標準出力のみで継続するようにした。

Security
- .env 出力テンプレートで .env を絶対に Git にコミットしないよう明記（config_setup が .env を生成する際に注意喚起を追加）。

Changed
- なし（初回リリース）

Removed
- なし

Breaking Changes
- 監視プロセスは設計上「環境にかかわらず」本番用 sqlite_path を参照する仕様を明記（run_monitoring）。運用上、monitoring が paper_trading DB を参照するような変更はないため、既存の期待と異なる場合は注意。

Notes / Known limitations
- research/factor_research.py はファイル末尾で未完の部分があり、ファクター計算の一部（モメンタム等の実装の続き）は今後の実装が必要。
- position_sizing の lot_size は現在全銘柄共通。将来的には銘柄ごとの lot_map を受け取る設計拡張を想定。
- apply_sector_cap は price_map に価格が欠損（0.0）がある場合にエクスポージャーが過少見積もられる可能性がある旨を TODO として残している。

今後の予定（例）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / Monitoring のエンドツーエンドの統合テスト追加
- BrokerClient の具象実装とペーパートレード / 本番の切り替えに関するドキュメント強化

--- 

（補足）
- 本 CHANGELOG は提供されたコードベースの内容から機能・挙動を推測して作成しています。実際の変更履歴やコミットログと差異がある可能性があります。必要であれば、各項目についてさらに細かいファイル単位の差分説明や担当者情報を付記します。