Keep a Changelog 準拠の形式で、コードベースから推測した変更履歴を日本語で作成しました。初回リリースを v0.1.0（2026-04-13）とし、主要な機能追加・設計上の注意点・既知の制限をまとめています。

CHANGELOG.md
=============

すべての変化は慣例に従い分類しています。セマンティックバージョニングやリリース管理に合わせて更新してください。

Unreleased
----------
- （現在未リリースの変更はありません）

[0.1.0] - 2026-04-13
-------------------
Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、MockBrokerClient による分離運用をサポート。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててセッション実行。
    - RiskManager の初期設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors/ window, max_drawdown 等）を実装。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用するように設計（監視 DB は環境分離しない想定）。
    - プロセス優先度を起動直後に "high" に設定。

- 設定管理
  - config.py: 環境変数／.env ファイル読み込みユーティリティを実装。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 行パーサは export 形式・クォート・エスケープ・インラインコメント等に対応。
    - Settings クラスを導入し、各種設定値（DB パス、API トークン、PID ファイルパス、各種閾値、環境判定メソッドなど）をプロパティとして提供。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）や KABUSYS_ENV / LOG_LEVEL の検証を実装。

- 監視/モニタリング
  - monitoring_db 初期化呼び出し（冪等）を Execution/Monitoring 起動時に行うように組み込み。

- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順 / signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクターごとの既存エクスポージャーを計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは WARN を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score に対応した株数決定ロジックを実装。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超えた場合のスケーリングと端数処理）を実装。
      - cost_buffer による保守的コスト見積りを考慮。
      - price が欠損/0 の場合はスキップする安全策を実装。

- 研究（research）機能
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いたファクター計算を実装（MA200、ATR20、各期間リターン、PER/ROE 等）。
    - 大規模スキャンを避けるための日数バッファ設定や NULL ハンドリングを配慮。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）計算（最小有効件数の判定あり）。
    - rank / factor_summary: ランク化（同順位は平均ランク）や基本統計量を計算。
  - research/__init__.py で公開 API を整理（zscore_normalize などを re-export）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news / news_symbols から記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとにセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込み。
    - バッチ処理（20 銘柄/チャンク）、トークン肥大化対策（記事数上限・文字数上限）、429/ネットワーク/5xx 等に対する指数バックオフ＋リトライを実装。
    - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分失敗に備えた安全な DB 書換（対象コードのみ置換）を設計。
    - OPENAI_API_KEY の環境変数または引数指定を必須化。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。日時フィルタ、各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を算出して PASS/FAIL を出力。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。

- ユーティリティ
  - utils/process_priority.py
    - cross-platform なプロセス優先度設定（Windows: psutil の PRIORITY_CLASS、POSIX: nice 値）。対応 OS を判定してログ出力と安全な失敗（権限不足時は警告）を行う。
    - set_cpu_affinity を追加し、指定コア数への固定をサポート（権限/未対応環境ではスキップ）。

Changed
- （初回リリースのため「変更」はなし）

Fixed
- （初回リリースのため「修正」はなし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーの未設定時に明確なエラーを上げるようにし、秘密情報の取扱いに注意する旨をドキュメント化。

Notes / Implementation details
- DB
  - DuckDB を分析用（prices_daily / raw_financials / ai_scores など）に使用。SQLite は監視・paper_trading の軽量永続化に使用。
- 環境分離
  - ExecutionEngine は paper_trading モード時に paper_sqlite_path を用いて本番 DB と完全に分離する設計。
  - ただし、監視（run_monitoring）は設計上「本番 sqlite_path を使用する」挙動になっているため、本番/検証の分離方針と運用上の注意が必要。
- ロバスト性
  - API 呼び出しや外部状態に対する失敗はログ出力後にフォールバック/スキップする方針（フェイルセーフ）。
- 設計上の TODO / 既知の制限
  - apply_sector_cap: price が欠損（0.0）だとエクスポージャーが過少見積りされ、想定外に除外が回避される可能性がある（将来的に価格フォールバックの導入を検討）。
  - position_sizing: 将来的には銘柄ごとの lot_size を持たせる拡張（stocks マスタを想定）。
  - ai/news_nlp: JSON Mode 応答の厳密な検証や API レスポンススキーマの変更に対する互換性チェックが重要。
  - .env 自動読み込みはプロジェクトルート判定に依存するため、配布後は環境変数管理に注意。

Authors
- 初期実装チーム（コードコメントと実装から推測して作成）。

ライセンス
- コードベースにライセンスファイルがない場合は別途指定してください。

補足
- 本 CHANGELOG はリポジトリ内のソースコード（docstring・コメント・実装）からの推測に基づき作成しています。実際の変更履歴やコミットログが存在する場合はそちらを優先し、必要に応じて内容を差し替えてください。