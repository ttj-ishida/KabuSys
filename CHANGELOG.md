Keep a Changelog
================

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- （現在なし）

[0.1.0] - 2026-04-17
--------------------

Added
- 実行エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて実運用/ペーパートレードを切り替え、専用の SQLite を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。
- 設定管理
  - config.Settings クラスを追加し、環境変数経由の設定取得を統一（DB パス、API キー、閾値などを含む）。
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等を考慮して読み込み。
- データレイヤ / DB 統合
  - DuckDB を分析用に導入（duckdb_path 設定）。
  - 監視用・ペーパートレード用の SQLite パス分離（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を利用して起動時に必要テーブルの存在を保証。
- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio.portfolio_builder: シグナル選択（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）。
  - portfolio.risk_adjustment: セクターキャップ適用（apply_sector_cap）、マーケットレジームに基づく乗数計算（calc_regime_multiplier）。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）をサポートする株数決定ロジック（単元丸め、aggregate cap、コストバッファ等の考慮）。
  - これらは純粋関数群で DB を参照せずメモリ内計算のみ。
- Research（ファクター計算・探索）
  - research.factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算を DuckDB SQL で実装（calc_momentum, calc_volatility, calc_value）。
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）計算、統計サマリーなどのユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）。
  - DuckDB 接続を受け取る設計で、外部 API に依存しない。
- AI / ニュース NLP
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとにセンチメントを ai_scores に書き込む処理を実装（バッチング、トークン肥大対策、スコアクリップ、リトライ戦略、レスポンス検証等）。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを集計し PASS/FAIL を判定。
- ユーティリティ
  - utils.process_priority: プロセス優先度と CPU affinity 設定ユーティリティを追加（Windows / POSIX の差分吸収、例外時は警告でスキップ）。
- 運用
  - 停止フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを導入し、安全に停止・監視できる仕組みを提供。

Changed
- ペーパートレード設計
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用する前提とし、ペーパートレード用 DB を完全に分離。
- ログ／閾値の設定
  - Settings にて LOG_LEVEL、CPU/MEM/DISK 閾値や kill/clear フラグ設定を提供。
- モニタリング
  - run_monitoring は常に本番 sqlite_path を使用（環境に依存しない監視 DB 利用）。
  - _get_poll_interval にて不正値（0 以下や非整数）に対してデフォルトへフォールバックし、警告ログを出すように変更。
- エラー耐性
  - 監視ループ内で monitor.check_once() が例外を出してもループを継続するように例外キャッチとログを追加。
  - run_execution は起動前に停止フラグが立っている場合は起動をスキップする安全装置を追加。
  - OpenAI API 呼び出しに対するリトライ戦略や失敗時のフェイルセーフを設計段階で導入（ニュース NLP）。

Fixed
- .env 読み込みの堅牢化
  - クォートやバックスラッシュエスケープ、インラインコメントの扱いを改善し、誤ったパースを修正。
  - OS 環境変数を保護するため override / protected の挙動を明確化。
- レポート生成の堅牢化
  - tools.paper_verification_report: テーブルが存在しない場面（OperationalError）に対してデフォルト値で扱い、処理が途中でクラッシュしないように保護。
- 設定バリデーション
  - PAPER_FILL_MODE の値チェックを追加し、不正な値は例外を投げるようにした（有効値: instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の不正値チェックを追加。
- プロセス優先度設定
  - set_process_priority / set_cpu_affinity は権限不足や未サポート環境で発生する例外を捕捉して警告ログを出し、安全にスキップするように修正。

Notes / Internals
- 多くの計算モジュール（portfolio, research）は純粋関数として設計され、副作用を持たないためテストしやすい。
- DuckDB を用いた集計・ファクター計算は SQL と Python を組み合わせた実装で、prices_daily / raw_financials 等のテーブルを参照する。
- AI ニュース NLP はレスポンスの検証、スコアのクリッピング、部分更新（対象コードのみ DELETE/INSERT）など、途中障害時に既存データを保護する設計になっている。
- 将来の改善点（TODO メモ）
  - position_sizing: 銘柄別の lot_size を stocks マスタから取得する拡張。
  - apply_sector_cap: price 欠損時の価格フォールバック（前日終値等）導入検討。

Authors
- KabuSys 開発チーム（ソースコード内コメント・ドキュメントに基づくまとめ）

<!--
参考: 上記 CHANGELOG は提供されたソースコードから推測して作成しています。実際のコミット履歴ではなく、コードの機能・コメントに基づく要約です。
-->