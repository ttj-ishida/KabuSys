# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
このファイルはコードベースから推測される機能追加・仕様・既知の制約をまとめたものであり、実装のコメントや docstring を元に作成しています。

## [Unreleased]

- （今後の予定やマイナー改善・ドキュメント追記などを記載）

---

## [0.1.0] - 2026-04-12

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装・公開。

### Added
- 基本パッケージとバージョン情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）。
  - .env パーサ実装（コメント、export、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 環境変数値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - 各種パス・閾値を Settings オブジェクトで一元管理（duckdb/sqlite/paper_trading 等）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`。

- 実行ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差分を吸収するプロセス優先度設定（Windows / POSIX 対応）。
  - CPU affinity 固定ユーティリティ（core 数指定）。
  - 権限不足などで設定失敗した場合は警告してスキップする堅牢な実装。

- 監視（kabusys.monitoring + run_monitoring.py）
  - SystemMonitor のポーリングループ起動スクリプト `run_monitoring.py`。
  - 起動時にプロセス優先度を "high" に設定。
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒、1 未満はデフォルトにフォールバック）。
  - 監視は環境に関わらず本番用 sqlite_path を使用して監視テーブルを初期化（冪等）。

- 実行エンジン（kabusys.execution + run_execution.py）
  - ExecutionEngine の起動スクリプト `run_execution.py`。
  - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite DB を使用（data/paper_trading.db がデフォルト）および MockBrokerClient を利用して本番 DB から分離。
  - 起動時にプロセス優先度を "high" に設定。
  - ExecutionEngine のためのコンポーネント群 (BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler 等) を組み立ててセッションを実行。
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。initial_portfolio_value はブローカからの available_cash を使用。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定と重み計算（portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分。スコア総和が 0 の場合は等金額へフォールバック（警告出力）。
  - セクター集中とレジーム調整（risk_adjustment）
    - apply_sector_cap: 既存保有を基にセクター比率を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。未知レジームは 1.0 でフォールバック（警告）。
  - ポジションサイズ計算（position_sizing）
    - calc_position_sizes: risk_based / equal / score 各方式をサポート。LOT 単位切り捨て、1 銘柄上限・合計投下上限（aggregate cap）に対するスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による再配分ロジックを実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research: momentum / volatility / value の計算関数を実装。
    - Momentum: 1M/3M/6M リターンと 200 日 MA 乖離（必要行数が足りない場合は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比（NULL の伝播制御を考慮）。
    - Value: raw_financials から最新財務データを取り出して PER / ROE を算出。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ、ランク付け（同順位は平均ランク）。
  - DuckDB 接続を受け取り SQL + Python で完結する設計（外部 API 非依存、prices_daily / raw_financials を使用）。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を UTC に変換して対象記事を抽出。
  - 1 銘柄あたり記事数・文字数上限（トリミング）、最大バッチサイズ、レスポンス検証、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数的バックオフリトライ等の堅牢化。
  - OpenAI API キーの未設定時は ValueError を送出。

- ツール（kabusys.tools）
  - paper_verification_report: Paper Trading DB（デフォルト data/paper_trading.db）から検証レポートを生成する CLI スクリプト。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し、パス/フェイル基準（稼働率 99% 等）に基づく判定を標準出力に表示。
    - P95 の計算、日付フィルタ (--from / --to)、DB 存在チェック、テーブル欠損時のフォールバックを実装。

- DB 初期化ユーティリティ
  - monitoring 用テーブルの初期化関数 `init_monitoring_db` を呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Removed
- （初回リリースのため削除履歴はなし）

### Notes / Known limitations
- news_nlp の OpenAI 呼び出しは外部 API に依存しており、API キー未設定時は明示的に例外を発生させる設計。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップする（配布後の動作安定性を考慮）。
- position_sizing の価格欠損時の挙動について TODO があり（price=0 の場合の前日終値フォールバック等、将来的に改善予定）。
- DuckDB の executemany に関する注意（空パラメータを渡さないチェック等）や、Paper Verification レポートはテーブルがない場合に安全にフォールバックする実装が含まれる。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでの実行を想定して警告で安全にスキップする。

---

（以降のバージョンでは機能追加・バグ修正・API 互換性の変更点を同様のフォーマットで記載してください）