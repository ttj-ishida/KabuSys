CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

最新更新: 2026-04-24

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- 初回公開リリース。
- 実行系 / 監視系起動スクリプトを追加
  - run_execution.py：ExecutionEngine 起動スクリプトを提供。KABUSYS_ENV=paper_trading 時はペーパートレード専用 DB（data/paper_trading.db）と MockBrokerClient を使用する設計。
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag ファイルを検出して行う。
- 設定管理・ウィザード・検証
  - config.py：.env 自動読み込み（.env → .env.local、OS 環境変数を保護）と Settings クラスを提供。各種環境変数の取得・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - config_setup.py：対話式 .env 作成／更新ウィザードを追加。シークレット項目のマスク表示や選択肢サポート、.env への書き込み機能を提供。
  - validate_config.py：起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML 利用時）・本番向けガードを検証。--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py：共通ログ設定を提供。コンソール (stdout) と日次ローテートファイルハンドラをルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py：プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX 対応）と CPU affinity 設定ユーティリティを追加。アクセス拒否など失敗時は警告を出して安全にフォールバック。
- ポートフォリオ構築関連モジュール
  - portfolio/portfolio_builder.py：候補選定（スコア降順、signal_rank によるタイブレーク）と等重・スコア重み付けを実装。
  - portfolio/risk_adjustment.py：セクター集中上限適用（既存保有を考慮）とレジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - portfolio/position_sizing.py：発注株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積）を考慮。
  - portfolio/__init__.py：上記関数群をまとめてエクスポート。
- 分析・研究モジュール（初期実装）
  - research/factor_research.py：DuckDB 上の prices_daily/raw_financials を利用したファクター計算の骨組み（Momentum/Value/Volatility/Liquidity 等）を追加（関数インターフェース・定数を含む）。
- 運用ツール
  - tools/paper_verification_report.py：Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB 指定可能。

Changed
- なし（初回リリース）

Fixed / Robustness
- .env パーサーを強化
  - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、行末コメント処理の改善によりより実用的な .env の解析を実装。
  - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポートを追加（テスト用途を想定）。
  - .env.local を .env の上書きとしてロードする際に OS 環境変数を保護する仕組みを導入。
- run_monitoring.py / run_execution.py の安全性向上
  - 起動時にプロセス優先度を先に設定するように統一。
  - DB 初期化処理（init_monitoring_db）を起動前に呼び出し、監視テーブルの存在を冪等性を保って保証。
  - stop flag / kill flag を用いた安全な停止処理を採用（ファイル検知によるグレースフルシャットダウン）。
- logging_setup.py の堅牢化
  - ログディレクトリ作成失敗時にアプリケーションを止めず、ファイルハンドラ作成失敗をログ出力してフォールバックするように変更。
- process_priority.py のフォールバック
  - 未対応 OS や権限不足時には警告ログを出し、処理をスキップするようにして起動失敗を避ける実装に。

Security
- config_setup の対話・出力においてシークレット項目はマスク表示（保存時は平文で .env に書き出すため .env の取扱い注意を明記）。

Notes / その他
- 設計方針メモが各モジュールに付与されており、将来的な拡張点（例: 銘柄ごとの lot_size 管理、価格フォールバック、より詳細なレジームハンドリング等）が明記されている。
- バージョンはパッケージルートの __init__.py にて 0.1.0 として定義。

参考: 主要な環境変数・ファイルパス（デフォルト）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_DIR: logs/
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用、デフォルト 60）
- data/stop_requested.flag によるプロセス停止制御

今後の予定（TODO / 想定拡張）
- factor_research の完全実装（各ファクターの SQL 実装・正規化）
- 銘柄別 lot_size のサポート（stocks マスタの導入）
- 監視・実行コンポーネントのさらなるエラーハンドリング強化と単体テスト整備
- CLI ドキュメント整備とリリースパッケージ化

-----