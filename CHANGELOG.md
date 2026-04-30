# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

全般: この CHANGELOG は、ソースツリー内のスクリプトや設定処理の追加・改善内容を、コードから推測してまとめたものです。

## [0.1.0] - 2026-04-30

### 追加 (Added)
- 基本モジュール
  - kabusys パッケージの初期公開 (バージョン `0.1.0`)。__version__ を `0.1.0` に設定。
- 環境設定 / 設定読み込み
  - Settings クラスを実装し、環境変数に対するプロパティアクセスを提供（J-Quants、kabu API、LINE、DBパス、閾値など）。
  - 自動 .env 読み込み機能を追加（プロジェクトルートの検出: `.git` または `pyproject.toml` を基準）。`.env` と `.env.local` の読み込み順序と上書きルールを実装。
  - .env ファイルのパース機能を強化（`export KEY=val` 形式対応、クォート文字列のバックスラッシュエスケープ処理、コメント処理）。
- CLI / 実行スクリプト
  - 実行系:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。紙トレード (paper_trading) 向けに専用 DB を利用可能。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。PID ファイル/停止フラグ対応。
  - レポート／ユーティリティ:
    - run_pre_market_report.py: Pre-Market Report を生成する CLI を追加。
    - run_market_close_report.py: Market Close Summary CLI を追加（JSON出力・保存オプションあり）。
    - run_performance_report.py: 運用成績サマリーレポート（daily/weekly/monthly）CLI を追加。DuckDB から集計を取得。
    - run_position_reconciliation_report.py: Position Reconciliation レポート CLI を追加（watch モードあり）。
    - run_signal_queue_report.py: Signal Queue 確認ビュー CLI を追加（JSON/保存オプションあり）。
    - run_intraday_monitor.py: ザラ場中監視用 CLI を追加（単発 / watch モード、表示フォーマット実装）。
    - validate_config.py: 起動前設定検証ツールを追加（必須環境変数・YAML の存在とパース検証・本番向けガード等）。`--strict` オプションをサポート。
    - config_setup.py: 対話式で .env を作成・更新するウィザードを追加（シークレット項目はマスク表示、保存テンプレート出力）。
    - tools/paper_verification_report.py: Paper Trading 向けの検証レポート生成スクリプトを追加（稼働率・注文成功率・レイテンシ P95 等）。
- モニタリング・DB
  - 監視用 DB 初期化処理（init_monitoring_db）を利用して監視テーブルの存在を保証する仕組みを導入。
  - DuckDB を分析用途に使用するための接続処理を各 CLI に導入（read-only オプションを適宜使用）。
- リスク管理 / Execution 起動時処理
  - risk_config.yaml を読み込む loader を追加。設定値の型変換と妥当性チェック（0 < 値 <= 1、各閾値は >=1 など）を実装し、詳細なエラーメッセージを返す。
  - 起動時に Broker クライアントから現金・ポジション評価を取得して総資産を算出し、RiskManager に初期資産を渡す仕組みを実装。
  - 起動時のリコンシリエーション実行と Execution Startup Summary の生成／保存を実装（例外時は警告を出して起動継続）。
- 実行管理
  - プロセス優先度を起動直後に高優先度 ("high") に設定するユーティリティ呼び出しを追加（set_process_priority の利用）。
  - ExecutionEngine をスレッドでデーモン起動し、停止フラグ検知時に安全に停止処理を行う仕組みを実装。
  - PID ファイルの作成・削除・存在チェック、停止フラグ (stop_requested.flag / kill.flag) の検出を各所で実装。
- レポート入出力
  - 各種レポートで CLI 表示 / JSON 出力 / 保存（artifacts 配下）をサポート。JSON モードでは出力を汚染しないため保存先メッセージを stderr に出力するオプションを導入。
- 監視用の小部品
  - run_intraday_monitor のスナップショット構造（IntradaySnapshot）収集と CLI フォーマットを実装。ステータス判定ロジックを追加（OK/WARNING/CRITICAL）。

### 変更 (Changed)
- .env 読み込みの振る舞いを明確化
  - OS 環境変数は保護され、`.env.local` は `.env` の上書きとして読み込まれるように変更。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加してテスト時などの挙動制御を可能に。
- Settings の振る舞い
  - KABUSYS_ENV と LOG_LEVEL の値検証を追加（無効な値は例外）。
  - paper_trading 環境用に paper_sqlite_path、paper_fill_mode 等の設定を分離して扱うように変更。
  - 監視系設定（CPU/MEMORY/DISK の閾値や PID ファイルパス、kill flag 周り）を Settings に統合。
- 実行起動 / 監視ループ
  - run_monitoring: MONITOR_POLL_INTERVAL 環境変数を導入し、ポーリング間隔を上書き可能に。0 以下や不正な値はデフォルト (60 秒) にフォールバックする安全策を追加。
  - 監視ループ・Execution 起動時に DB 接続（SQLite / DuckDB）を必ず閉じるよう finally ブロックで明示的にクローズ処理を追加。
- リスク設定ロード
  - risk_config.yaml の読み込み時に発生する各種エラー（ファイル未存在、パース失敗、必須キー欠如、値の範囲外）に対してわかりやすい例外メッセージを追加。
- エラーハンドリング / ロギング
  - 報告生成や Broker クローズの際の例外をキャッチして警告ログを出すようにして、可能な限り起動や処理を続行する設計に変更。
  - CLI 実行時に logging.basicConfig を用いてデフォルトのログレベル/フォーマットを設定するよう統一。

### 修正 (Fixed)
- .env パーサーでのクォートされた値の扱いを改善し、バックスラッシュエスケープやインラインコメントの扱いを正しく処理するように修正。
- MONITOR_POLL_INTERVAL の不正値（非整数・0・負数）を検出してロギングとともに既定値にフォールバックするように修正。
- SQLite / DuckDB の読み取り専用 URI を使用する箇所での接続方法を調整し、読み取り専用モードでの安全なアクセスを実現。
- ExecutionEngine 起動前に停止フラグが既に立っている場合、起動を抑制するガードを追加。

### ドキュメント / ユーティリティ (Documentation / Tools)
- config_setup.py による対話式 .env 作成ウィザードを導入。生成される .env テンプレートに注記を付与し、秘密情報は表示時にマスクする実装を追加。
- validate_config により .env と config/*.yaml の基本的な整合性チェックと本番ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）を提供。
- 各 CLI のヘルプ・使い方のコメントを整備（例: run_signal_queue_report、run_intraday_monitor、run_position_reconciliation_report 等）。

---

注: 上記はソースコードから推測して記載した変更履歴です。手元のリポジトリに含まれる他のモジュール（monitoring.system_monitor、execution.*、operations.*、utils.* 等）の詳細実装によっては更に細かな変更点やバグ修正が存在する可能性があります。必要であれば各モジュール単位でさらに詳細な CHANGES を生成できます。