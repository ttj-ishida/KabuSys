# CHANGELOG

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

履歴の粒度はモジュール単位・機能単位で記載しています。コードベースの状態から推測して作成したため、実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-13

Added
- 初期公開リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 環境設定 / ロード
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を上位ディレクトリから探索）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数を保護する protected 機能、.env.local は .env を上書き）。
  - .env パーサを強化:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり / なしでの違いを考慮）
  - Settings クラスを実装（環境変数から各種設定を取得、バリデーション付与）。
    - 主要な環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE
    - KABUSYS_ENV に対する入力検証（development / paper_trading / live のみ許容）
    - PAPER_FILL_MODE の有効値検査（instant/partial/never/reject）

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動処理を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - DB 接続:
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用（settings.paper_sqlite_path）。本番 DB と完全分離。
      - monitoring 用テーブルの初期化（冪等）を呼び出し。
      - DuckDB 接続を確立。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時はモッククライアント想定）。
    - OrderRepository, OrderManager, RiskManager (RiskConfig), Reconciler の組み立て。
    - ExecutionEngine を EngineConfig(target_date=date.today()) で初期化しセッション実行。
    - finally ブロックで DB を確実にクローズ。

- 監視（Monitoring）起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正値（0 以下・非整数）に対してはフォールバックし警告出力。
    - 起動時にプロセス優先度を "high" に設定。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（重要: paper_trading と分離されない挙動に注意）。
    - check_once() 実行中の例外は捕捉してログ出力し、ループ継続（フェイルセーフ）。KeyboardInterrupt による正常終了をサポート。

- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化呼び出しを run_monitoring/run_execution で保証（テーブル存在確認・作成を想定）。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プラットフォーム差分を吸収する set_process_priority(level) を実装（Windows / POSIX 対応）。
    - CPU affinity を固定する set_cpu_affinity(cpu_count) を追加（None で無効化）。権限不足や未サポート環境では警告を出してスキップ。
    - AccessDenied 等の例外を捕捉して安全に退避する実装。

- ポートフォリオ構築 / ポジションサイズ
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank でブレークして最大 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分。スコア総和が 0 の場合は等配分にフォールバックし WARNING を出す。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限超過セクターの新規候補除外。sell_codes による当日売却銘柄の除外を考慮。unknown セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（ログ警告）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（risk_based / equal / score）。
      - risk_based: risk_pct / stop_loss_pct 基準でベース株数算出、per-stock 上限や lot_size 丸めを適用。
      - equal/score: weight に基づく金額配分、max_utilization・max_position_pct・lot_size を考慮。
      - aggregate cap: 全銘柄合計が available_cash を超える場合、スケールダウンして lot_size 単位で残差分を配分するロジックを実装。
      - cost_buffer によりコスト保守的見積もりをサポート。
      - price 欠損時のスキップとデバッグログ。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン・MA200 乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB 上の prices_daily / raw_financials から計算する関数を実装。データ不足時は None を返す。
    - SQL ウィンドウ関数や COUNT による不足判定を行い安定した結果を出力。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（horizons の検証あり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（同順位は平均ランク）。
    - rank / factor_summary: ランク変換、基本統計量（count/mean/std/min/max/median）を計算。
  - research パッケージ __all__ を設定し、zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI ニュース NLP（OpenAI 統合）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を ai_scores に書き込む機能を追加。
    - バッチサイズ・文字数制限（_BATCH_SIZE=20、1銘柄あたり最大記事数・最大文字数）や JSON モード厳格検証、スコアクリップ（±1.0）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ（_MAX_RETRIES 等）。
    - API キーが未設定の場合は ValueError を送出して早期検出。
    - ニュース収集ウィンドウ計算（calc_news_window）を提供（JST 基準で前日 15:00 〜 当日 08:30 を UTC に変換して扱う）。

- ツール: Paper Trading 検証レポート
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を集計してレポートを標準出力に出力する CLI を実装。
    - 指標: 稼働率（uptime）, 注文成功率（fill_rate）, 送信率（send_rate）, レイテンシ（avg/max/P95）など。P95 計算実装。
    - デフォルト閾値を定義して PASS/FAIL 判定を出力。DB ファイル欠損やテーブル欠損時にデグラード動作（N/A や 0 を返す）して安全に終了。
    - CLI オプション: --from, --to, --db。環境変数 PAPER_TRADING_SQLITE_PATH と優先順位を持つ。

Changed
- （初回リリースのため、過去からの変更はなし）

Fixed
- .env 読み込みでの文字列パースの堅牢化（クォート/エスケープ/コメント処理）により誤読による設定ミスを低減。

Security
- OpenAI API キー管理:
  - news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY のいずれかが必須。未設定時は ValueError を送出。

Notes / Important behaviors
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用 SQLite）を使用するため、paper_trading 環境でも監視データは本番 DB に書き込まれる点に注意。実運用で分離が必要であれば設定やコードの変更が必要。
- run_execution は paper_trading 環境時に paper 用 SQLite を使用して注文履歴を完全分離する設計になっている（data/paper_trading.db デフォルト）。
- process_priority / set_cpu_affinity は実行環境（権限・OS）によっては効果が出ない（警告ログを出してスキップ）ので、デプロイ先の権限設定に注意。
- calc_position_sizes のスケールダウンロジックは lot_size（現状 100）前提。将来的に銘柄別 lot_size をサポートする旨の TODO コメントあり。
- research / factor 計算は DuckDB 上のテーブル（prices_daily, raw_financials）を前提としており、外部 API 呼び出しは行わない設計。

Migration / Upgrade tips
- .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト時に便利）。
- PAPER_TRADING_SQLITE_PATH を設定すると paper_trading 環境で run_execution の DB が切り替わる。
- MONITOR_POLL_INTERVAL は秒数の整数を指定。0 や負数・非整数を与えるとデフォルト（60 秒）にフォールバックして警告を出す。

参考（実装ファイル）
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/utils/process_priority.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py

--- 

この CHANGELOG はコードの現状から推測して作成しています。実際のコミット単位の履歴を得たい場合は git のログやタグ付けに基づく CHANGELOG 生成を推奨します。