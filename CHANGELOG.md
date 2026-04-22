CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-22
--------------------

Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を使用（本番 DB と分離）。スレッドでエンジンを実行し、data/stop_requested.flag を検知すると安全に停止する。起動時にプロセス優先度を "high" に設定し、PID ファイルを出力する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）。監視は環境に関係なく本番用 sqlite_path を使用し、停止フラグ検知でループを終了する。

- 設定管理とウィザード
  - config.py: .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。.env/.env.local の読み込み順序と保護キー（OS 環境変数を上書きしない仕組み）に対応。細かな .env パース（export 形式、クオート、エスケープ、コメント扱い）を実装。Settings クラスを提供し、各種環境変数の取得と妥当性検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を行う。
  - config_setup.py: 対話式 .env 作成/更新ウィザードを追加。シークレットのマスク表示、選択肢・デフォルト値の提示、保存前確認を備える。

- 検証ツール
  - validate_config.py: 起動前に .env や config/*.yaml の欠落や設定不備を検出する CLI を追加。--strict オプションで警告も失敗として扱う。YAML パーサ（PyYAML）がない場合は存在チェックのみを行う。

- ペーパートレード検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、API レイテンシ（P95 など）を集計し、閾値に基づく PASS/FAIL 判定を出力する。期間指定（--from / --to）と DB パス指定（--db / 環境変数）をサポート。

- ポートフォリオ構築/資金配分モジュール
  - portfolio/portfolio_builder.py: シグナル選定（スコア降順）、等金額配分、スコア加重配分を実装。スコア全0時は等金額にフォールバックするロジックを追加。
  - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap を実装（当日売却予定銘柄の除外、"unknown" セクター扱いの注意点）。市場レジームに基づく資金乗数 calc_regime_multiplier を実装（bull/neutral/bear にマッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に基づく発注株数決定を実装。単元株（lot_size）丸め、1 銘柄上限・aggregate cap、手数料・スリッページを見積る cost_buffer、利用可能現金に応じたスケールダウンロジックを備える。

- ユーティリティ
  - utils/logging_setup.py: 全起動スクリプト共通のロギングセットアップを実装。stdout（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを考慮。
  - utils/process_priority.py: cross-platform（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。psutil を用い、権限不足や未実装環境では警告を出してスキップするよう実装。

- リサーチ（計算）モジュール
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け prices_daily / raw_financials を参照する設計）。モメンタム等の定数・方針の定義を含む（関数の続きは実装中）。

Changed
- パッケージ初期化
  - __init__.py にバージョン "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

Fixed
- なし（初版のため特定のバグ修正履歴はなし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 備考
- 設定やファイルパス関連は既定で data/ 以下を利用する設計になっているため、運用環境では .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH などを明示的に設定することを推奨します。
- run_monitoring と run_execution は停止を data/stop_requested.flag により協調するため、運用時は該当ファイルの設置/削除によりプロセスの開始停止を制御できます。
- PAPER_FILL_MODE の妥当性チェックや KABUSYS_ENV の制約により、誤設定があれば起動時に例外が発生するため .env の作成後に validate_config で検証するワークフローを推奨します。