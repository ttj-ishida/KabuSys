CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用しています。

Unreleased
----------

（現在の開発ブランチに対する未リリースの変更はここに記載します。）


[0.1.0] - 2026-04-12
-------------------

Added
- 基本パッケージ初期リリース
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として設定。

- 実行系（Execution）
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py を追加。
    - ExecutionEngine の起動フローを実装（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて実行）。
    - 実行時に sqlite3 と DuckDB に接続し、セッション終了時にクローズする。
  - Paper Trading モード対応:
    - KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を使用（BrokerClientFactory 経由）。
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）を用いて本番 DB と完全分離。
    - PAPER_FILL_MODE（instant/partial/never/reject）でモックの約定挙動を指定可能。
    - RiskManager の既定パラメータ（max_position_pct 等）を RiskConfig に定義し、初期ポートフォリオ値をブローカーの get_available_cash() から初期化。

- 監視（Monitoring）
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py を追加。
    - SystemMonitor を用いたポーリングループ（デフォルト 60 秒）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能。無効値はデフォルトにフォールバックして警告。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視データは本番 DB を参照）。
    - プロセス優先度を起動時に "high" に設定する処理を組み込み（set_process_priority 呼び出し）。

  - 監視テーブル初期化ヘルパー init_monitoring_db を呼び出して存在を保証（冪等）。

- 設定管理（Config）
  - src/kabusys/config.py:
    - Settings クラスを導入し、環境変数から各種設定を取得するプロパティ群を提供。
    - 自動 .env ロード機能:
      - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む。
      - OS 環境変数は保護され、.env.local は上書きを許可（ただし OS 環境変数を保護）。
      - export KEY=val 形式、クォート（'"/）内のエスケープ、インラインコメント処理等に対応したパーサ実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途）。
    - 設定プロパティ:
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PID / Kill flag 関連パス
      - しきい値（CPU/MEMORY/DISK）
      - 環境タイプ検証（KABUSYS_ENV = development | paper_trading | live）
      - LOG_LEVEL 検証
      - ほか API トークン等の必須取得ヘルパ _require

- ポートフォリオ構築（Portfolio）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）:
    - select_candidates: スコア降順、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: スコアが全て 0 の場合は等分配にフォールバック（警告ログ付き）。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market regime に応じた資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知は警告の上 1.0）。
  - 取引数量計算（src/kabusys/portfolio/position_sizing.py）:
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に対応。
    - リスクベース算出（risk_pct / stop_loss_pct に基づく）、単元株（lot_size）丸め、per-stock/max aggregate cap を実装。
    - cost_buffer を考慮した保守的見積り、利用可能資金を超える場合のスケールダウンと端数補正ロジックを実装。

- 研究・ファクター計算（Research）
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を追加。DuckDB の prices_daily / raw_financials を用いた実装。
    - 長期 MA、ATR、出来高系指標、PER/ROE の計算ロジックを含む。欠損データに対する安全処理あり。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）、rank（平均ランク処理）を追加。
    - 外部依存を持たない純粋 Python 実装、DuckDB を入力に利用。

- AI ニュース NLP（news_nlp）
  - src/kabusys/ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ、最大記事文字数、最大記事数、JSON Mode を利用した堅牢な入出力想定。
    - 429/ネットワーク断/タイムアウト/5xx に対するリトライ（指数バックオフ）と最大リトライ回数管理。
    - 結果のバリデーションとスコアの ±1.0 クリップ、部分失敗時の既存スコア保護（変更対象コードを限定して DELETE→INSERT）。

- ユーティリティ（Utils）
  - src/kabusys/utils/process_priority.py:
    - set_process_priority(level) で Windows / POSIX（Linux/Mac/FreeBSD）に対応した優先度設定（psutil 利用）。
    - set_cpu_affinity(cpu_count) で最初の N コアへプロセスをピン留めする機能。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール
  - Paper Trading 検証レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py
    - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して標準出力にレポートを出力。
    - PASS/FAIL の基準値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ、DB ファイルパス指定（--db / 環境変数）に対応。

- DuckDB / SQLite の併用
  - 実行系・研究系で DuckDB（時系列価格や財務データ）を利用し、監視・ログは SQLite を利用する設計。

Fixed
- 監視・起動シーケンスの堅牢化:
  - 起動時にプロセス優先度設定を最初に実行するよう統一。
  - run_execution で監視テーブルの初期化（init_monitoring_db）を行い、監視テーブルが存在しない場合でも起動を妨げないようにした（冪等）。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取り扱い:
  - news_nlp.score_news は引数や環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出して安全に失敗する設計。

Notes / Known limitations
- price_fallback:
  - apply_sector_cap 内の注記のとおり、price_map に 0.0 や欠損があるとエクスポージャーが過少評価される可能性がある。将来的に前日終値や取得原価をフォールバックする拡張を検討。
- lot_size の取り扱い:
  - 現状は全銘柄共通の lot_size（デフォルト 100）で算出。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO コメントあり）。
- News NLP の外部 API 呼び出しはネットワーク依存のため、API エラー時は部分的にスコアが欠損する可能性がある（フェイルセーフでスキップ動作）。
- Research モジュールは DuckDB のテーブル構成（prices_daily / raw_financials）に依存するため、スキーマ不一致時は sqlite / duckdb 側で調整が必要。

Acknowledgements
- 本ログはソースコードの内容（モジュール、関数、ドキュメント文字列、定数、TODO コメント等）から推測して作成しています。細部の挙動や将来的な変更はソースを参照してください。