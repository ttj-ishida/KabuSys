CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" として記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

Added
- news_nlp モジュールの実装を追加（OpenAI を用いたニュースセンチメントのバッチスコアリング）。
  - gpt-4o-mini を利用する想定、JSON Mode 出力を期待。
  - タイムウィンドウ計算、記事集約、バッチ送信、リトライ／バックオフ、結果検証、スコアのクリップ、
    部分更新（DELETE → INSERT）による堅牢な書き込み戦略などの設計が含まれる。
- research モジュールの拡充（factor_research, feature_exploration）。
  - モメンタム / ボラティリティ / バリューファクターの計算 (DuckDB ベース) を追加。
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、ランク関数を追加。
- portfolio 関連の純関数群を追加（portfolio_builder, position_sizing, risk_adjustment）。
  - 候補選定、等金額／スコア加重の重み計算。
  - リスクベース・等配分・スコア配分に基づく株数決定ロジック（単元株丸め、aggregate cap のスケーリング、cost_buffer 対応）。
  - セクター集中上限適用と市場レジームに応じた投下資金乗数計算。
- 実行・監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine 起動スクリプト。paper_trading 環境向けに MockBroker と専用 SQLite DB を使って本番 DB と分離。
    - BrokerFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
    - 停止フラグ（data/stop_requested.flag）と実行用 pid ファイル（data/execution.pid）をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する設計。
    - プロセス優先度を高く設定して起動。
- utils/process_priority.py を追加（プロセス優先度・CPU affinity のユーティリティ）。
  - Windows / POSIX の差異を吸収し、nice 値 / HIGH_PRIORITY_CLASS を設定。
  - set_cpu_affinity によりプロセスを先頭 N コアに固定可能。権限不足時は警告を出してスキップ。
- config.py を追加（.env ファイル自動読み込み・設定管理）。
  - プロジェクトルート検出（.git / pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の順、OS 環境変数は保護）。
  - export KEY=val 形式、シングル／ダブルクォートやバックスラッシュエスケープ、インラインコメント処理などを考慮した堅牢なパーサ実装。
  - 各種環境設定プロパティ（DB パス、paper_trading 用 DB パス、PID/kill フラグパス、閾値、PAPER_FILL_MODE 検証等）。
- tools/paper_verification_report.py を追加（Paper Trading 検証レポート生成 CLI）。
  - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシなどを算出し PASS/FAIL 判定。
  - --from/--to/--db オプションをサポート、閾値はソース内定義（稼働率 99% 等）。

Changed
- パッケージ初期バージョンを __version__ = "0.1.0" に設定。
- DuckDB を解析・集計処理に積極的に利用する設計に（research / ai / tools で DuckDB 接続を受け取る形へ統一）。
- run_execution/run_monitoring の起動フローでプロセス優先度設定（set_process_priority）を起動直後に行うように統一。

Fixed
- .env 読み込み失敗時に警告を出すよう改善（権限エラー等のハンドリングを追加）。
- position_sizing のスケーリングロジックで残差配分の安定性を確保（lot_size 単位での端数処理、再現性のため二次キーで code を使用）。

Deprecated
- (なし)

Removed
- (なし)

Security
- OpenAI API キーが未設定の場合は明示的に ValueError を送出するように変更（news_nlp）。

注記（Unreleased）
- news_nlp モジュールのソース末尾が未完であり、記事取得部分の関数呼び出し（_fetch_articles 等）が実装途中で切れている場所があります。未完成箇所は今後のリリースで完了予定です。

[0.1.0] - 2026-04-17
--------------------

Added
- 初回公開リリース。
  - 上記の主要機能群を含む初期実装をまとめてリリース:
    - 実行・監視スクリプト (run_execution, run_monitoring)
    - 環境設定自動読み込み（.env パーサ）と Settings クラス
    - portfolio（候補選定・重み付け・ポジションサイズ計算・リスク調整）
    - research（ファクター計算・将来リターン・IC・統計サマリー）
    - ai/news_nlp（OpenAI ベースのニューススコアリング設計）
    - tools/paper_verification_report（Paper Trading の検証レポート CLI）
    - utils/process_priority（優先度・CPU affinity ユーティリティ）
    - DuckDB / SQLite を組み合わせたデータ処理基盤
- パッケージメタ情報（kabusys.__init__.__version__ = "0.1.0"）を追加。

Fixed
- 初期動作に必要な DB 初期化呼び出し（init_monitoring_db）を run_execution/run_monitoring 起動時に追加。

Security
- 環境変数必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）に未設定時の明確なエラー通知を追加。

その他 / TODO
- news_nlp の記事取得・バッチ送信の未完了部分実装。
- position_sizing の lot_size を銘柄別に設定する拡張や価格フォールバック（欠損価格時の対応）は将来的に検討。
- CPU affinity / priority の挙動はプラットフォーム依存のため運用環境での動作確認推奨。

参考
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。