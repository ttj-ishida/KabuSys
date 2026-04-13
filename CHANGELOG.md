# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の慣習に従っています。バージョニングは SemVer を想定します。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。
  - 環境変数ベースの設定管理 `kabusys.config.Settings` を実装。.env 自動読み込み機能（プロジェクトルート検出、.env/.env.local の読み込み順）を持ち、必要な環境変数のバリデーションを行う。
  - DuckDB / SQLite を併用するデータ基盤のサポート。
  - プロセス優先度・CPU affinity 設定ユーティリティ `kabusys.utils.process_priority` を追加（Windows / POSIX に対応、権限不足時は警告でスキップ）。

- 実行（Execution）
  - 実取引／Paper Trading に対応した起動スクリプト `src/kabusys/run_execution.py` を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使い MockBrokerClient を利用する設計（本番 DB と分離）。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てとセッション実行を実装。
    - ExecutionEngine 起動前にプロセス優先度を "high" に設定。
    - RiskManager にデフォルト RiskConfig を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - PID 管理用のファイルパス設定（Settings.pid_file_path）を追加。

- 監視（Monitoring）
  - システム監視ループ起動スクリプト `src/kabusys/run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データは一元管理）。
    - 起動時にプロセス優先度を "high" に設定。

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み計算モジュール `kabusys.portfolio.portfolio_builder`
    - select_candidates（スコア降順・同点タイブレーク）を実装。
    - 等金額配分 calc_equal_weights、スコア加重 calc_score_weights（全スコアが0のとき等金額へフォールバック）を実装。
  - リスク調整モジュール `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap（セクター別上限チェック。既存保有の時価計算、売却予定銘柄の除外に対応）。
    - calc_regime_multiplier（市場レジームに基づく投下資金乗数。未知レジームは警告の上で 1.0 でフォールバック）。
  - ポジションサイズ計算 `kabusys.portfolio.position_sizing`
    - calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元株）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer を用いた保守的見積り、残余キャッシュを使った端数配分ロジックを実装。

- リサーチ（Research）
  - ファクター計算モジュール `kabusys.research.factor_research` を追加。
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）
    - calc_volatility（20日 ATR、ATR比、平均売買代金、出来高比）
    - calc_value（PER, ROE を raw_financials と株価から計算）
    - DuckDB に対する SQL ベースの実装で、データ不足時は None を返す等の安全処理あり。
  - 特徴量探索モジュール `kabusys.research.feature_exploration`
    - calc_forward_returns（将来リターン: デフォルト [1,5,21]）
    - calc_ic（Spearman ランク相関による IC 計算、3 銘柄未満は None）
    - factor_summary（count/mean/std/min/max/median の計算、None 値除外）
    - ランキングユーティリティ rank（同順位は平均ランク）

- AI（ニュース NLP）
  - ニュースセンチメントスコアリングモジュール `kabusys.ai.news_nlp` を追加。
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別スコアを ai_scores に書き込む処理を実装。
    - 前日15:00 JST〜当日08:30 JST のウィンドウ計算（UTC 変換）を実装（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（記事数上限・文字数上限）、API レスポンス検証、±1.0 のクリップ、エクスポネンシャルバックオフ（リトライ）などを実装。
    - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を送出。

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - コマンドラインから期間指定可能（--from, --to, --db）。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、P95 レイテンシ等を集計。
    - PASS/FAIL 判定としきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を組み込み。
    - DB が存在しない場合やテーブル欠如時にフォールバックして出力。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Internal / Notes
- Settings:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許容。LOG_LEVEL も有効値制約あり。
  - .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行い、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）を実装。
- 安全性・堅牢性:
  - プロセス優先度や cpu_affinity の設定は権限不足や未対応 OS の場合に警告してスキップするフォールバックを実装。
  - DB 操作や API 呼び出し周りで例外耐性（try/except とログ出力）を考慮。
- DuckDB / SQLite:
  - DuckDB を分析用途（prices_daily, raw_financials, ai_scores など）に使用し、SQLite は主に監視・発注履歴等の軽量ストレージとして併用する想定。

---

作者注: 上記はコードベースの実装内容から推測して作成した初期リリースの変更履歴です。細かな実装意図や将来的な変更はリポジトリのコミット履歴や設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。