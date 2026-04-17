CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠しています。  
リリースノートは主にコードベースから推測して作成しています。実装の意図や運用上の注意点は該当箇所の docstring やログメッセージに基づき記載しています。

[Unreleased]
------------

- ドキュメント的な差分はなし（この CHANGELOG は初期リリース内容を v0.1.0 としてまとめています）。
- 注意: src/kabusys/ai/news_nlp.py の末尾が途中で切れており、_fetch_articles 呼び出し以降の処理が未完の状態に見えます。実稼働で利用する前に実装の完了およびテストが必要です。

[0.1.0] - 2026-04-17
--------------------

Added
- 基本パッケージ初期実装（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を開始。
    - data/stop_requested.flag を監視して安全に停止。実行中 PID を data/execution.pid に管理。
    - プロセス優先度を "high" に設定するユーティリティ呼び出しを最初に行う。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバックして警告出力）。
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）。
    - 停止フラグ (data/stop_requested.flag) による終了をサポート。
    - duckdb を併用している想定の接続処理を含む。

- 設定・環境変数管理
  - config.py: Settings クラスの導入
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化。
    - .env ファイルのパースは export 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの挙動を考慮して実装。
    - 必須キー取得用の _require() ヘルパーを実装（未設定時は ValueError）。
    - 設定プロパティ群:
      - J-Quants / kabu API 関連（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL）
      - LINE Messaging API（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）
      - データベースパス: duckdb_path, sqlite_path, paper_sqlite_path
      - Paper Trading 固有: paper_fill_mode（"instant"|"partial"|"never"|"reject"、不正値はエラー）
      - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, CPU/MEM/DISK 閾値
      - 環境: env 値の検証（development, paper_trading, live）、log_level 検証
      - ヘルパー properties: is_live / is_paper / is_dev

- モニタリング DB 初期化
  - monitoring_db の初期化呼び出しを run_monitoring と run_execution に導入（init_monitoring_db を通じて監視テーブルが存在することを保証）。

- プロセス制御ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level) を実装（"high"|"normal"|"low"）。
      - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して適切な nice / priority クラスを設定。
      - 許可が無い場合や未対応 OS ではログを吐いてスキップ。
    - set_cpu_affinity(cpu_count) を実装（None なら何もしない、1 未満は ValueError）。
    - 例外キャッチとログ出力で安全に動作する設計。

- Portfolio（ポートフォリオ構築）ライブラリ
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレークして上位 N を返す。
    - calc_equal_weights: 等金額配分（1/N）を返す。
    - calc_score_weights: スコア割合により重みを計算。全てのスコアが 0 の場合は等配分にフォールバックして警告ログ。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限 (max_sector_pct) を超えるセクターの新規候補を除外（"unknown" セクターは上限対象外）。
      - 当日売却予定銘柄を除外して既存エクスポージャーを計算可能（sell_codes）。
      - price の欠損時の注意コメント（将来的なフォールバック提案）。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた資金乗数を返す（未知は 1.0 でフォールバックし警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 銘柄ごとの発注株数を計算する主要関数を実装。
      - allocation_method: "risk_based"（リスクベース）および "equal" / "score" に対応。
      - リスクベース: risk_pct, stop_loss_pct を考慮した計算。
      - 等配/スコア配分: weight に応じた割付。
      - lot_size（単元株）に丸め、max_position_pct（個別上限）、max_utilization（総利用率）、cost_buffer（手数料/スリッページ見積り）を考慮。
      - available_cash を超過した場合のスケールダウンと残余キャッシュを使ったロット単位での追加配分ロジックを実装（端数処理の安定性を意識）。

  - portfolio/__init__.py で上記関数をエクスポート。

