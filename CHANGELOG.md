CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and is maintained under
Semantic Versioning.

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリース: kabusys パッケージを追加。パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
- 起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - ポーリング中の例外はログを出力して次のポーリングへ継続。
    - 監視処理は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する。プロセス優先度を起動時に設定。
  - run_execution.py を追加。ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - 起動時にプロセス優先度を High に設定。
    - ExecutionEngine の依存コンポーネント（BrokerClient, OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててセッションを実行。
- 設定管理
  - src/kabusys/config.py を追加。
    - プロジェクトルート（.git / pyproject.toml）を基準に .env 自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env/.env.local の読み込み順・上書きルールと OS 環境変数保護（protected keys）を実装。
    - .env ファイルの行パーサを実装し、export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント処理に対応。
    - Settings クラスを提供し、各種環境設定値（DB パス、PID/KILL フラグ、閾値、PAPER_FILL_MODE 等）をプロパティとして取得可能に。
    - 必須環境変数チェック用の _require 実装（未設定時は ValueError）。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading の検証レポート生成 CLI。
    - --from / --to / --db オプションに対応。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を集計して判定（PASS/FAIL）を出力。
    - P95 の計算、欠損データに対する安全なフォールバックを実装。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア順ソートと上位 N 件選択。
    - calc_equal_weights, calc_score_weights: 重み計算。全スコアが 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有と想定価格からセクターごとのエクスポージャーを算出し、セクター上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未知レジームは警告して 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。単元株（lot_size）丸め、1 銘柄上限、aggregate cap、cost_buffer を考慮したスケーリングと残差配分ロジックを実装。
- 研究機能（DuckDB ベース）
  - research/factor_research.py を追加。
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials を使ったファクター計算（MA200、ATR20、リターン等）。欠損データに対する安全処理を実装。
  - research/feature_exploration.py を追加。
    - calc_forward_returns: 任意ホライズンの将来リターンを一回のクエリで取得する効率的な実装。
    - calc_ic: Spearman ランク相関（IC）を実装。データ不足時は None を返す。
    - factor_summary, rank: 基本統計量とランク化ユーティリティ。
  - research/__init__.py で上記と zscore_normalize をエクスポート。
- AI ニュース NLP
  - ai/news_nlp.py を追加。
    - raw_news テーブルから銘柄ごとに記事を集約し OpenAI (gpt-4o-mini) へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む処理を実装（バッチサイズ、トークン肥大化対策、スコアクリッピング、部分失敗時の保護ロジックなど）。
    - calc_news_window を実装して JST ベースのニュースウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC に変換。
    - API 呼び出しに対してリトライ（429/ネットワーク/5xx 用）と指数バックオフを実装。API キーは引数または OPENAI_API_KEY 環境変数を使用。
- ユーティリティ
  - utils/process_priority.py を追加。
    - set_process_priority: Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定。権限不足時は警告してスキップ。
    - set_cpu_affinity: 最初の N コアへ固定する機能。引数チェックと失敗時のフォールバックを実装。

Changed
- run_execution: 起動時に monitoring 用テーブルが存在することを保証するため init_monitoring_db を呼び出す（冪等）。
- 各所で欠損データやゼロ割りの可能性に対するガードを追加し、安全に None やデフォルトを返す実装を採用（ファクター計算・レポート生成・position sizing 等）。
- .env パーサでより多様な .env 記法（export, quoted values, escapes, inline comments）に対応。

Fixed
- run_monitoring の MONITOR_POLL_INTERVAL が 0 以下や不正文字列の場合に time.sleep に渡して ValueError になる問題を防止（不正値はデフォルト 60 秒にフォールバックして警告ログを出力）。

Security
- 環境変数読み込みで OS 環境変数を上書きしないよう保護（protected set）を導入。必要に応じて .env.local で明示的に上書き可能だが、既存 OS 環境変数は既定で保護される。

Breaking Changes
- Settings.env（KABUSYS_ENV）に許容される値を厳格化（development / paper_trading / live のみ）。無効な値を設定している場合、Settings.env の参照で ValueError を送出するため起動時に失敗します。設定を見直してください。
- PAPER_FILL_MODE の値を厳格に検証するようになりました（instant | partial | never | reject のみ）。不正な値は ValueError を送出します。
- LOG_LEVEL の値検証を追加（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ）。既存のカスタム値は受け入れられません。

Notes / その他
- 各種 DB 接続で DuckDB / SQLite を併用（研究系は DuckDB、監視・実行周りは SQLite）。
- ai/news_nlp の OpenAI 呼び出しは外部 API に依存するため、API キー未設定時は例外となります（呼び出し側で処理してください）。
- 一部関数内で将来の拡張について TODO コメントあり（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の価格フォールバック等）。

---

今後の予定（例）
- テストカバレッジ拡充（ユニットテスト・統合テスト）
- 実行時のメトリクス収集・可視化強化
- broker factory のモック/スタブを明示化してローカル検証を容易にする改善

---