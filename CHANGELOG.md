CHANGELOG
=========

すべての注目すべき変更はここに記録します。フォーマットは "Keep a Changelog" に準拠しています。
リリースはセマンティックバージョニングに従います。

[Unreleased]
-------------
（なし）

[0.1.0] - 2026-04-17
--------------------
初回リリース。日本株自動売買フレームワーク "KabuSys" の基本コンポーネントを実装しました。
主な追加点・特徴は以下の通りです。

Added
- 基本パッケージ
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージエクスポートの整理（portfolio / research / ... の public API を __all__ で定義）。

- 設定管理 (.env 自動読み込み / Settings)
  - 環境変数・.env ファイルを安全にロードする自動ロード機構を実装。
    - プロジェクトルートは .git または pyproject.toml を探索して特定（CWD 非依存）。
    - .env と .env.local の読み込みルールを実装（OS 環境変数は保護、.env.local は上書き可）。
    - export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、コメント処理など豊富なパース対応。
  - Settings クラスを実装し、各種設定値をプロパティで取得可能に。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）、PID/kill フラグ、しきい値（CPU/MEM/DISK）等を提供。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力検証を実装（不正値時は ValueError を送出）。
  - settings インスタンスをモジュールレベルで公開。

- 実行系（Execution）
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成をサポート（MockBrokerClient を想定）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと起動ルーチンを実装。
    - 停止フラグ (data/stop_requested.flag) を監視し、外部からの停止要求に対応。
    - 実行用 PID ファイル (data/execution.pid) を利用。

- 監視系（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - Monitoring は環境に依らず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) を検知して安全にループを終了。
    - 起動時にプロセス優先度を "high" に設定。

- プロセス制御ユーティリティ
  - utils/process_priority.py を追加。
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度（nice/HIGH_PRIORITY_CLASS）を設定。
    - set_cpu_affinity(cpu_count): 最初の N コアへプロセスをピン留めする機能を実装。
    - 権限不足や未対応 OS の場合はログに警告を出してスキップするフェイルセーフを実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順・タイブレークロジック実装。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限ロジック。既存保有をもとにセクター別エクスポージャを算出し、上限超過セクターの新規候補を除外。
      - "unknown" セクター（sector_map に未登録）は除外対象としない。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
      - Bear -> 0.3, Neutral -> 0.7, Bull -> 1.0 のマッピングを採用。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数算出ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
      - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づくロジック。
      - equal/score: 重み (weights) と max_utilization に基づくロジック。
      - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合はスケーリング）を実装。
      - cost_buffer による保守的コスト見積り、残差処理による追加配分ロジックを実装。
      - price 欠損時はスキップする安全策を実装。
    - 将来的な拡張ポイント（TODO）として銘柄別 lot_size マップ導入の注記あり。

- リサーチ / ファクター計算
  - research/factor_research.py を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20, ATR%（ATR/close）, 20日平均売買代金、出来高比率を計算。true_range の NULL 処理に注意を払った実装。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - DuckDB を用いた SQL+ウィンドウ関数ベースの実装で、大規模データに対する効率を重視。
  - research/feature_exploration.py を実装。
    - calc_forward_returns: 将来リターン（任意ホライズン）を計算。入力検証（horizons の範囲）を実施。
    - calc_ic: Spearman ランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクで処理する実装（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
  - research パッケージは data.stats.zscore_normalize をエクスポートするための __init__ を用意。

- ツール（Paper Trading 検証レポート）
  - tools/paper_verification_report.py を追加。
    - paper_trading の SQLite DB（デフォルト: data/paper_trading.db）から各種指標を集計し、人間向けレポートを標準出力に表示。
    - 指標: 稼働率 (uptime)、注文成功率 (fill_rate)、送信率 (send_rate)、リスク却下数、API レイテンシ（avg / max / P95）。
    - PASS/FAIL の閾値を導入（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200 ms）。
    - CLI 実行可能: python -m kabusys.tools.paper_verification_report および --from/--to/--db オプションをサポート。
    - レポートは期間フィルタ（ISO8601 UTC）に基づいて集計。

- AI ニュース NLP（OpenAI ベースのセンチメントスコアリング）
  - ai/news_nlp.py を実装（ニュース集約 → OpenAI へバッチ送信 → ai_scores テーブルへ書き込み）。
    - gpt-4o-mini を想定した設計とし、JSON モードでの厳密な出力を期待するプロンプトを用意。
    - タイムウィンドウ：target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリ）。
    - 1回の API コールで最大 20 銘柄を処理するバッチ化、1 銘柄あたりの最大記事数・最大文字数でトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフリトライを実装（上限あり）。
    - レスポンス検証、スコアの ±1.0 クリッピング、部分失敗時の DB 保護（対象コードのみ差し替え）等のフェイルセーフ設計。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未提供時は ValueError を投げる。

Changed
- 環境変数の振る舞いと既定値の明確化
  - MONITOR_POLL_INTERVAL の不正値は警告ログを出してデフォルト（60 秒）にフォールバック。
  - .env 読み込みでは OS 環境変数を保護（上書き禁止）する動作を定義。
  - KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の値検証を追加し、不正値時に早期に検出するようにした。

Fixed
- （初期リリースのため特定のバグ修正履歴はなし。ただし各モジュールで入力検証・NULL 安全策を加え、実運用でのクラッシュを抑制。）

Known issues / Notes
- ai/news_nlp.py 内の実装は堅牢化を意図した設計となっているが、OpenAI ライブラリのバージョンや API 仕様に依存します。実運用前に十分な統合テストを推奨します。
- portfolio/position_sizing.py: 将来的な拡張として銘柄別の lot_size を渡せるようにする TODO コメントあり。
- portfolio/risk_adjustment.py: price が欠損（0.0）の場合、エクスポージャーが過少見積りになる可能性があり、将来的に前日終値等のフォールバックを導入する注記あり。
- process_priority の優先度設定・CPU affinity 設定は OS 権限に依存します。権限不足時は警告を出してスキップします。
- run_monitoring/run_execution はデータディレクトリ（data/）内のフラグファイル・PID ファイルに依存した制御を行います。運用環境でのパス確認を行ってください。

Security
- API キー等の秘密情報は環境変数（または .env）での注入を想定。バンドルやログ出力での露出に注意してください。

Acknowledgments
- 本リリースは内部モジュール間のインターフェースを明確にすることを目的とした最初の安定版です。今後、テストカバレッジ拡充・ドキュメント整備・運用観点の改善を行っていきます。