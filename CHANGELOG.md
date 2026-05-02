CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。

README
------
- 本ファイルはコードベースから推測して作成した変更履歴です。実際のコミット履歴が存在する場合はそちらを優先してください。

Unreleased
----------
- （なし）

[0.1.0] - 2026-05-02
--------------------
最初の公開リリース（推定）。以下の主要機能・改善点・動作仕様を含みます。

Added
- 多数の CLI エントリポイントを追加
  - 実行・監視・レポート生成に関するスクリプト群を提供:
    - run_execution.py — ExecutionEngine の起動スクリプト（スレッドでセッション実行、停止フラグ対応）
    - run_monitoring.py — SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL による間隔制御）
    - run_intraday_monitor.py — ザラ場中監視 CLI（単発・watch モード）
    - run_pre_market_report.py — Pre-Market Report 生成
    - run_market_close_report.py — Market Close Summary 生成
    - run_performance_report.py — 日次/週次/月次の運用成績レポート生成
    - run_position_reconciliation_report.py — ポジション照合レポート（watch モード対応）
    - run_signal_queue_report.py — Signal Queue 確認ビュー生成
    - validate_config.py — 設定検証 CLI（.env と config/*.yaml を検査）
    - config_setup.py — 対話式 .env 作成/更新ウィザード
    - tools/paper_verification_report.py — ペーパートレード検証レポート生成ツール
- 設定管理モジュール (kabusys.config)
  - .env / .env.local の自動ロード機能（プロジェクトルート検出, OS 環境変数を保護）
  - 複雑な .env 行パースに対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントルール）
  - Settings クラスを提供し、環境変数をプロパティとしてアクセス可能に
  - 各種プロパティを公開: DB パス (duckdb/sqlite/paper_sqlite)、KABUSYS_ENV、ログレベル、LINE 設定、Kill Switch 関連、システム閾値（CPU/MEM/DISK）、paper_trading 用設定（PAPER_FILL_MODE）等
- Execution エンジンの環境分離
  - KABUSYS_ENV=paper_trading の場合は専用の SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離
  - BrokerClientFactory によるブローカークライアント生成（paper/live を透過的に扱う想定）
- リスク設定読み込みと検証
  - config/risk_config.yaml を読み込み RiskConfig を構築
  - 各種パラメータ検証を実施（値の存在チェック、型変換、範囲チェック）
    - max_position_pct, max_utilization, max_drawdown: (0, 1] の範囲
    - rate_limit_per_sec, circuit_breaker_errors, circuit_breaker_window_sec: >= 1
    - max_position_pct <= max_utilization を保証
  - 読み込み完了時にログ出力
- 起動時リコンシリエーション & スタートアップサマリ
  - Execution 起動時にリコンシリエーションを実行し、起動レポートを生成・保存（可能なら CLI に出力）
- 監視プロセス関連の動作
  - run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視実行時はプロセス優先度を "high" に設定（set_process_priority 呼び出し）
  - PID ファイルと停止フラグ（data/.../monitoring.pid, stop_requested.flag）により外部から停止制御
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視用 DB は共通）
- レポート系ユーティリティ
  - 各種 report モジュール（performance, pre_market, market_close, signal_queue, position_reconciliation）との連携を想定
  - DuckDB をクエリ対象に用いる（read_only 接続をサポート）
  - 出力形式に CLI テキスト、JSON、Markdown をサポートし、artifacts/ 配下への保存をサポート
- 設定ウィザード
  - config_setup.py により対話式で .env を生成・更新。秘密値はマスク表示、既存値再利用をサポート
  - .env のテンプレート化された書式で保存
- 設定検証ツール
  - validate_config.py により必須環境変数の存在、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検査（PyYAML が無ければ警告）を実施
  - --strict モードで警告を失敗扱いにできる

Changed
- （初期リリースのため主要な「追加」が主体。既知の挙動改善点を実装）
  - .env の自動ロードはプロジェクトルートが検出できない場合はスキップされるように設計（配布後の動作安定化を目的）
  - 一部スクリプトで DB 接続を read-only モードにして安全にクエリするようにした（URI ベースでの接続を使用）

Fixed
- 環境変数の不正値に対するフォールバックとログ出力
  - MONITOR_POLL_INTERVAL が不正（整数に変換できない、0 以下など）の場合はデフォルト（60 秒）にフォールバックし、警告ログを出力
  - PAPER_FILL_MODE の不正値検出時に明示的なエラーを投げることで早期検出
- 各種リソースのクローズ処理を確実に実行
  - 監視ループ終了時・Execution 終了時に sqlite/duckdb 接続をクローズし、PID ファイルをクリーンアップ

Security
- 秘密情報取り扱い注意
  - config_setup と .env の取り扱いに関する注意書きを同梱（.env を Git にコミットしない旨）

Notes / Implementation details（コードから推測）
- Process priority, logging setup, broker factory 等はいくつかのユーティリティモジュール（kabusys.utils.*）に依存しており、環境に合わせた実装が期待される
- run_execution は起動時に利用可能資産（現金 + 保有評価額）を計算し、これを RiskManager の initial_portfolio_value に供給する設計
- 複数の CLI において JSON 出力と保存オプション（--json, --save）が提供され、JSON 時は標準出力の混在を避けるため保存先メッセージを stderr に出す等の配慮がある
- tools/paper_verification_report.py は稼働率、注文成功率、送信率、レイテンシ（P95）の閾値を定義しており、ペーパートレード向けの自動検証を行う

既知の制限（推測）
- 一部の機能（ブローカークライアント、ExecutionEngine, SystemMonitor 等）は別モジュールに依存しており、これらの実装が存在しないとエンドツーエンドで動作しない
- YAML 検証には PyYAML が必要（未インストール時は警告によりスキップされる）

今後の改善提案（推測）
- 詳細なユニット/統合テストの追加（環境依存処理や DB 接続のモック化）
- ログ出力の一貫化・Structured logging の検討
- CLI の共通オプションやヘルプ文の国際化（一貫した英語ヘルプと日本語ヘルプの両立）

参考
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- リリース日（本 CHANGELOG 作成日）: 2026-05-02

----- End of CHANGELOG -----