Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

現在バージョン
-------------

- 0.1.0 - 2026-04-18

[0.1.0] - 2026-04-18
--------------------

Added
- 初期リリース: KabuSys 自動売買システムのコア機能を実装。
- 実行用スクリプトを追加:
  - run_execution.py — ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて paper_trading 用 DB/MockBroker を分離、停止フラグ / PID 管理、デーモンスレッドでの実行制御）。
  - run_monitoring.py — SystemMonitor ポーリングループの起動スクリプト（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止フラグ検知で終了）。
- 環境設定周り:
  - config_setup.py — 対話式 .env ウィザード（秘密項目のマスク表示、既存 .env 読み込み・更新、.env 書き出しテンプレート）。
  - validate_config.py — 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス / config/*.yaml の存在と YAML パース検証、--strict モード）。
  - config.py — 環境変数自動読み込み（プロジェクトルート検出: .git または pyproject.toml 基準）、高度な .env パーサ（export プレフィックス・クォート・インラインコメント対応）、Settings クラス（各種設定プロパティ、値検証、デフォルト）。
- データベース / 解析:
  - duckdb と sqlite の接続サポート（Settings 経由でパス指定）。
  - monitoring_db の初期化を呼び出して監視テーブルの存在を保証する処理を追加（冪等）。
- ポートフォリオ構築ロジック（純粋関数群、メモリ内計算）:
  - portfolio_builder.py — 候補選定（スコア降順 + タイブレーク）、等重み・スコア重みの計算（スコア総和が 0 の場合はフォールバック）。
  - risk_adjustment.py — セクター集中制限（既存ポジションを考慮して新規候補を除外、"unknown" セクターは制限除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバック）。
  - position_sizing.py — 発注株数計算（risk_based / equal / score モード、損切り率・リスク割合に基づく算出、単元株丸め、aggregate cap によるスケールダウンと残余の配分ロジック、cost_buffer による保守的見積り）。
- 研究用モジュール:
  - research/factor_research.py — モメンタム等のファクター計算（DuckDB 経由で prices_daily / raw_financials を参照する設計。ファイル内で多様な指標を計算するための基盤を実装。）
- ユーティリティ:
  - utils/logging_setup.py — 統一的なロギングセットアップ（stdout StreamHandler を使用、日次ローテートの TimedRotatingFileHandler を設定、ログディレクトリ作成失敗時はファイル出力をスキップ）。
  - utils/process_priority.py — Windows / POSIX を吸収するプロセス優先度・CPU affinity 設定ユーティリティ（優先度設定失敗時は警告でスキップ）。
- ツール:
  - tools/paper_verification_report.py — Paper Trading 検証レポート生成ツール（稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均 / max / P95）を計算して判定を出力。PAPER_TRADING_SQLITE_PATH / --db オプションで DB 指定可能、期間フィルタ対応）。
- パッケージ情報:
  - __init__.py にバージョン情報とエクスポート定義を追加（__version__ = "0.1.0"）。

Changed
- ロギング:
  - デフォルトで stdout にログを出力するように設計（cron/Task Scheduler からの利用を想定し stdout/stderr 統合を容易にするため）。
  - 日次ローテーション & 30 日分保持を実装。
  - 既存ハンドラがある場合は一旦 flush/close してから再設定し、二重登録を防止。
- .env の自動読み込み順序:
  - OS 環境変数 > .env.local > .env の順で読み込む実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。既存の OS 環境変数は保護され上書きされない。

Fixed
- .env パーサの堅牢化:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱い、空行・コメント行の無視などに対応。
- Process / OS 互換性:
  - process_priority.set_process_priority は Windows/POSIX の差分を吸収し、失敗時に警告でスキップする安全設計を採用。
- Execution / Monitoring の安全停止:
  - run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag（停止フラグ）を検知して安全に停止する仕組みを実装。
  - run_execution は paper_trading 環境で本番 DB と完全に分離された専用 SQLite（デフォルト: data/paper_trading.db）を使用するようにした。
- Paper 検証レポート:
  - P95 の計算と欠損データへの耐性を実装。データ不足・テーブル未存在時に OperationalError を捕捉して N/A を返すように堅牢化。
- ポートフォリオロジック:
  - calc_score_weights が全スコア 0 の場合に等金額配分へフォールバックし警告を出すよう修正。
  - apply_sector_cap は "unknown" セクターを制限対象から除外する仕様（不明セクターはブロックしない）。
  - position_sizing の集計上限調整で lot_size 単位での丸めや残余分の配分を実装し、利用可能現金を超えた場合にスケーリングする挙動を追加。

Security
- 環境変数 .env の取り扱いについて、config_setup.py のヘッダに ".env は絶対に Git にコミットしないこと" を明示。

Notes / その他
- Settings の各種プロパティで値検証を行い、不正な値は ValueError を送出する（例: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE）。
- 一部のコメントや TODO に将来的な拡張案（銘柄ごとの lot_size 管理やフォールバック価格の採用）が残されている。
- 実運用前に validate_config.py で設定を検証し、必要に応じて config_setup.py で .env を作成してから起動することを推奨。

Acknowledgements
- 本リリースは初期実装のため、今後 API 呼び出し周り（broker クライアントの実装・テスト）、monitoring の詳細実装、テストカバレッジ、エラーハンドリングの追加強化などが想定されます。