CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。
バージョン番号はパッケージの __version__ に合わせています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-23
------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本機能群を追加。
  - コアモジュール
    - kabusys.config: 環境変数 / .env の読み込みと設定オブジェクト（Settings）。.env 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、厳密な値検証（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
  - 起動スクリプト / CLI
    - run_monitoring: SystemMonitor 用ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）検出で安全終了。監視用 DB 初期化と duckdb 接続を行う。
    - run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading のときは専用のペーパートレード用 SQLite を使用し MockBrokerClient による完全分離をサポート。停止フラグ検出でエンジン停止、PID ファイル管理、デーモンスレッドでの実行管理を実装。
    - validate_config: .env と config/*.yaml の起動前検証ツール。必須環境変数チェック、パスの存在確認、YAML パーサがない場合のスキップ処理、KABUSYS_ENV=live に対する追加ガード、--strict オプションをサポート。
    - config_setup: 対話式 .env 作成/更新ウィザード。シークレットのマスク、選択肢とデフォルト提示、保存確認を実装。
  - ポートフォリオ構築（純関数群・DB 非依存）
    - portfolio.portfolio_builder: 候補選定（select_candidates）、等重配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - portfolio.risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - portfolio.position_sizing: 株数決定ロジック（calc_position_sizes）。risk_based / equal / score の割付方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的コスト見積り。
  - ユーティリティ
    - utils.logging_setup: ルートロガー設定ユーティリティ。コンソール（stdout）と日次ローテートされたログファイルを設定、既存ハンドラのクリア、LOG_DIR/LOG_LEVEL の解決ロジック、ファイルハンドラ作成失敗時のフォールバックを実装。
    - utils.process_priority: psutil を用いたプロセス優先度設定と CPU affinity 設定ユーティリティ。Windows / POSIX の差分吸収、失敗時の警告処理を実装。
  - モニタリング / データベース
    - monitoring.monitoring_db（初期化呼び出しを統一して監視テーブル存在を保証）
  - ツール
    - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプト。稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。日時範囲フィルタおよび DB パス指定（環境変数/オプション）をサポート。
  - 研究用モジュール（部分実装含む）
    - research.factor_research: Momentum 等のファクター計算を開始（DuckDB の prices_daily / raw_financials を前提に計算する設計）。（コードは一部未完／続きあり）

Changed
- 初回公開のため履歴はすべて Added として記載。

Fixed / Improved
- MONITOR_POLL_INTERVAL のパースを堅牢化: 不正な値や 0 以下の値を検知し、デフォルト（60 秒）へフォールバックして警告ログを出力。
- .env 読み込みの強化:
  - export プレフィックスやクォート内のエスケープ、インラインコメントの扱いなどを正しくパース。
  - _load_env_file による override/protected 制御で OS 環境変数を保護。
- validate_config:
  - PyYAML 未インストール時に YAML 検証をスキップし警告を出力するよう改善。
  - 設定ファイルの存在チェック・パースエラー検出を実装。
  - live 環境向けの追加安全チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装。
- logging_setup:
  - 既存ハンドラをフラッシュ/クローズしてから削除し二重登録を防止。
  - ログディレクトリ作成失敗時はコンソール出力のみで継続するフォールバック実装。
  - stdout を使用することで cron 等でのリダイレクト運用に対応。
- process_priority / set_cpu_affinity:
  - クロスプラットフォーム対応。権限不足や未実装 API に対して警告でスキップするように改善。
- run_execution:
  - paper_trading 環境では専用 SQLite を使用することで本番 DB と完全分離。
  - 起動時に停止フラグが立っている場合は起動をスキップする安全措置を追加。
  - エンジン停止要求時に thread.join(timeout=...) を使って穏やかに終了を待機。
- run_monitoring:
  - 監視ループでの例外をキャッチしてログ出力し、次のポーリングに継続するようにして安定性を向上。
  - 最終的に sqlite/duckdb 接続を必ずクローズするように修正。

Security
- .env ファイルの生成ウィザードでシークレット値（トークン／パスワード）をマスクして表示するように改良。

Known issues / Notes
- 一部モジュール内に将来の拡張や注意点を示す TODO コメントあり:
  - portfolio.risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャー過小評価となる問題が注記され、前日終値や取得原価などのフォールバック価格を使用する拡張を検討する旨が記載されています。
  - research.factor_research はファイル末尾で実装が途中となっている箇所があります（今後の完成が予定されます）。
- calc_regime_multiplier は未知のレジームに遭遇した場合に警告を出し 1.0 でフォールバックします（保守的な設計）。

Credits
- 初期実装: リポジトリ内の各モジュール群に基づく機能群をまとめて公開。

脚注
- デフォルトのファイルパス / 環境変数など主要なデフォルト:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_DIR: logs/
  - デフォルトログレベル: INFO
  - MONITOR_POLL_INTERVAL のデフォルト: 60 秒

もし特定の変更点をより詳細に分割して欲しい、またはリリース日やバージョンを別にしたい場合は教えてください。