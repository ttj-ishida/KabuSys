CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースから推測できる変更点・リリース内容を日本語で記載しています。

0.1.0 - 2026-04-17
-----------------

Added
- パッケージ初版リリース。以下の主要機能・モジュールを追加。
  - 実行エンジン起動スクリプト
    - src/kabusys/run_execution.py
    - ExecutionEngine の起動フロー、スレッド実行、停止フラグ（data/stop_requested.flag）検知、専用 PID ファイル管理を実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と完全分離する挙動をサポート（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory による実運用 / モックブローカーの切替を想定。
    - RiskManager / OrderManager / Reconciler 等の依存コンポーネント組み立て処理を含む。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。

  - 監視ポーリング起動スクリプト
    - src/kabusys/run_monitoring.py
    - SystemMonitor の初期化とポーリングループ、停止フラグ検知、MONITOR_POLL_INTERVAL 環境変数による間隔上書き（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

  - 設定 / 環境変数管理
    - src/kabusys/config.py
    - .env/.env.local を自動ロード（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
    - .env パーサが export 形式、クォート付き値、インラインコメント等に堅牢に対応。
    - Settings クラスでアプリケーション設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, 等）。
    - KABUSYS_ENV の検証（development / paper_trading / live）、LOG_LEVEL の検証。

  - ポートフォリオ構築ユーティリティ
    - src/kabusys/portfolio/*
    - 候補選定・重み計算 (select_candidates, calc_equal_weights, calc_score_weights)。
    - セクター集中制限・レジーム乗数 (apply_sector_cap, calc_regime_multiplier)。
    - 銘柄ごとの発注株数決定（calc_position_sizes）:
      - risk_based / equal / score の配分方式をサポート。
      - lot_size（単元）丸め、max_position_pct、max_utilization、cost_buffer による aggregate cap スケーリング処理。
      - 空価格や価格欠損時のログ出力・スキップ処理、スケールダウン時の端数処理（残差による追加配分）を実装。

  - 研究用ファクター計算・特徴量探索モジュール
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value：DuckDB の prices_daily / raw_financials を利用してファクターを SQL + Python で計算。
      - 長期移動平均、ATR、各種モメンタム（1M/3M/6M）等。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - 研究モジュールは外部 API を呼ばず、DuckDB 経由で自己完結的に集計可能。

  - AI ニュース NLP スコアリング
    - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) に対してバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を設計。
    - バッチサイズ、最大記事数・文字数トリム、429/タイムアウト/5xx 等に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップなどの安全策を導入。
    - 処理は API キー（api_key 引数または OPENAI_API_KEY 環境変数）を必要とする。

  - Paper Trading 検証ツール
    - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から期間指定で指標（稼働率・注文成功率・送信率・P95 レイテンシ等）を集計してレポート出力。
    - CLI インターフェース（--from, --to, --db）を提供。
    - 判定基準（閾値）を設定して PASS / FAIL の判定を行う。

  - プロセス優先度 / CPU affinity ユーティリティ
    - src/kabusys/utils/process_priority.py
    - Windows / POSIX(Linux, macOS, FreeBSD) を透過してプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加（psutil 依存）。
    - アクセス権限不足や未対応環境では警告を出して安全にスキップ。

  - パッケージ初期化情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- 環境変数の自動ロード時、既存の OS 環境変数を保護するため protected セットを使用（.env / .env.local の上書き制御）。
- OpenAI API キー未設定時に score_news が ValueError を送出して明示的に失敗させる設計（意図しないキー漏れを防止）。

Notes / Known limitations（コードから推測）
- research モジュールは DuckDB のテーブル構造（prices_daily, raw_financials 等）に依存するため、テーブルスキーマとデータの準備が必要。
- position_sizing の単元（lot_size）は現状グローバル固定（将来的に銘柄別拡張を想定した TODO が記載）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いにして上限適用を行わない（既知データの欠損に注意）。
- news_nlp（OpenAI 絡み）は外部 API 依存/料金発生のため運用時の注意が必要（API キー管理、レート制限、コスト）。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対しフォールバックロジックを持つ（0 以下や非整数はデフォルト 60 秒へ）。

開発者向けメモ
- 自動 env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストや CI で便利）。
- パッケージの設定は Settings クラス経由で取得可能。必須値は _require() により未設定時に明示的なエラーを投げます。
- DuckDB 接続は各モジュールで外部から渡す設計（テスト容易性を重視）。
- ログレベル等は環境変数 LOG_LEVEL で制御可能。

今後の改善候補（コード内 TODO や設計メモから推測）
- position_sizing: 銘柄別 lot_size を stocks マスタに持たせる拡張。
- apply_sector_cap: 価格欠損時のフォールバック（前日終値や取得原価）を導入してエクスポージャー過少見積りを防ぐ。
- news_nlp: API 呼び出しの部分でのより詳細な部分失敗対処（部分的リトライや永続化戦略）。
- duckdb / sqlite の初期化・マイグレーション管理をより明確にする移行手段。

Contact
- 変更点や設計意図に不明点がある場合は、リポジトリの該当ファイル（上記一覧）を参照してください。