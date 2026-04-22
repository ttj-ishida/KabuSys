CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained in Japanese.
See: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

(なし)

0.1.0 - 2026-04-22
------------------

Added
- 初回リリース。本リリースで実装された主要機能とモジュールを追加。
  - コアパッケージ
    - kabusys パッケージ本体を追加。バージョンは __version__ = "0.1.0"。
  - 設定管理
    - 環境変数/`.env` 管理モジュール (kabusys.config) を実装。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）。
      - .env / .env.local の自動読み込み（OS 環境変数を保護、読み込み無効化フラグあり）。
      - 複雑な .env パース対応（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等）。
      - Settings クラスで各種設定プロパティを提供（DB パス、API トークン、監視閾値、環境種別など）。
      - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）。
  - 設定ユーティリティ CLI
    - 環境設定ウィザード (kabusys.config_setup)
      - 対話式で .env を初期作成・更新。
      - シークレット入力マスク、選択肢、デフォルト値をサポート。
    - 設定検証ツール (kabusys.validate_config)
      - 起動前チェック: 必須環境変数、KABUSYS_ENV・LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース判定（PyYAML が無ければスキップして警告）。
      - --strict モードで警告をエラー扱いにできる。
  - 実行系・監視系スクリプト
    - ExecutionEngine 起動スクリプト (kabusys.run_execution)
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
      - Broker クライアントのファクトリ切替と依存コンポーネントの組み立て（OrderRepository, OrderManager, RiskManager, Reconciler 等）。
      - スレッドを使った ExecutionEngine の実行と停止フラグ監視（data/stop_requested.flag）。
      - 起動時にプロセス優先度を High に設定。
    - SystemMonitor 起動スクリプト (kabusys.run_monitoring)
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
      - 監視は環境にかかわらず本番 sqlite_path を使用する旨の仕様。
      - 停止フラグ検知でループ終了、例外発生時はロギングして次サイクルへフォールバック。
  - ポートフォリオ構築ライブラリ (kabusys.portfolio)
    - portfolio_builder
      - select_candidates: スコア降順・タイブレークロジックを実装。
      - calc_equal_weights, calc_score_weights: 等金額・スコア加重（スコア全て 0 の場合は等分にフォールバック）。
    - risk_adjustment
      - apply_sector_cap: セクターごとの既存エクスポージャー計算と新規候補除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をサポート、未知値は警告して 1.0 フォールバック）。
    - position_sizing
      - calc_position_sizes: risk_based / equal / score の配分方式、単元株（lot_size）での丸め、per-position と aggregate のキャップ、cost_buffer を考慮した保守的見積もりとスケーリングロジック。
  - 解析・レポート
    - Paper Trading 検証レポートツール (kabusys.tools.paper_verification_report)
      - SQLite（paper_trading.db）から各種指標（稼働率、注文成立率、送信率、P95 レイテンシ等）を集計して判定（PASS/FAIL）。
      - P95 計算、日付フィルタ (--from / --to)、DB パスの CLI オーバーライドをサポート。
  - ユーティリティ
    - logging_setup: 統一ロギング初期化（stdout StreamHandler + 日次ローテートファイルハンドラ、ログディレクトリ作成ロジック、ログレベル解決順）。
    - process_priority: Windows/Linux/macOS の差分を吸収したプロセス優先度設定と CPU affinity 設定（psutil を利用、失敗時は警告ログでフォールバック）。

Changed
- 仕様設計（明文化）
  - 実行・監視プロセスは起動直後に優先度を上げる（set_process_priority("high") の呼び出しを明示）。
  - 監視ループは外部フラグファイル (data/stop_requested.flag) で停止できる設計を採用。
  - .env の自動読み込み順序: OS 環境 > .env.local > .env（OS 環境を保護するため protected set を導入）。
  - logging_setup のログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する動作を明示。

Fixed / Robustness improvements
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いの改善により複雑な .env 値に対応。
- 設定の妥当性チェック
  - PAPER_FILL_MODE の未サポート値に対して ValueError を投げるようにして早期検出可能にした。
- DB 初期化の冪等性
  - init_monitoring_db 呼び出しを実行側で行い、監視テーブルが存在することを保証（複数回呼んでも安全）。
- Execution / Monitoring の安全停止
  - stop フラグ検知時に適切にログを出し、安全にシャットダウンするように改善。
- 例外ハンドリングの強化
  - monitor.check_once() や DB 操作での例外をキャッチしてループ継続する設計により、障害耐性を向上。
- ロギング設定の二重ハンドラ防止
  - setup_logging は既存ハンドラを一旦 flush/close してから再設定することで二重出力を防止。
- process_priority / cpu_affinity のフォールバック
  - 対応 OS でない場合や権限不足のケースで安全にスキップするよう警告ログでフォールバック。

Known issues / TODO
- research.factor_research モジュールは部分実装（ファイル末尾で途中）であり、モメンタム計算の SQL 実装が未完了。
- position_sizing の価格欠損（price==0.0）時はエクスポージャーが過少評価される懸念あり。将来的に前日終値や取得原価でのフォールバックを検討中（TODO コメントあり）。
- 単元株サイズの拡張: 現状は全銘柄共通の lot_size を想定。将来的には銘柄ごとの lot_map を導入予定。

Security, Privacy, and Operational notes
- .env は絶対にリポジトリにコミットしないよう注意喚起（config_setup がヘッダで警告）。
- 本番環境 (KABUSYS_ENV=live) の場合は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認するよう警告を出すチェックを実装（validate_config、Settings のプロパティでの検証）。
- 監視は本番 sqlite_path を参照する仕様のため、環境分離が必要な場合は設定で明示的に分けること（paper_trading 用 DB は run_execution 側で分離して使用）。

Migration / Upgrade notes
- 既存の運用で .env を使っている場合、本リリースの .env パーサは従来より厳密にパースするため、エスケープやクォートの扱いで差異が出る可能性があります。問題が発生したら .env の該当行を見直してください。
- Paper Trading 用 DB を利用する場合は KABUSYS_ENV を paper_trading に設定することで run_execution が data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH で指定したパス）を使用します。

Contact
-------
不明点やバグ報告は issue を作成してください。