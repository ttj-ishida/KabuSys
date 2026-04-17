Keep a Changelog
=================

すべての変更は「Keep a Changelog」フォーマットに従って記録しています。  
このファイルでは、リリースごとの主な追加項目、変更点、修正点を日本語でまとめています。

0.1.0 - 2026-04-17
------------------

Added
- コア: パッケージ初回リリース。
  - パッケージメタ情報: kabusys.__version__ = 0.1.0 を追加。
- 起動スクリプト:
  - run_monitoring.py を追加 — SystemMonitor のポーリングループを起動するユーティリティ。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。  
    - 停止はプロジェクトの data/stop_requested.flag ファイルで制御。  
    - 監視は環境にかかわらず本番 sqlite_path を使用して初期化。
  - run_execution.py を追加 — ExecutionEngine を起動するスクリプト。  
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite を使用して本番 DB と分離（data/paper_trading.db がデフォルト）。  
    - 起動時にプロセス優先度を "high" に設定し、停止フラグで安全にシャットダウンする仕組みを実装。  
    - BrokerClientFactory を用いて環境に応じたブローカークライアントを生成。
- 設定管理:
  - config.Settings を追加 — 環境変数・.env ファイルを読み込む設定層。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動ロード（無効化可）。  
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント等に対応。  
    - 各種設定プロパティ（DB パス、PID ファイル、しきい値、PAPER_FILL_MODE, KABUSYS_ENV 検証など）を提供。
- ポートフォリオ構築:
  - portfolio モジュールを追加（純粋関数群）。主な関数:
    - select_candidates: スコア降順で候補選択（タイブレーク: signal_rank）。  
    - calc_equal_weights / calc_score_weights: 重み計算（score が全て 0 の場合は等分へフォールバック）。  
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄除外や "unknown" セクター挙動等の仕様）。  
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。  
    - calc_position_sizes: 発注株数算出（risk_based / equal / score の各方式、lot_size 単位丸め、aggregate cap によるスケーリングと端数処理）。
- リサーチ機能:
  - research パッケージを追加:
    - factor_research: calc_momentum / calc_volatility / calc_value — DuckDB の prices_daily/raw_financials を用いたファクター計算。  
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank — 将来リターン、IC、統計サマリー計算。  
    - research.__init__ で zscore_normalize（kabusys.data.stats）との統合エクスポート。
- ユーティリティ:
  - utils.process_priority: set_process_priority / set_cpu_affinity を追加 — Windows / POSIX の差を吸収してプロセス優先度・CPU affinity を設定（権限不足時は警告を出してスキップ）。
- ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。  
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL 判定を行う。  
    - デフォルト DB パスは data/paper_trading.db。日付範囲指定 (--from / --to) に対応。  
    - しきい値（稼働率 99%、注文成功率 90%、送信率 95%、P95レイテンシ 200ms）を定義。
- AI:
  - ai.news_nlp モジュールを追加 — ニュース記事の OpenAI によるセンチメント評価用ユーティリティを実装。  
    - タイムウィンドウ計算、バッチサイズ、モデル指定、スコアクリッピング、リトライ／バックオフ戦略などの定数・初期処理を実装。  
    - 実装方針としてバッチ化（最大 20 銘柄）、JSON Mode 期待、API エラーの再試行、部分的な DB 更新戦略（影響範囲を限定）を記載。
- DB/監視:
  - 監視用 DB 初期化ユーティリティ init_monitoring_db の利用箇所を run_monitoring/run_execution に追加し、監視テーブルの存在を保証（冪等）。

Changed
- .env 読み込みの動作仕様を明確化:
  - OS 環境変数を保護する protected セットを導入し、.env.local は既存の OS 環境変数を上書きしないよう制御。  
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- Execution 起動フロー:
  - paper_trading 環境用 DB を明示的に分離（settings.paper_sqlite_path を使用）。  
  - エンジン起動前に停止フラグを確認して即座に起動中止するガードを追加。

Fixed
- calc_score_weights: 全銘柄のスコア合計が 0.0 の場合、等金額配分へフォールバックして警告ログを出力（ゼロ除算回避）。
- run_monitoring._get_poll_interval: MONITOR_POLL_INTERVAL が不正な値のときに適切にログを出しデフォルトへフォールバック（0 以下の値もデフォルトへ）。
- utils.process_priority: 未対応 OS や権限不足時に例外を投げず警告でスキップするように例外ハンドリングを追加。
- tools.paper_verification_report:
  - DB が存在しない場合のエラーメッセージと早期リターンを追加してユーザーフレンドリーに。
  - 各種クエリで OperationalError 発生時にフェイルセーフでデフォルト値にフォールバックするように変更。

Notes / Implementation details
- 多くの計算ロジックは DuckDB の SQL ウィンドウ関数を活用しており、prices_daily / raw_financials 等のテーブルを前提としています。データ欠損時の保護（NULL ハンドリング、行数チェック）を随所に入れて安全に動作する設計です。
- Execution 側のデフォルトリスクパラメータ（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）はコード内で初期設定されています（実運用前に要見直し）。
- ai.news_nlp の score_news 関数は API キーの解決やタイムウィンドウ計算、記事集約周りの骨格を実装しています（詳細な API 呼び出しループは実装ファイルの後半で完結する想定）。本番運用前に API 呼び出し周りのエラーハンドリング／レート制御の挙動確認を推奨します。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは明示的に環境変数 OPENAI_API_KEY または関数引数で供給する必要があり、未設定時は ValueError を送出して誤動作を防止します。

今後の予定（短期）
- ai.news_nlp の API 呼び出し／レスポンス検証ロジックの実装完了・テスト。  
- 監視・実行コンポーネントの統合テスト、ドキュメント（運用手順、.env.example）の整備。  
- パフォーマンス改善（DuckDB クエリのチューニング、バッチ処理の最適化）。

お問い合わせ・貢献
- バグ報告・要望はリポジトリの Issue へお願いします。貢献は歓迎します（プルリク前に Issue で相談していただけるとスムーズです）。