- 研究（research）モジュール
  - research/factor_research.py
    - 定量ファクター計算の実装（DuckDB を用いた SQL 実行）。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時の None 処理。
    - calc_volatility: ATR20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損は None）。
    - 各関数は target_date を受け DuckDB の prices_daily / raw_financials を参照。

  - research/feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得。horizons の検証あり（1〜252）。
    - calc_ic: スピアマンのランク相関（IC）計算。データ不足（有効レコード < 3）で None。
    - rank, factor_summary: ランク変換（同順位は平均ランク）、各カラムの統計量（count/mean/std/min/max/median）。
    - 外部依存（pandas 等）を使わず標準ライブラリ + DuckDB での実装を意識。

  - research/__init__.py で上記関数群と zscore_normalize をエクスポート。

- ツール群
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
      - コマンド例: python -m kabusys.tools.paper_verification_report
      - オプション: --from / --to（日付フィルタ）、--db（DB パス）。
      - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - 検証指標と閾値:
      - 稼働率 (uptime) >= 99.0%
      - 注文成功率 (fill rate) >= 90.0%
      - 送信率 (send rate) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - system_status / trade_logs / risk_logs 等の集計クエリを用いてレポート出力と PASS/FAIL 判定を行う。
    - 欠損テーブルやデータ不足に対しては N/A を扱うロバスト設計。

- AI ニュース NLP（未完）
  - ai/news_nlp.py
    - raw_news テーブルのニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores テーブルへ書き込む設計を導入。
    - 設計上の特徴:
      - ニュース収集ウィンドウ（JST 前日 15:00 ～ 当日 08:30）を計算する calc_news_window。
      - バッチサイズ、トークン肥大対策（最大記事数・最大文字数）、最大リトライ回数、指数バックオフ等の定数を定義。
      - API キーの解決ロジック（引数または OPENAI_API_KEY 環境変数）。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ、部分置換（DELETE+INSERT で対象コードのみ更新）など、フェイルセーフな設計方針を採用。
    - 注意: ファイル終端が途中で切れており、_fetch_articles 呼び出し以降の処理が未完。実運用前に実装完了と堅牢性確認が必要。

Changed
- なし（初期リリースとして追加のみを記載）。

Fixed
- なし（初期リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用する仕様。キーの取り扱いは注意。

運用上の注意 / マイグレーションガイド
- 環境変数・ファイル
  - .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われるため、プロジェクトを任意のディレクトリで実行する場合は .env の場所に注意してください。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - PAPER_TRADING_SQLITE_PATH を設定すると paper_trading の DB パスを変更可能。paper_trading 実行時は本番の sqlite_path とは完全に分離される設計。

- 実行プロセスと停止
  - run_execution/run_monitoring は data/stop_requested.flag による停止シグナルを監視します。運用側でフラグファイルを設置・削除することで安全に停止できます。
  - run_execution は data/execution.pid を PID 管理に使用（設定は Settings.pid_file_path でも上書き可能）。

- DB と DuckDB
  - 多くの研究・ファクター計算は DuckDB の prices_daily / raw_financials を前提としています。必要なテーブルと列の存在を確認してください。
  - monitoring 用のテーブルは init_monitoring_db によって起動時に冪等的に準備されます。

- 未実装・要確認
  - ai/news_nlp.py はファイル末尾が途切れており、記事フェッチ以降の処理が未実装に見えます（score_news の途中で切断）。OpenAI 統合の本番運用前に実装完了と回帰テストを必須としてください。
  - position_sizing の将来的拡張（銘柄別 lot_size、価格フォールバック等）は TODO コメントで言及あり。実運用で特殊な銘柄を扱う場合は検討が必要。

参考: コマンド例
- 実行エンジン起動（デフォルト動作）
  - python -m kabusys.run_execution
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を秒数で指定して上書き可能（例: MONITOR_POLL_INTERVAL=30）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を直接指定: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

―――

この CHANGELOG はコード内の docstring、定数、ログメッセージ、関数名・引数、TODO コメント等から可能な範囲で推測して作成しています。実際のコミット履歴や issue トラッキングがある場合はそれに基づいて補完・修正することを推奨します。