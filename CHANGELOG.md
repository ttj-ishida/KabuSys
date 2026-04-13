# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースから推測できる機能追加・設計方針・既知の制約・今後の改善候補をまとめたものです。

なお、リリース日はコードの取得時点の日付（2026-04-13）を採用しています。

## [Unreleased]

### 追加予定 / 改善案
- セクターエクスポージャ算出時の価格欠損（price が 0.0）のフォールバックロジック（前日終値や取得原価を用いる）を実装する（risk_adjustment.apply_sector_cap の TODO）。
- 銘柄ごとの単元（lot_size）マスタ導入により position_sizing.calc_position_sizes の lot_size パラメータを銘柄別対応へ拡張する。
- ai/news_nlp の API 呼び出し成功時に部分失敗があった場合のより詳細なロギング／リトライ可視化。
- 単体テスト・統合テストの追加（特に API キー未設定時・DuckDB/SQLite がない環境での挙動確認）。
- duckdb executemany の制約を踏まえたバルク書き込みの堅牢化（コメントにある注意点の実装強化）。

---

## [0.1.0] - 2026-04-13

初期公開リリース。以下の主要機能・モジュールを含みます。

### 追加
- 全体
  - パッケージ初版を公開（kabusys v0.1.0）。
  - パッケージメタ情報に __version__ = "0.1.0" を導入。

- 設定 / 環境変数管理 (kabusys.config)
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env / .env.local の読み込み順序制御（OS 環境変数の保護、override 挙動）。
  - .env パースロジック（export 付き・クォート・コメント処理対応）を実装。
  - 環境変数の検証ロジック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）と Settings クラスを提供。
  - デフォルト DB パス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)、PID / KILL フラグパス等の設定プロパティを提供。

- 実行エントリ / 実行環境制御
  - ExecutionEngine 起動スクリプト (run_execution.py)
    - プロセス優先度を起動直後に設定（utils.process_priority.set_process_priority）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み合わせ ExecutionEngine.run_session を呼び出す起動フローを実装。
    - RiskManager の初期設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker 設定 等）をデフォルトで適用。

  - SystemMonitor 起動スクリプト (run_monitoring.py)
    - プロセス優先度を High に設定。
    - MONITOR_POLL_INTERVAL 環境変数で監視ループのポーリング間隔を上書き可能（デフォルト 60 秒、1 未満の値はデフォルトにフォールバック）。
    - 監視処理は環境に関係なく本番 sqlite_path を使用し監視テーブルを初期化（init_monitoring_db）。

- 監視関連
  - monitoring モジュールと DB 初期化ユーティリティにより system_status などの監視テーブルを整備（init_monitoring_db を使用）。

- ユーティリティ (kabusys.utils.process_priority)
  - クロスプラットフォームでのプロセス優先度設定（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）を実装。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限がない場合は警告を出してスキップ）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder: シグナル選定（select_candidates）および等重配分 / スコア加重配分（calc_equal_weights, calc_score_weights）を実装。スコア全0時のフォールバック挙動あり。
  - risk_adjustment: セクター上限除外ロジック（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知レジームはフォールバック（1.0）。
  - position_sizing: 複数配分方式（risk_based, equal, score）に対応した株数算出ロジックを実装。aggregate cap、cost_buffer を考慮したスケーリングと lot_size 単位での丸め処理を実装。

- 研究用 / ファクター計算 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（DuckDB prices_daily を参照、データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比などを計算（true_range の NULL 伝播を適切に処理）。
    - calc_value: raw_financials から最新の財務データを取得し PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を計算。horizons の検証あり。
    - calc_ic: Spearman ランク相関による IC 計算を実装（レコードが少ない場合 None を返す）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティを提供。
  - DuckDB を用いた SQL+Python ハイブリッドでパフォーマンス寄与を考慮した実装。

- ツール (kabusys.tools.paper_verification_report)
  - Paper Trading 検証レポート生成 CLI を実装。
    - 検証指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシなど。
    - デフォルト閾値を実装（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - 日付フィルタ (--from / --to)、DB 指定 (--db) 対応。
    - P95 算出関数、NULL/データ不足時の N/A 表示・Fail 判定ロジックあり。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルに書き込む機能を実装。
  - バッチ処理（最大 20 銘柄/チャンク）、記事文字数・記事数制限（1 銘柄あたり最大記事数・最大文字数）によりトークン肥大化対策を実装。
  - レスポンスのバリデーション、スコアの ±1.0 クリップ、429/ネットワーク/5xx の指数バックオフリトライを導入。
  - OPENAI_API_KEY 必須（引数 or 環境変数）。失敗時はフェイルセーフでスキップして継続する設計。

### 変更
- なし（初期リリースのため該当なし）。

### 修正
- なし（初期リリースのため該当なし）。

### 既知の制約 / 注意点
- apply_sector_cap: price が欠損（0.0）の場合、エクスポージャが過小見積りされブロックが甘くなる可能性がある（TODO コメントあり）。
- position_sizing では現状 lot_size は全銘柄共通の設計。将来的に銘柄別単元対応が予定されている。
- research / flag: DuckDB 接続を前提にしているため、prices_daily / raw_financials テーブルが存在しないと一部機能は sqlite/duckdb エラーになる（実行前にデータ整備が必要）。
- ai.news_nlp は OpenAI API に依存。API キー未設定時は ValueError を送出する。
- run_monitoring は monitoring 用 DB として settings.sqlite_path（本番 DB）を使用する設計。監視データは環境に関係なく本番 sqlite_path に記録される。
- process_priority / cpu_affinity 設定は権限の問題やプラットフォーム差により失敗する場合があり、その場合はログ警告でスキップされる。

### セキュリティ
- なし（公開コード中に明示的な脆弱性は検出されなかったが、API キーの管理・ログ出力の取り扱い等は運用上の注意が必要）。

---

参考: 各モジュールの意図やアルゴリズムはソースコード内の docstring / コメントに基づいて記載しています。実装の詳細やパラメータは該当ファイルを参照してください。