# CHANGELOG

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under Semantic Versioning.

## [0.1.0] - 2026-04-17

### Added
- 初回公開: KabuSys コードベースの主要機能を追加しました。
  - 実行エンジン
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading モードに対応し、paper_trading 用の SQLite DB を本番 DB と分離して使用。
      - BrokerClientFactory によるブローカークライアント生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてエンジンを構成。
      - ストップフラグ (data/stop_requested.flag) による安全停止、実行 PID の出力 (data/execution.pid)。
  - 監視プロセス
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグによるループ終了、例外ハンドリングで次ポーリングへ継続。
  - 設定管理
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml）。
      - export 形式・クォート・インラインコメントに対応した独自 .env パーサ実装。
      - 環境変数必須チェック用の _require()、Settings クラスとしてプロパティ経由で設定参照。
      - 設定項目: DB パス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/kill flag パス、閾値系（CPU/MEM/DISK）、Paper Trading 用挙動（PAPER_FILL_MODE）等。
      - 自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - ポートフォリオ構築
    - src/kabusys/portfolio/*
      - portfolio_builder: シグナル選別 (select_candidates)、等重み/スコア加重 (calc_equal_weights / calc_score_weights)。スコア合計が 0 の場合のフォールバック実装と警告出力。
      - risk_adjustment: セクターキャップ適用 (apply_sector_cap)、レジーム乗数計算 (calc_regime_multiplier)（未知レジームはフォールバックして 1.0 を返す）。
      - position_sizing: 各種配分方式（risk_based / equal / score）に基づく発注株数計算。単元株（lot_size）による丸め、ポジション上限や aggregate cap（利用可能現金に基づくスケールダウン）、cost_buffer による保守的見積り。
      - 上記はすべて純粋関数で、DB を参照しない（メモリ内計算）。
  - リサーチ / ファクター計算
    - src/kabusys/research/*
      - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 経由で prices_daily / raw_financials を参照）。200 日移動平均や ATR、各種リターン計算を SQL+Python で実装。
      - feature_exploration: 将来リターン calc_forward_returns（複数ホライズン対応）、IC（calc_ic）計算、ランク変換ユーティリティ rank、ファクター統計 summary（factor_summary）。外部ライブラリに依存せず純粋 Python 実装。
      - research パッケージのエクスポート定義を追加（zscore_normalize を含む）。
  - AI / ニュース NLP（下地）
    - src/kabusys/ai/news_nlp.py
      - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価し ai_scores へ書き込む設計を実装。
      - バッチ処理、トークン肥大化対策（記事数・文字数上限）、API リトライ（429/ネットワーク/5xx へ指数バックオフ）、レスポンスバリデーション、スコアクリッピング（±1.0）などの耐障害方針を記載。
      - 注: ファイル末尾が途中で切れている箇所があり（実装途中の状態を含む）。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - cross-platform（Windows / POSIX）でプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を提供。権限不足や未対応環境では警告を出してスキップ。
  - CLI / ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成ツール。期間指定（--from / --to / --db）で稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計して標準出力へ出力。
      - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定を行う。

### Changed
- プロジェクト構成
  - DuckDB を分析用途のストレージ（prices_daily / raw_financials など）として使用する前提を反映。
  - パッケージの __init__ に基本的なエクスポートとバージョン (0.1.0) を追加。

### Fixed
- .env パーサの堅牢性
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いを改善。
  - .env ファイル読み込みに失敗した場合は警告を出して継続（テストや権限不足対策）。
- 設定値バリデーション
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の不正値で早期に ValueError を発生させることで誤設定を検出しやすく。

### Deprecated
- なし（初回リリース）

### Removed
- なし

### Security
- OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数から取得。未設定時は明示的なエラーを投げる設計（news_nlp）。

### Notes / Known issues
- src/kabusys/ai/news_nlp.py はファイル末尾が途中で切れており（記事集約フェーズで mid-line で終了）、完全実装ではない箇所があります。OpenAI との実際の I/O 部分（API 呼び出し / DB 書き込み周り）は実装の続きを要します。
- position_sizing 内の価格欠損時（price が 0.0）のフォールバックロジックに関する TODO コメントあり（将来的に前日終値や取得原価をフォールバックする案）。
- set_cpu_affinity は権限や OS に依存するため、環境によっては無視される（警告ログのみ）。

---

このリリースはプロジェクトの最初のまとまった公開版を表します。将来の変更はこのファイルに従ってバージョンごとに追記していきます。