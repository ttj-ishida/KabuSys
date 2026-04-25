CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

リリース日や詳細はコード中の実装から推測して記載しています。

Unreleased
----------

- （現在の開発状態）

0.1.0 - 2026-04-25
------------------

Added
- 初期リリースとして以下の主要機能・モジュールを追加しました。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag による。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db を既定）および MockBrokerClient を使用して本番 DB と分離。
  - 設定・環境管理
    - config.py: .env 自動読み込み（.env.local を優先）・環境変数パーサ実装。多数の設定プロパティ（DB パス、PID/kill flag、しきい値、PAPER_FILL_MODE の検証など）を提供。
    - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。機密項目はマスク表示。
    - validate_config.py: 起動前検証 CLI を追加（--strict オプションで警告も失敗扱いにできる）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース検証などを実施。PyYAML 未インストール時に YAML 検証をスキップして警告を出す。
  - ポートフォリオ構築ライブラリ
    - portfolio.portfolio_builder: シグナル選定・重み計算（等金額・スコア加重）を実装。
    - portfolio.position_sizing: 発注株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、aggregate cap のスケールダウン、コストバッファ考慮等をサポート。
    - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - ユーティリティ
    - utils.logging_setup: stdout ストリームハンドラと TimedRotatingFileHandler（日次、30日分保持）を用いた統一ロギング設定を提供。ログディレクトリ作成失敗時はファイル出力を無効化して続行する挙動。
    - utils.process_priority: Windows / POSIX を透過したプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定を提供。CPU affinity 設定ユーティリティも追加。
  - ツール
    - tools.paper_verification_report: ペーパートレード用 SQLite を解析して稼働率、注文成功率、送信率、レイテンシ等の検証レポートを生成する CLI を追加。日付フィルタ／DB 指定オプションをサポート。
  - その他
    - パッケージバージョンを __version__ = "0.1.0" に設定。

Changed
- 起動時にプロセス優先度を "high" に設定するように run_monitoring / run_execution の各エントリポイントで自動化。
- run_monitoring は KABUSYS_ENV にかかわらず監視用 DB 接続にデフォルトの sqlite_path（本番用）を使用するよう明示。
- run_execution では KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離する挙動を導入（安全性向上）。
- logging_setup の StreamHandler は stdout を用いる仕様に統一（cron / スケジューラとの相性改善）。
- .env 読み込みロジックを強化:
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理を実装。
  - OS 環境変数を保護するための protected 上書き制御を実装。
- Settings クラスで環境値の検証を強化:
  - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等に対する許容値チェックとエラーメッセージを追加。
  - 各種パス（duckdb/sqlite/paper_sqlite/pid/kill_flag）や閾値をプロパティ化して簡単に参照可能に。

Fixed
- MONITOR_POLL_INTERVAL に不正（0 や負数、数値でない文字列）が設定された場合に警告を出しデフォルト 60 秒へフォールバックする処理を追加（time.sleep に渡す値検証）。
- run_execution/run_monitoring における DB 接続の後処理で finally にて必ず接続を閉じるようにしてリソースリークを防止。
- run_execution が既に停止フラグ（data/stop_requested.flag）を検知した場合は起動を中止して早期に終了する安全策を実装。
- ExecutionEngine 起動中に停止フラグが立った場合、engine.stop() を呼んで安全に終了するループ制御を追加。
- run_monitoring のポーリングループ内の monitor.check_once() 呼び出しで発生した例外を捕捉してロガーに出力し、ループを継続することで監視プロセスの安定性を向上。

Security
- config_setup による .env 出力時にファイルにシークレット値を直接書く点は必要なため注意を明記（コメント内で .env をコミットしない旨を強調）。
- validate_config で本番環境（KABUSYS_ENV=live）の場合に LINE 通知設定や Kill Switch の設定（KILL_FLAG_CLEAR_ON_START）を警告するチェックを追加し、本番ミスを防止。

Docs / Dev
- 主要モジュールに docstring を追加して使用法・設計方針・引数仕様を明記。tools や portfolio の関数には戻り値やエッジケース（データ不足時の挙動等）の説明を追加。

Known limitations / Notes
- research.factor_research モジュールはファイル内で実装が途中（calc_momentum の途中）になっているため完全実装が必要。
- apply_sector_cap の価格欠損時（price が 0.0）の挙動に TODO コメントが残っており、将来的にフォールバック価格の導入が検討されている。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム非対応時に Warning を出してスキップする実装。期待通り設定できない場合はログメッセージを確認してください。

Breaking Changes
- Settings.PAPER_FILL_MODE の受け入れ値を厳密に検証するようになりました（"instant" | "partial" | "never" | "reject" のみ）。不正値は ValueError を送出します。既存の環境設定に合わせて値を確認してください。
- KABUSYS_ENV と LOG_LEVEL の許容値制約が厳格化されています。不正な値だと起動時に例外が発生します。

Security fixes
- ログディレクトリ作成失敗時はファイルハンドラを作成せずコンソールのみで継続するため、ファイル IO 例外でプロセスが落ちることを防止。

その他
- パッケージの __version__ を 0.1.0 に設定。

以上。必要であれば各変更点を参照して詳細な差分（ファイル別の実装差分や該当行）を出力できます。どのリリースノートを優先して詳細化しますか？