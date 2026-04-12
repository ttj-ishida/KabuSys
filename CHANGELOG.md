CHANGELOG
=========

すべての重要な変更を時系列で記録します。本ファイルは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 今後の変更
- 各バージョン: 追加 (Added)、変更 (Changed)、修正 (Fixed)、削除 (Removed) 等のカテゴリ分け

Unreleased
----------

- なし（初回リリースに続く）

[0.1.0] - 2026-04-12
--------------------

Added
- 基本アプリケーション構成を追加
  - パッケージバージョン: __version__ = "0.1.0"
  - パッケージエクスポート: portfolio, research, execution, monitoring などの主要モジュールを公開。

- 実行スクリプト
  - run_execution.py
    - ExecutionEngine の起動エントリポイントを追加。Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() によるセッション実行を行う。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - プロセス優先度を最初に "high" に設定するユーティリティ呼び出しを追加。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）を導入。initial_portfolio_value は broker.get_available_cash() で取得。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は実行環境 (KABUSYS_ENV) に関わらず本番 sqlite_path を使用する設計。

- 設定管理
  - config.py
    - 環境変数と .env/.env.local の自動ロード機能を追加（プロジェクトルートを .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
    - .env パーサの実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
    - Settings クラスを導入し、J-Quants / kabu API / LINE / DB / 監視閾値 / システム設定等をプロパティ経由で取得。環境値のバリデーションを実施（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順＋タイブレーク（signal_rank）で候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を実装。全スコア 0 の場合は等配分にフォールバックして警告。

  - portfolio.risk_adjustment
    - apply_sector_cap: 既存保有のセクター集中度を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外しない設計）。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に基づく資金乗数を実装（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告の上 1.0 にフォールバック。

  - portfolio.position_sizing
    - calc_position_sizes: allocation_method として "risk_based" / "equal" / "score" をサポート。lot_size（単元）丸め、per-position上限、aggregate cap（available_cash）に基づくスケールダウン、cost_buffer を用いた保守的なコスト推定、スケールダウン後の余剰配分（remainders による安定な分配）を実装。
    - risk_based: 損切り率 stop_loss_pct に基づく発注株数算出。
    - スケーリングや端数処理の詳細ロジックを導入。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（cnt_200 チェック）を DuckDB 経由で計算。
    - calc_volatility: 20 日 ATR・相対 ATR、20 日平均売買代金、出来高比を計算。true_range の NULL 伝播制御、cnt_atr による充分性判定を実装。
    - calc_value: raw_financials から直近報告を取得し PER/ROE を計算（EPS=0/NULL の場合 PER は NULL）。

  - research.feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。horizons 引数の検証（1..252）あり。
    - calc_ic / rank / factor_summary: スピアマン（ランク）相関 (IC) 計算、同順位は平均ランク処理、統計サマリ（count/mean/std/min/max/median）を実装。外部依存（pandas 等）を使わない純 Python 実装。

  - research パッケージは zscore_normalize（data.stats から）含むエクスポートを提供。

- ニュース NLP（AI）モジュール
  - ai.news_nlp
    - raw_news → OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコアリング機能を追加。
    - バッチ処理（_BATCH_SIZE=20）、JSON Mode 出力の厳密バリデーション、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ・最大試行 _MAX_RETRIES）を実装。
    - 記事の集約上限（最大記事数、最大文字数）やニュースウィンドウ calc_news_window（JST→UTC 変換）を実装。
    - 書き込みは ai_scores テーブルへ（既存スコアは部分的に安全に置換する戦略を採用）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows（HIGH_PRIORITY_CLASS 等）および POSIX（nice 値）に対応し、対応外 OS はスキップ。例外（AccessDenied 等）は警告でスキップ。
    - set_cpu_affinity: 指定コア数で CPU affinity を固定する補助関数を追加（None の場合は何もしない）。入力検証あり。

- ツール
  - tools.paper_verification_report
    - Paper Trading 検証レポート生成 CLI を追加。レポート指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプションをサポート。
    - 指標の閾値（稼働率 99.0%、fill 90%、send 95%、P95 latency 200 ms）を定義し PASS/FAIL 判定を出力。

Changed
- なし（初回公開に相当）

Fixed
- なし（初回公開に相当）

Notes / Implementation details
- DB 接続
  - 多くの処理は sqlite3（監視 / 発注ログ等）と duckdb（時系列価格・ファクタ計算）を併用する設計。
  - run_monitoring は監視用 DB に本番 sqlite_path を常に使用（環境に依存しない監視）。
  - run_execution は paper_trading 環境で paper_sqlite_path を使用し本番 DB と分離。

- 設計上の注意点・TODO
  - apply_sector_cap: price_map に価格が欠損 (0.0) の場合、エクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価をフォールバックする検討を想定。
  - position_sizing: lot_size を将来的に銘柄別対応へ拡張する余地あり（stocks マスタへの lot_size 保持を想定）。
  - ai.news_nlp: OpenAI API キー未設定時は ValueError を投げる。API 呼び出し失敗時はフェイルセーフで継続する設計だが、部分失敗時の DB 更新は破壊的にならないよう配慮している。

Security
- OpenAI API キーや各種秘密情報は Settings 経由で環境変数として管理。自動 .env ロード機能は必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Deprecated
- なし

Removed
- なし

References
- ソースコードに含まれるモジュール、関数、定数の実装に基づいて記載しました。実装の詳細や運用上の注意は各モジュールの docstring / TODO コメントを参照してください。