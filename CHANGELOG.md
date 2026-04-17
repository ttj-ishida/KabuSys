# Changelog

すべての重要な変更履歴を Keep a Changelog の形式で記載します。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-17

初回リリース。システム監視・実行エンジン・ポートフォリオ構築・リサーチ・ニュースNLP 等の主要機能を実装。

### 追加
- 基本情報
  - パッケージバージョンを 0.1.0 に設定（kabusys.__version__）。
  - DuckDB / SQLite を併用するデータ基盤を想定した設計を導入（Settings にパス設定）。

- 環境設定/ロード（src/kabusys/config.py）
  - .env 自動ロード機能を実装：プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を読み込む。
  - .env パーサーを強化：export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスで各種環境変数をラップ：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 必須取得（未設定時は例外）。
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH などのデフォルトパス。
    - PAPER_FILL_MODE の妥当性チェック（有効値: instant, partial, never, reject）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証。
    - 監視閾値（CPU/MEMORY/DISK）や PID / KILL フラグ関連設定。

- 実行エントリポイント
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine の起動フローを実装。BrokerClientFactory を使って実際の / モックのブローカークライアントを選択。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離。
    - エンジンは別スレッドで実行、停止フラグ（data/stop_requested.flag）検知で停止。
    - 初期化時に監視テーブル存在を保証（init_monitoring_db）。
    - リスク管理初期設定（RiskConfig）をデモ用値で設定し、broker.get_available_cash() を初期ポートフォリオ値として使用。
    - 実行用 PID ファイルパス管理（data/execution.pid）。

  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL（秒）で間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルト使用。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを抜ける。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を使用）。

- プロセス制御ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) を実装：Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度（high/normal/low）設定を試みる。
  - set_cpu_affinity(cpu_count) を実装：プロセスを先頭 N コアにピン留めする機能（アクセス権限等で失敗した場合は警告でスキップ）。
  - PSUtil 経由の例外（AccessDenied 等）を丁寧にハンドルしてフォールバック。

- ポートフォリオ構築モジュール（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates(): BUY シグナルを score 降順、signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights(), calc_score_weights(): 等配分・スコア加重配分。スコア合計が 0 の場合は等配分にフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap(): セクター集中制限を実装。既存保有のセクター別エクスポージャーを算出し、上限超過セクターの新規候補を除外（unknown セクターは除外しない）。sell_codes により当日売却銘柄を除外可能。
    - calc_regime_multiplier(): 市場レジームに応じた投下資金乗数を返す（bull:1.0 / neutral:0.7 / bear:0.3）。未知レジームは 1.0 にフォールバック（警告）。
  - position_sizing:
    - calc_position_sizes(): allocation_method に応じた株数決定（risk_based / equal / score）。
      - risk_based: 許容リスク率、stop_loss を用いたリスクベース計算。
      - equal/score: ウェイトに基づく配分、max_position_pct/per-stock 上限、lot_size（単元）で丸め。
      - aggregate cap: 合計コストが available_cash を超える場合にスケールダウンし、端数調整で lot_size 単位を再配分するロジックを実装。
      - cost_buffer（手数料・スリッページ見積り）を考慮。
    - 設計上の注記（TODO）: price 欠損時のフォールバックや将来的な lot_size 銘柄別対応の余地を明記。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum(): mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB の prices_daily から計算（ウィンドウ・行数チェックあり）。
    - calc_volatility(): ATR/atr_pct / avg_turnover / volume_ratio を計算（true_range の NULL 伝播制御を考慮）。
    - calc_value(): raw_financials と prices_daily を結合して PER / ROE を算出（最新報告日の取得に ROW_NUMBER を利用）。
  - feature_exploration:
    - calc_forward_returns(): 指定ホライズン（デフォルト [1,5,21]）で将来リターンをまとめて取得。horizons の入力検証を実装。
    - calc_ic(): ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なレコードがない場合は None を返す。
    - rank(), factor_summary(): ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージの __all__ を整備して外部利用を容易に。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込むための設計を実装。
  - 主要機能・設計方針:
    - ニュース収集ウィンドウ計算（JST 基準、UTC に変換）を calc_news_window() で提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・記事/文字数トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - API 失敗（429 / ネットワーク / タイムアウト / 5xx）に対する指数バックオフリトライ。
    - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための差分書き込み（DELETE→INSERT）方式。
    - API キー未設定時は ValueError を送出。
    - 注意: 実装は JSON Mode を期待し、出力フォーマットは厳密な JSON を要請するシステムプロンプトを含む。
  - （注）ファイル末尾は一部コード切れの状態（提供コードの末尾で途中切断）だが、主要設計と安全処理方針は含まれている。

- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading 検証レポート生成ツールを追加。
    - コマンドライン実行に対応（--from / --to / --db オプション）。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ、リスク却下数等。
    - Pass/Fail 判定基準を定義（稼働率 >=99% 等）および結果フォーマットを標準出力へ印字。
    - DB が存在しない / テーブル欠如時の耐性（OperationalError を捕捉して N/A を返す）を備える。

- パッケージ初期化等
  - kabusys package の __all__ を整理（主要サブパッケージ名を列挙）。
  - tools パッケージを追加（__init__.py）。

### 変更
- なし（初回リリースのため既存からの変更はありません）

### 修正
- なし（初回リリース）

### 削除
- なし

### 既知の制限・注意点
- news_nlp モジュールのファイル末尾は提供コード内で途中切断されており、fetch 以降の実装が未確認。実運用時は該当箇所の完全実装とテストが必要。
- position_sizing 内の price 欠損時のフォールバックロジックは TODO コメントとして残存（将来的に前日終値等へのフォールバックを検討）。
- process_priority / set_cpu_affinity は権限やプラットフォームの違いで失敗する可能性があり、その場合は警告でスキップする設計。
- .env 自動ロードはプロジェクトルート探索に依存するため、パッケージ配布後や特定環境でプロジェクトルートが見つからない場合は自動ロードがスキップされます（必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使用）。

---

今後の予定（例）
- news_nlp の残り実装と E2E テストの追加
- BrokerClient の具象実装の補完および execution の細かい挙動テスト
- 銘柄別 lot_size 対応、price フォールバック実装
- DuckDB クエリのパフォーマンスチューニングとカバレッジ拡充

（必要があれば、この CHANGELOG を基にセクションの追記・修正を行います。）