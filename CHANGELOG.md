# Keep a Changelog

すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

## [Unreleased]

（このブランチは現在のスナップショットでは未使用。リリース履歴は下記 0.1.0 を参照してください。）

## [0.1.0] - 2026-04-17

初回リリース。以下の機能群を実装・追加しました（ソースコードの内容から推測して作成）。

### 追加 (Added)
- 基本パッケージ情報
  - kabusys パッケージ初期化とバージョン設定（__version__ = "0.1.0"）。

- 実行エントリ／運用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知で安全に終了。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）で本番 DB と分離。
    - スレッドで ExecutionEngine を実行し、停止フラグ検知で安全に停止。
    - 起動時にプロセス優先度を "high" に設定。
    - 実行用 pid ファイル管理（data/execution.pid）。

- 設定管理
  - config.py
    - .env 自動ロード機構（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env と .env.local の読み込み優先順位（OS 環境変数保護機構あり）。
    - 複雑な .env パース実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ、インラインコメント処理）。
    - Settings クラスを提供し、各種設定プロパティを安全に取得：
      - J-Quants / kabuAPI / LINE の設定
      - duckdb / sqlite / paper_trading sqlite パス
      - PID / kill フラグパス・しきい値（CPU/MEM/DISK）
      - 環境判定プロパティ（is_live/is_paper/is_dev）
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）

- モニタリング DB 初期化支援
  - monitoring.monitoring_db の init_monitoring_db を実行してテーブル作成を保証（冪等）。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム抽象化されたプロセス優先度設定 set_process_priority(level) を追加（Windows / POSIX 対応）。
    - CPU affinity を固定する set_cpu_affinity(cpu_count) を追加。
    - psutil 標準での例外（アクセス権限不足等）を警告ログで扱う。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等重／スコア加重配分（スコア総和が 0 の場合は等配にフォールバックし warning）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存ポジション比率が max_sector_pct を超えるセクターの新規除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数（デフォルトフォールバック 1.0、未知レジームは警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・現金・保有等を考慮し株数を決定。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積り、残余配分ロジックを実装。

- 研究（Research）モジュール
  - research/factor_research.py
    - calc_momentum: MOM 1M/3M/6M、MA200 乖離率を DuckDB SQL ウィンドウ関数で算出（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比を算出（true_range の NULL 伝播に注意）。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。

  - research/feature_exploration.py
    - calc_forward_returns: 1/5/21 日等の将来リターンを LEAD を使って一括取得。horizons 入力検証あり。
    - calc_ic / rank / factor_summary: スピアマン（ランク相関）による IC 計算、ランク付け（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）。

  - research/__init__.py: 主要関数の再エクスポート（zscore_normalize を data.stats から導入）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - コマンドラインツールで paper_trading DB を解析し、稼働率・注文成功率・送信率・P95 レイテンシ等を集計してレポート出力。
    - 閾値（稼働率 99%、成立率 90% 等）に基づく PASS/FAIL 判定を実装。
    - DB 存在チェック、テーブル欠損時の安全ハンドリング（sqlite3.OperationalError を捕捉し適切なデフォルトを使用）。
    - P95 計算ユーティリティ、日付フィルタ構築を実装。

- AI / ニュース NLP（未完の実装を含む）
  - ai/news_nlp.py
    - raw_news を OpenAI（gpt-4o-mini）に送信して銘柄別センチメント（-1.0〜1.0）を算出し ai_scores へ書き込む設計を追加。
    - バッチ処理（最大 20 銘柄）、トークン肥大化対策（article/char 限度）、リトライ・指数バックオフ、レスポンスバリデーション、スコアクリップを盛り込んだ設計。
    - ニュース集計ウィンドウ（JST 基準、UTC 変換）を計算する calc_news_window を実装。
    - 実装断片の末尾で処理が切れている（このスナップショットでは _fetch_articles 等の続きが未収録）。

- DB/分析基盤
  - DuckDB と SQLite の両方を使用する設計（duckdb は分析用／prices_daily/raw_financials 等、sqlite は運用ログ・モニタリング用）。
  - 各所で DuckDB 接続を受け取る関数設計（副作用なしの純粋関数重視）。

### 変更 (Changed)
- 設計方針の明示
  - 多くのモジュールで「DB 参照なし — メモリ内計算のみ」「外部 API にアクセスしない」等、単体テストしやすい方針がコメントで明示化。

- run_monitoring/run_execution
  - 起動直後にプロセス優先度を上げるよう統一（運用上の優先度確保）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export プレフィックス対応、クォート内エスケープ対応、インラインコメントの扱い、無効行のスキップ等を実装して .env の読み込みエラーを低減。

- Paper 検証レポート
  - テーブルが存在しない場合でもツールがハンドリングしてクラッシュしないように sqlite3.OperationalError を捕捉。

### 注意 / 既知の問題 (Known Issues)
- ai/news_nlp.py はスナップショット末尾で途中までの実装（_fetch_articles 等の続きが欠落）。実稼働化のためには記事取得部分と DuckDB への書き込みロジックの続きが必要。
- position_sizing の価格欠損（open_prices に 0.0 または欠損がある場合）に関する TODO コメントあり。将来的に前日終値や原価でのフォールバックが必要。
- process_priority の優先度設定はプラットフォーム／権限に依存し、失敗した場合は警告を出してスキップする挙動。

### セキュリティ (Security)
- OpenAI API キーなどの機密情報は Settings/.env 経由で管理する設計。ただし、API キー取り扱いは実行環境での適切なシークレット管理（環境変数管理）を推奨。

---

注: 上記はソースコードの内容から推測して作成した CHANGELOG です。実際のコミット履歴やリリースノートと異なる場合があります。必要であれば実際の git コミットメッセージや開発履歴に基づいた差分版 CHANGELOG を生成します。