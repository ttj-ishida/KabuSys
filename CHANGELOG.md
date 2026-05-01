# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルではリポジトリのコードから推測される機能追加・改善点をまとめています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正・堅牢性向上
- Security: セキュリティ対応

※日付は本リリース推定日時です（コードからの推測に基づく）。

## [Unreleased]
- 今後の変更等をここに記載します。

## [0.1.0] - 2026-05-01

### Added
- 実行用エントリポイント・CLI を多数追加／公開
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視用 PID / 停止フラグの管理を実装。
  - run_intraday_monitor.py: ザラ場中監視向け CLI を追加。1回実行／watch モード（定期更新）での監視表示と終了ステータス判定を実装。
  - run_pre_market_report.py / run_market_close_report.py / run_position_reconciliation_report.py / run_signal_queue_report.py / run_performance_report.py: 各種レポート生成 CLI を追加。--json / --save / --watch 等のオプションに対応。
  - tools/paper_verification_report.py: ペーパートレード検証用のレポート生成ツールを追加（稼働率、注文成功率、レイテンシ等の指標集計）。
  - validate_config.py: .env および config/*.yaml の設定検証用 CLI を追加。--strict モードにより警告も失敗扱いに可能。
  - config_setup.py: .env を対話式に作成・更新するウィザードを追加。既存 .env の読み込み／既定値表示／機密値のマスク等に対応。
  - run_position_reconciliation_report.py: ブローカーとローカルレポジトリを用いたポジション突合（差異検出） CLI を追加。

- 設定・環境変数管理機能を実装
  - config.py: プロジェクトルート自動検出（.git または pyproject.toml を探索）を実装。自動で .env / .env.local を読み込み（OS 環境変数が優先）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサーの強化: export プレフィックス、クォート（' "）内のバックスラッシュエスケープ、行内コメント扱いの改善に対応。
  - Settings クラスを追加し、J-Quants / kabu API / DB パス / ペーパートレード設定 / 監視閾値等のプロパティ化を提供。paper_fill_mode などの値検証を実装。

- 起動時・実行時の運用上の便利機能
  - 各種スクリプトでプロセス優先度を "high" に設定するユーティリティ呼び出しを統一して使用（set_process_priority を利用）。
  - 実行中の PID ファイル書き出しと終了時のクリーンアップ処理を実装（monitoring.pid, execution.pid 等）。
  - 停止フラグ（data/stop_requested.flag）検出による安全なシャットダウン処理を各種スクリプトに実装。
  - レポート出力: CLI 表示（人間向けテキスト）と JSON 形式出力を選択可能。--save により artifacts 配下へ保存。

- モニタリング DB 初期化用関数により監視テーブルの冪等な準備を行う init_monitoring_db を使用。

- ペーパートレード検証レポートで P95 計算、各種閾値（稼働率・成功率・レイテンシ）に基づく判定ロジックを追加。

### Changed
- プロジェクトルート探索ロジックの導入により、カレントワーキングディレクトリに依存しない環境変数自動ロードを実現。
- DB 接続挙動の明示化
  - run_monitoring や run_execution 等で sqlite3 と duckdb の接続を確立し、finally ブロック等で確実にクローズするよう整理。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する旨を明示（監視データは環境に依存させない方針）。

### Fixed / Robustness
- .env 読み込みの堅牢化
  - ファイルが開けない場合は警告を出して処理継続（warnings.warn）。
  - 読み込み上書き（override）時に OS 環境変数を保護する protected 引数を導入。
- 設定検証の充実
  - validate_config にて必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在チェックおよび PyYAML がない場合のフォールバックメッセージを実装。
  - 本番環境（KABUSYS_ENV=live）特有の注意喚起（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の危険性）を追加。
- Execution 起動フローの堅牢化
  - 起動時にブローカーから現金・ポジションを取得して初期総資産を算出し、RiskManager の初期値に反映。risk_config.yaml のパースエラー・キー欠落・範囲外値に対する分かりやすい例外メッセージを実装。
  - Reconciler による起動時リコンシリエーション処理を実行し、Execution Startup Summary の生成失敗時は警告を出して起動継続。
  - ExecutionEngine をバックグラウンドスレッドで実行し、停止フラグ検出時に安全に停止させるロジックを実装（engine.stop() 呼び出しなど）。
- Monitoring の例外耐性向上
  - monitor.check_once() が例外を投げてもループを続行して次回ポーリングまで待機するように例外捕捉とログ出力を追加。
  - ポーリング間隔の環境変数 MONITOR_POLL_INTERVAL の不正値に対しては警告を出してデフォルト値にフォールバック。

### Documentation / Misc
- パッケージバージョンを __version__ = "0.1.0" として追加。
- 各 CLI のヘルプ・usage（コメント）を整備し、実行例や引数説明を記載。
- config_setup のウィザードで作成される .env のテンプレート出力（_write_env）を整備。機密情報は出力時にマスクして表示。

### Security
- .env ファイルに関する注意喚起を config_setup で明記（.env を Git にコミットしないこと等）。
- OS 環境変数を上書きしない既定動作と、上書き時の保護（protected）により意図しない環境変数の上書きを防止。

---

注: 本 CHANGELOG は提供されたコードの内容から推測して作成したものであり、実際のコミット履歴や設計意図と完全に一致しない場合があります。必要であれば、各ファイルの関数コメントやログ出力メッセージを基にさらに詳細な項目へ分割して記載できます。