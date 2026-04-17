Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[0.1.0] - 2026-04-17
-------------------

Added
- 基本パッケージ初期リリース（kabusys 0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60秒）。不正値はデフォルトへフォールバック。
    - 停止はプロジェクト直下 data/stop_requested.flag ファイルの存在検知で行う。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（監視用 DB）を使用して初期化。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント作成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 起動前・実行中ともに data/stop_requested.flag による停止制御を実装。実行 PID を data/execution.pid に出力する想定。

- 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）と上書き制御（protected）を実装。
    - .env パーサの強化:
      - export プレフィックス対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ対応
      - クォート無し時のインラインコメント扱い改善
    - Settings クラスを導入し、アプリで使う全環境変数をプロパティとして提供（DB パス、API トークン、監視閾値、環境種別など）。
    - env 値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を追加。
    - 便利プロパティ: is_live / is_paper / is_dev。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレーク: signal_rank）select_candidates を追加。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加（スコア全0時に等配分へフォールバックし警告）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を追加（既存保有のセクター比率を計算して候補除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップ、未知レジームは警告し 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加（allocation_method: risk_based / equal / score をサポート）。
    - 単元株（lot_size）丸め、最大ポジション割合・利用上限・コストバッファを考慮した aggregate cap スケーリングを実装。
    - price 欠損時のスキップやログ出力など堅牢性考慮。

- リサーチ / ファクター計算
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算関数を追加（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - mom_1m/3m/6m, ma200_dev, atr_20, atr_pct, avg_turnover, volume_ratio, per, roe 等を計算。データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary を追加。外部ライブラリに依存しない純 Python 実装。
    - rank ユーティリティは ties を平均ランクで処理する。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加（コマンドライン: --from / --to / --db）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを算出し、閾値による PASS/FAIL 判定を行う。
    - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 判定閾値の定義 (稼働率>=99%、fill>=90%、send>=95%、P95<=200ms)。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news から銘柄ごとのセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores テーブルへ書き込む機能を追加。
    - ニュースウィンドウの計算（前日15:00 JST 〜 当日08:30 JST -> UTC に変換）を実装。
    - 1銘柄あたりの最大記事数/文字数制限、最大バッチサイズ、リトライ（429/タイムアウト/5xx などに対する指数バックオフ）、レスポンス検証、スコアクリップ（±1.0）などを実装。
    - 実行時に OPENAI_API_KEY が必要（引数での指定も可）。失敗時はフェイルセーフでスキップ。
    - （注）ソースの一部は省略・途中で切れている可能性があるが、設計と多くの処理フローは実装済み。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows / POSIX の差を吸収（Windows 用 HIGH_PRIORITY_CLASS、Linux/Mac の nice 値）。アクセス権限がない場合は警告してスキップ。
    - set_cpu_affinity を追加（N コアにピン留め）。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db 呼び出し（監視テーブルの冪等初期化）は run_monitoring / run_execution の起点で実行。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー、J-Quants / Kabu API の機密情報は環境変数で管理（Settings で必須チェックを行う）。  
  - 環境変数未設定時は起動時に ValueError を投げる設計（必要な箇所）。

Notes / Migration
- 環境変数の追加・必須化:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（news_nlp を使う場合は必須）
  - KABUSYS_ENV（development / paper_trading / live のいずれか。デフォルト: development）
  - PAPER_FILL_MODE（paper_trading 時のモック約定動作、 instant|partial|never|reject。デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
  - その他: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等

- DB 分離:
  - paper_trading モードでは専用 SQLite を使用するため、本番監視データ・発注データと分離されます。既存ワークフローを paper_trading で使う場合は PAPER_TRADING_SQLITE_PATH を確認してください。

- .env 自動ロード:
  - プロジェクトルート検出に失敗する場合は自動ロードをスキップします。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化可能。

- プロセス優先度:
  - run_monitoring / run_execution 起動時に set_process_priority("high") を呼び出すため、実行環境によっては権限不足で warnings が出る可能性があります（その場合は設定をスキップ）。

- 未実装 / TODO（今後の改善候補）
  - position_sizing: 銘柄別単元情報（lot_size）の外部マスタ化。
  - risk_adjustment.apply_sector_cap: price 欠損時のフォールバック価格（前日終値等）の採用。
  - news_nlp.py: ソース末尾が途中で切れている可能性があり、DB 書き込み周りの細部実装やエラーハンドリングの最終確認が必要。
  - DuckDB / SQLite 周りの接続プールや並列実行性の最適化。

お問い合わせ
- このリリースに関する質問や不具合報告は開発チームまでお知らせください。