CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。重要度の高い変更（追加・変更・修正）を日本語でまとめています。

[Unreleased]
------------

- （現在のリポジトリ状態：リリースタグがまだない場合はこのセクションに記載してください）
- （本スナップショットからの差分を作成する場合はここに追記してください）

0.1.0 - 2026-04-21
------------------

Added
- 基本アプリケーション基盤を実装（初期リリース）。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を追加。
- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの .env, .env.local を読み込む）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化対応。
  - .env の行パースで export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント等に対応する堅牢なパーサを実装。
  - Settings クラスにより各種環境変数を型安全に取得可能（DBパス、APIトークン、動作環境、監視閾値、Paper Trading 設定等）。
  - 環境値の検証（許容値チェック・enum 値チェック）を実装（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV/LOG_LEVEL の検証）。
- 環境設定ウィザード（kabusys.config_setup）
  - 対話式 CLI で .env を新規作成 / 更新するツールを実装。
  - シークレット項目のマスク表示や選択肢、デフォルト値のサポート、既存 .env の読み込み・再利用機能を提供。
- 設定検証 CLI（kabusys.validate_config）
  - 起動前に必須環境変数や config/*.yaml の存在・パースを検証する CLI を実装。
  - --strict モードで警告も失敗扱いにするオプションを追加。
  - PyYAML 未インストール時のフォールバックや、本番環境向けの追加チェック（LINE通知設定、KILL_FLAG_CLEAR_ON_START）を実装。
- ログ設定ユーティリティ（kabusys.utils.logging_setup）
  - すべての起動スクリプトで共通のログ設定を提供。
  - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app>.log）を設定。
  - 既存ハンドラをクリアして二重出力を防止、ログディレクトリ自動作成、LOG_DIR/LOG_LEVEL 経由の設定解決を実装。
  - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続するフォールバックを備える。
- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX の差分を吸収し、"high"/"normal"/"low" の優先度設定を提供（psutil に依存）。
  - CPU affinity を最初の N コアにピン留めする set_cpu_affinity を実装。
  - 権限不足や未対応プラットフォーム時に警告を出して安全にスキップする仕組みを実装。
- 実行系エントリスクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine を別スレッドで起動するライフサイクル制御を実装。
    - data/stop_requested.flag による停止フラグで安全に停止する仕組み。
    - 起動時にプロセス優先度を "high" に設定。
    - PID ファイル（data/execution.pid）を利用。
  - 監視ループ起動スクリプト（run_monitoring.py）
    - SystemMonitor を初期化しポーリングループを実行。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は常に本番 sqlite_path を利用（環境にかかわらず監視 DB を共通化する設計）。
    - 停止フラグ（data/stop_requested.flag）、KeyboardInterrupt を検出してクリーンに終了。例外はログに出力して次ポーリングまで待機。
- DB / 分析基盤
  - sqlite3 と DuckDB を併用する設計を採用（監視履歴は SQLite、分析は DuckDB）。
  - init_monitoring_db 呼び出しにより監視用テーブルの存在を保証（冪等）。
- ペーパートレード検証ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の SQLite を読み取り、システム稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を計算してレポート出力する CLI を実装。
  - P95 計算、各種閾値（稼働率 >= 99%、注文成功率 >= 90% 等）を用いた PASS/FAIL 判定を提供。
  - コマンドラインで期間指定（--from / --to）および DB パス指定（--db）に対応。
- ポートフォリオ構築ライブラリ（kabusys.portfolio）
  - 銘柄選定: select_candidates（スコア降順、タイブレークに signal_rank を使用）。
  - 重み計算: calc_equal_weights（等額）、calc_score_weights（スコア比率、全スコアが 0 の場合は等分にフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中の除外ロジック）、calc_regime_multiplier（市場レジームに応じた乗数。bull/neutral/bear をサポート、未知値は警告して 1.0 フォールバック）。
  - 銘柄ごとの発注株数算出: calc_position_sizes
    - allocation_method="risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）で丸め処理、1 銘柄上限（max_position_pct）、ポートフォリオ合計上限（available_cash / max_utilization）を考慮。
    - コストバッファ（cost_buffer）を考慮した保守的見積り、合計が available_cash を超える場合のスケールダウンと端数配分アルゴリズム（fractional remainder に基づく追加配分）を実装。
    - 価格欠損時にはスキップし、ログでデバッグ情報を出力。
- リサーチ（kabusys.research.factor_research）
  - DuckDB を用いたモメンタム等ファクター計算の骨子を実装（モメンタムの計算期間定義や P95 計算用ユーティリティ等）。（一部実装途中）

Changed
- ロギングのデフォルト設定を統一（stdout を使用、ログファイルは logs/ 以下に日次ローテーションで保存）。
- 環境依存処理（プロジェクトルート探索、.env 自動読み込み）を __file__ ベースの探索に変更し、CWD の影響を受けにくくした。

Fixed
- MONITOR_POLL_INTERVAL に 0 以下や不正な文字列が指定された場合に time.sleep で ValueError にならないよう、安全にデフォルトにフォールバックする処理を追加。
- ログハンドラの多重設定を防止するため、setup_logging で既存ハンドラを明示的に flush/close/削除するように変更。
- process_priority / set_cpu_affinity で権限不足や未対応プラットフォームの例外を捕捉し、警告でスキップするように変更（サービス運用時の安定性向上）。
- .env 読み込みでファイルオープン失敗時に警告を出して処理を継続するように変更。

Security
- シークレット項目（J-Quants / kabu API パスワード / LINE トークン等）は config_setup の UI でマスク表示。.env ファイルにプレーンテキストで保存される点は注意喚起（.env を Git にコミットしない旨の注記あり）。

Notes / 限界事項
- research.factor_research の一部関数は実装途中（コメント・定数定義はあるが実装継続が必要）。
- position_sizing で price が欠損（0.0）の場合、現在はスキップするのみでフォールバック価格（前日終値等）を参照しない。将来的な改善候補として注記あり。
- Paper Trading の検証ツールは SQLite のスキーマ（system_status, trade_logs, risk_logs 等）に依存する。スキーマが存在しない/異なる場合は適切なハンドリング（OperationalError のフォールバック実装あり）。

Acknowledgements
- DuckDB, psutil を用いた実装により、高速な分析と OS 操作（優先度 / affinity）の抽象化を行っています。

今後の予定（候補）
- research.factor_research の完成（ファクター計算ロジックの実装完了）。
- 銘柄別 lot_size のサポート（stocks マスタ参照による銘柄別単元対応）。
- .env の暗号化保存やシークレット管理の改善（Vault 等の導入検討）。
- 単体テスト・統合テストの拡充、CI パイプラインでの自動検証。

-----
（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴がある場合はコミットメッセージに基づいて差分を詳述することを推奨します。）