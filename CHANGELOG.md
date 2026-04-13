CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and aims to maintain
backward‑compatible, human‑readable release notes.

フォーマット:
- Added: 新機能
- Changed: 互換性のある変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当時に記載

[Unreleased]
------------

（現在未リリースの変更はありません）

0.1.0 - 2026-04-13
-----------------

Added
- パッケージ初回リリース。
- 基本アーキテクチャと主要コンポーネントを実装。
  - kabusys.config (src/kabusys/config.py)
    - .env 自動読み込み機能（プロジェクトルートに .git または pyproject.toml がある場合）。
    - .env/.env.local の読み込み順序と上書きポリシー（OS環境変数保護）。
    - 高度な .env パース処理（クォート文字列、エスケープ、インラインコメントの取り扱い）。
    - Settings クラス（プロパティ経由で各種設定を取得）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視周りの設定を提供。
  - 実行用スクリプト
    - run_execution (src/kabusys/run_execution.py)
      - ExecutionEngine の起動スクリプト。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立ててセッションを実行。
      - プロセス起動時にプロセス優先度を "high" に設定。
      - DuckDB/SQLite 接続の生成とクローズ処理を管理。
    - run_monitoring (src/kabusys/run_monitoring.py)
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
      - プロセス優先度を "high" に設定。
  - 監視 DB 初期化ユーティリティ
    - init_monitoring_db を用いて監視用テーブルの存在を保証（冪等）。
  - ポートフォリオ構築関連 (src/kabusys/portfolio/)
    - portfolio_builder: 銘柄候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
      - calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし警告ログを出す。
    - risk_adjustment: セクター制限 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier)。
      - apply_sector_cap は当日売却予定銘柄をエクスポージャ計算から除外可能。unknown セクターは上限適用外。
      - calc_regime_multiplier は 'bull'/'neutral'/'bear' を扱い、未知レジームは 1.0 でフォールバック（警告）。
    - position_sizing: 株数決定ロジック (calc_position_sizes)
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）、max_position_pct、max_utilization、cost_buffer を考慮した計算と aggregate cap（利用可能現金を超えた場合のスケールダウン）処理。
      - スケールダウン後の端数処理（lot_size 単位で残差を再配分するロジック）を実装。
  - 研究・ファクター (src/kabusys/research/)
    - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクターを計算。
      - MOMENTUM（1/3/6M リターン, MA200 乖離）、ATR（20 日）、出来高/売買代金指標等を提供。
      - 欠損データ時は None を返す設計。
    - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、統計サマリー (factor_summary)、rank ユーティリティ。
      - calc_ic はスピアマンのランク相関を実装（同順位は平均ランク処理）。
      - calc_forward_returns は任意ホライズン（デフォルト [1,5,21]）をサポート。
  - AI ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols からニュースを銘柄別に集約し、OpenAI API (gpt-4o-mini を想定) を使って銘柄ごとのセンチメントスコア（-1.0〜1.0）を生成して ai_scores に書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）とチャンク処理（最大 20 銘柄/チャンク）。
    - トークン肥大化対策（1 銘柄あたりの記事・文字数上限）、429/ネットワーク/5xx のリトライ（指数バックオフ）処理、レスポンス検証、スコアの ±1.0 クリップ。
    - API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError を送出。
    - 部分失敗時にも既存スコアを守るため、対象コードを限定して DELETE → INSERT を行う方針。
  - ツール (src/kabusys/tools/paper_verification_report.py)
    - Paper Trading 用検証レポート生成 CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 等。
    - デフォルト DB は data/paper_trading.db。--db オプションで指定可能。
    - 判定基準（閾値）を定義（稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）。
    - P95 計算ユーティリティ、日付フィルタ指定（--from/--to）。
  - ユーティリティ (src/kabusys/utils/process_priority.py)
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX(Linux, Darwin, FreeBSD) の差分吸収。アクセス権限や未対応 OS の場合は警告を出してスキップ。
  - パッケージ情報 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"

Fixed
- 環境変数・設定周りの堅牢化:
  - .env 行のパースでクォート・エスケープ・インラインコメントを正しく扱うように実装。
  - MONITOR_POLL_INTERVAL の不正値（0/負数/非整数）を検出して警告し、デフォルト値にフォールバックする処理を追加。
- SQLite / DuckDB 接続ライフサイクルの明確化（スクリプト実行後の確実な close）。

Notes / Known limitations / TODO
- apply_sector_cap 内の注記:
  - price_map が欠損（0.0）の場合にエクスポージャを過少見積りする可能性があり、将来的に前日終値や取得原価をフォールバック価格として利用することが検討されている（TODO コメントあり）。
- calc_position_sizes:
  - 現状は全銘柄共通の lot_size を使用。将来的に銘柄別単元情報を持たせる拡張を想定（TODO）。
- AI ニュース NLP:
  - 実運用では OpenAI API の利用料金・レート制限に注意。失敗時はフェイルセーフでスキップする設計だが、部分失敗に伴う運用ルールの整備が推奨される。
- 自動 .env ロードはプロジェクトルートが特定できない場合はスキップされる（CI / 配布後の挙動に注意）。
- run_monitoring は監視 DB として常に本番 sqlite_path を参照する設計になっているため、Paper Trading 環境で監視を分離したい場合は注意が必要。

Usage / Migration notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（Settings のプロパティ参照）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading を設定すると run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用し、本番 DB と分離して動作します。
  - PAPER_FILL_MODE により MockBroker の挙動（instant/partial/never/reject）を制御できます。
- 監視:
  - MONITOR_POLL_INTERVAL で監視ループのポーリング間隔を秒単位で設定できます（不正値は無視され 60 秒にフォールバック）。
- OpenAI:
  - NEWS NLP を利用する場合は OPENAI_API_KEY を環境変数か関数引数で指定してください。

Acknowledgements
- ドキュメント内の多くの設計ノート（PortfolioConstruction.md, StrategyModel.md 等）に準拠して実装されています（ドキュメントは別途管理）。

----- End of CHANGELOG -----