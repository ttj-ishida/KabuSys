注意: 以下は提示されたソースコードの内容から推測して作成した CHANGELOG です。コミット履歴がないため、機能追加・変更点・修正点はコード上の実装・ドキュメント文字列から推測しています。必要に応じて日付や詳細を差し替えてください。

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

変更履歴フォーマットは Keep a Changelog 準拠（日本語）です。

Unreleased
----------
- (なし)

0.1.0 - 2026-04-25
------------------
Added
- 実行スクリプトを追加・整備
  - run_execution.py: ExecutionEngine を起動するエントリポイント。環境によりペーパートレード専用 DB を使用し、MockBrokerClient を利用可能。プロセス優先度の設定、PID ファイル管理、停止フラグ検知、スレッド管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定可能。停止フラグの検出により安全に終了する仕組みを搭載。

- 設定管理・初期化ツール
  - config.py: .env 自動読み込み機能を実装（.env < .env.local の優先度、OS 環境変数の保護）。環境変数のパースを強化（export プレフィクス、クォート内エスケープ、インラインコメント処理等）。Settings クラスを提供し、アプリ設定の一元化（パス、閾値、動作モード等）。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。既存値の読み込み・マスク表示・保存をサポート。
  - validate_config.py: 起動前に .env および config/*.yaml の妥当性をチェックする CLI を追加。--strict オプションで警告をエラー扱いに可能。

- ポートフォリオ構築モジュール（純粋関数）
  - portfolio.portfolio_builder: シグナルから候補抽出、等金額/スコア加重の重み計算を実装。
  - portfolio.position_sizing: ポジションサイズ計算ロジックを実装（risk_based / equal / score の配分方法、単元丸め、aggregate cap スケーリング、cost_buffer の考慮）。
  - portfolio.risk_adjustment: セクター上限適用ロジック（既存保有反映、売却候補除外）および市場レジームに基づく投下資金乗数計算を実装。

- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテートされる TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力を無効化してフォールバックする堅牢な実装。
  - utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティ（nice / HIGH_PRIORITY_CLASS のラッパ）。CPU affinity 設定ユーティリティも提供。
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95 など）を計算して PASS/FAIL 判定を行う。

- 分析基盤
  - DuckDB を利用した分析パス（duckdb_path 設定）を導入し、research/factor_research.py（ファクター計算の基礎）などが DuckDB 接続を受け取って処理する設計を追加。

Changed
- DB 分離の明確化
  - run_execution.py: KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）を使うようにし、本番 DB と完全分離する設計に。
  - run_monitoring.py: 監視用途（SystemMonitor）は環境にかかわらず本番用 sqlite_path を使用する旨を明記（監視データは一元管理）。

- .env の自動読み込み順序と保護
  - config.py: 自動ロードの挙動は OS 環境変数 > .env.local > .env の優先度に設定。プロジェクトルート未検出時は自動ロードをスキップ。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。OS 環境変数は protected として上書きを防止。

- ログ設定のデフォルト・挙動
  - setup_logging: ログレベルとログディレクトリの解決順を明確化。既存ハンドラを洗い替えして重複出力を防止する実装に。

Fixed
- リソース解放と例外耐性
  - run_monitoring.py / run_execution.py: finally ブロックで sqlite/duckdb 接続を確実にクローズするように実装。run_monitoring のポーリング中に monitor.check_once() で例外が発生してもループを継続するよう例外捕捉を追加。
  - run_execution.py: スレッド管理中に停止フラグを検知すると Engine.stop() を呼び安全に終了する処理を追加。

- .env パーサの堅牢化
  - config._parse_env_line: export プレフィクス対応、クォート内のエスケープ処理、インラインコメントの扱いなどを実装して .env の多様な記法に対応。

- paper_verification_report のレポート計算
  - P95 計算、NULL（データ不足）時の出力、SQL の日付フィルタリングなどの実装で、DB が欠けている場合でも Graceful に N/A を表示するように改善。

Deprecated
- なし（このバージョンでの明示的な非推奨 API はなし）

Removed
- なし

Security
- なし（明示的なセキュリティ修正はソースコードコメントからは確認できず）

Notes / Known limitations (コードコメントに基づく注意事項)
- run_monitoring は明示的に「環境にかかわらず本番 sqlite_path を使用する」としているため、開発やペーパートレード環境で監視データを分離したい場合は注意が必要（設定での調整が必要）。
- portfolio.risk_adjustment.apply_sector_cap は price_map に 0.0 が含まれる場合にエクスポージャーを過小見積りする可能性があり、将来的に価格フォールバック（前日終値等）が必要である旨の TODO が残っている。
- calc_regime_multiplier は未知のレジームで 1.0 にフォールバックし警告を出す（仕様上の安全弁）。
- utils/process_priority.set_cpu_affinity / nice の呼び出しはプラットフォーム依存の権限 (chmod / CAP_SYS_NICE 等) に影響を受け、権限不足時は警告を出してスキップする。
- .env 自動読み込みはプロジェクトルート (.git / pyproject.toml) を起点に行うため、配布後にルートが特定できない環境では自動ロードがスキップされる点に注意。

参考
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として管理されています。

もし実際のコミット/リリース履歴を元にしたより正確な CHANGELOG が必要であれば、git のログやリリースノート（コミットメッセージ）を提供してください。