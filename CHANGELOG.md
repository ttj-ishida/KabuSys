CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

### Added
- 今後のリリース向けに下記の改善・追加予定を記載。
  - factor_research モジュールの未完了箇所（ソースが途中で切れているため完全実装）を完成させる。
  - position_sizing の lot_size を銘柄別に対応する拡張（stocks マスタへの lot_size 統合）。
  - price が欠損した場合のフォールバック（前日終値や取得原価など）実装。
  - テスト支援用のモック・ユーティリティの拡充。

### Fixed
- なし

### Changed
- なし

0.1.0 - 2026-04-11
------------------

### Added
- 基本アーキテクチャと CLI / ユーティリティ類を初版として追加。
  - パッケージバージョンを 0.1.0 として設定（src/kabusys/__init__.py）。
- 環境設定・管理
  - .env 自動ロード機能を実装（プロジェクトルートの .env / .env.local を読み込み、OS 環境変数は保護）（src/kabusys/config.py）。
  - .env のパースは引用符・エスケープ・コメントを考慮して安定的に処理。
  - Settings クラスを提供し、環境変数に基づく型安全な設定アクセスを実現（DB パス、各種閾値、環境判定プロパティ等）。
  - 環境設定ウィザード CLI を実装（python -m kabusys.config_setup）。対話式で .env を作成／更新可能（src/kabusys/config_setup.py）。
  - 設定検証 CLI を実装（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在／パースチェック等を実行（src/kabusys/validate_config.py）。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の際は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカー切替を想定。
    - 停止フラグファイル（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた制御を実装。
    - リスク管理（RiskManager）と Reconciler、OrderManager、OrderRepository の組み立てと Engine の起動ループを実装。
  - SystemMonitor ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- ロギング／プロセス管理ユーティリティ
  - 統一ログセットアップ関数 setup_logging を追加（stdout StreamHandler ＋ 日次ローテートファイルハンドラ）（src/kabusys/utils/logging_setup.py）。
    - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続。
    - LOG_LEVEL / LOG_DIR の解決順とハンドラ二重登録防止を実装。
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収し、"high"/"normal"/"low" の優先度設定を提供。アクセス権限エラー等は警告を出してフォールバック。
    - CPU affinity を最初の N コアに固定する関数を提供。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレーク処理を実装。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコア 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションからセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: market_regime に応じた資金乗数（bull/neutral/bear）を定義、未知レジームは警告して 1.0 にフォールバック。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた発注株数計算（risk_based / equal / score）。
    - 単元（lot_size）丸め、1 銘柄上限・aggregate cap によるスケーリング、cost_buffer による保守的見積り、scaled 時の残差配分ロジックを実装。
  - ポートフォリオ API エクスポート（src/kabusys/portfolio/__init__.py）
- 研究・分析ユーティリティ
  - factor_research モジュールを追加（価格データから Momentum / Value / Volatility / Liquidity を計算する設計開始）。DuckDB を利用する設計（src/kabusys/research/factor_research.py）。※本ファイルは実装途中である箇所あり（ソース末尾が切れている）。
- ツール類
  - Paper Trading 検証レポート生成スクリプトを追加（python -m kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を算出し PASS/FAIL を判定するしきい値を定義。デフォルト DB は data/paper_trading.db（src/kabusys/tools/paper_verification_report.py）。
- データベース関連
  - DuckDB を分析用に利用（duckdb 接続を settings.duckdb_path で解決）。
  - 監視テーブルの初期化を保証する init_monitoring_db 呼び出し（冪等）。
- その他
  - ユーティリティ __all__、モジュール構造、CLI の entrypoint 実装（if __name__ == "__main__": main()）等、実運用を想定した設計。

### Changed
- 初版リリースのため変更点なし（新規機能追加が中心）。

### Fixed
- 初版リリースのため修正履歴なし。

### Security
- セキュアな情報（J-Quants / Kabu パスワード等）は .env に格納する設計。config_setup には .env を絶対に Git にコミットしない旨の注意を追記。

注意事項・既知の制約
------------------
- factor_research.py が途中で切れている（未実装箇所あり）。完全なファクター計算ロジックは追加実装が必要。
- position_sizing の価格欠損時の扱いについて TODO コメントあり（price が 0.0 の場合のフォールバックが未実装）。
- 単元（lot_size）は現状グローバル固定（デフォルト 100）。将来的に銘柄別対応が予定されている（TODO）。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。テスト時に自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
- 本番運用時の安全チェック（validate_config の警告や KABUSYS_ENV=live の追加ガード）を実装しているが、実際の運用では必ず validate_config を実行して設定を確認してください。
- process_priority / cpu_affinity は OS と権限に依存し、失敗時は警告ログを出してスキップするため、安全にフォールバックする設計。

参考: 主要な環境変数
- KABUSYS_ENV (development | paper_trading | live)
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL (run_monitoring 用ポーリング間隔秒)
- PAPER_FILL_MODE (paper_trading 時のフィルモード: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (本番で自動クリアしないことを推奨)

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリース日・細部の設計意図はリポジトリの変更履歴やリリースノートと合わせてご確認ください。