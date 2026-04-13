CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/）のフォーマットに準拠しています。  
日付はコードベースのスナップショット作成日を基準にしています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初期公開: KabuSys 基本機能群を追加。
  - パッケージ概要:
    - kabusys.__version__ = "0.1.0"
    - モジュール群: data, strategy, execution, monitoring, portfolio, research, ai, tools, utils 等を含む構成。
  - 環境設定 / ロード:
    - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パーサ実装: コメント、export 形式、シングル/ダブルクォート、エスケープを考慮した堅牢な解析。
    - OS 環境変数を保護する override/protected の取り扱い。
    - Settings クラスを提供し、各種設定（DB パス、API トークン、各種閾値、環境モード等）をプロパティ経由で取得可能。
    - 設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
  - 実行スクリプト:
    - run_monitoring.py:
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値は警告してデフォルトにフォールバック。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を「high」に設定する（utils.process_priority 経由）。
    - run_execution.py:
      - ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離。
      - BrokerClientFactory を使ったブローカー抽象化、OrderRepository/OrderManager/RiskManager/Reconciler を組み合わせてセッションを実行。
      - 起動時にプロセス優先度を「high」に設定。
      - RiskManager のデフォルトコンフィグを実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。
  - 監視/ツール:
    - monitoring_db 初期化ユーティリティ（冪等に DB の監視テーブルを準備）。
    - tools/paper_verification_report.py:
      - Paper Trading 用検証レポート生成 CLI を実装（--from, --to, --db オプション）。
      - 稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を計算し PASS/FAIL 判定を出力。
      - デフォルト DB は data/paper_trading.db。
  - ポートフォリオ構築:
    - portfolio.portfolio_builder:
      - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
      - スコア全てが0 の場合は等分配へフォールバック（警告付き）。
    - portfolio.risk_adjustment:
      - セクター集中制限（apply_sector_cap）を実装。既存保有のセクターエクスポージャを計算して新規候補を除外。
      - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装（bull/neutral/bear のマッピング、未知レジームは警告のうえ 1.0 でフォールバック）。
    - portfolio.position_sizing:
      - 株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積りを実装。
      - 可用性がない価格データや負価格のハンドリング（スキップ）や、端数配分の再割当ロジックを実装。
  - リサーチ機能:
    - research.factor_research:
      - Momentum / Volatility / Value ファクター計算を DuckDB 上の prices_daily / raw_financials データで実装。
      - MA200、ATR20、各種モメンタム（1m/3m/6m）等を計算。
    - research.feature_exploration:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）や統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
      - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - research パッケージは zscore_normalize をエクスポートしている（data.stats から提供）。
  - AI / ニュース:
    - ai.news_nlp:
      - raw_news を OpenAI API（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む仕組みを実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算して記事を集約。
      - 1銘柄あたりの記事数・文字数上限、銘柄バッチサイズ（20）で API 呼び出しを行う（JSON Mode を期待）。
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ実装の方針（定数で最大試行回数等を設定）。
      - API レスポンス検証、スコアの ±1.0 でのクリップ、部分失敗時に既存スコアを保護する DB 更新戦略（対象 code のみ DELETE → INSERT）を用意。
  - ユーティリティ:
    - utils.process_priority:
      - cross-platform（Windows / POSIX）でのプロセス優先度設定（set_process_priority）を実装。アクセス権や未対応 OS は警告出力してスキップ。
      - CPU affinity 設定（set_cpu_affinity）を実装。引数検証と失敗時の警告を含む。

Changed
- ログ出力とエラーハンドリングの改善:
  - run_monitoring のループ内で check_once() の例外を捕捉してログ出力し、次のポーリングへ継続するフェイルセーフを実装。
  - run_execution/run_monitoring で起動時に INFO レベルの basicConfig を設定。
- 設定まわりの堅牢化:
  - .env パースとロードで OS 環境変数を上書きしない安全設計（.env.local での明示上書きは可能）。

Fixed
- MONITOR_POLL_INTERVAL に 0 以下や非整数が指定された場合に time.sleep に渡して ValueError になるのを防ぐため、不正値は警告してデフォルトにフォールバックする処理を追加。

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーを環境変数または明示引数で解決し、未設定時は ValueError を返して安全に失敗する設計を採用。
- .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能（テストや CI 用）。

Notes / Implementation details
- DuckDB と SQLite の併用:
  - 時系列・ファクタ計算等の分析用途は duckdb（デフォルト: data/kabusys.duckdb）を使用。
  - 監視・トレードログ等の軽量データは SQLite（デフォルト: data/monitoring.db / data/paper_trading.db）を使用。
- Paper Trading の分離:
  - KABUSYS_ENV=paper_trading のとき実行は paper_trading 用 SQLite を使用し、本番 DB と完全分離することを明示。
- 未完/今後の注記:
  - ai.news_nlp モジュールは多くのフェイルセーフ（バッチング、リトライ、レスポンス検証）を備えているが、実運用では API コスト・レート制限・JSON モデルの安定性確認が必要。
  - position_sizing の lot_size は現状全銘柄共通の想定（将来的に銘柄別単元対応を検討するコメントあり）。
  - apply_sector_cap は price_map の欠損価格に対するフォールバック処理（前日終値等）の実装が TODO で残る。

今後の改善候補（抜粋）
- .env パースのテストケース拡充（エスケープ・複雑な引用符組合せ）。
- ai.news_nlp の部分失敗時のリトライ・ロギング拡張と実行メトリクス出力。
- position_sizing の銘柄別 lot_size 対応および手数料モデルの詳細化。
- DB スキーマとマイグレーション管理の仕組み導入（現状は init_monitoring_db の冪等初期化に依存）。

--- 
各リリースノートはコード内の実装・コメントから推測して作成しました。実際のリリース履歴や日付はリポジトリの git 履歴に基づいて調整してください。