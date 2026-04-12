CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。  
日付はコードベースの現状（この CHANGELOG 作成時点）を反映しています。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-12
--------------------

Added
- パッケージ初期実装を追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。
- 実行エントリ / デーモン系スクリプトを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は環境（KABUSYS_ENV）に関わらず本番の sqlite_path を使用して DB を開く。
    - プロセス優先度を起動直後に High に設定（utils.process_priority.set_process_priority を利用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - `KABUSYS_ENV=paper_trading` 時は paper_trading 専用の SQLite DB（デフォルト: data/paper_trading.db）と MockBrokerClient を使用し、本番 DB と分離。
    - ExecutionEngine の組み立て（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、duckdb 接続など）を行いセッションを実行。
    - 起動時にプロセス優先度を High に設定。

- 設定・環境変数管理を実装。
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの .env / .env.local、OS 環境変数を保護）。
    - .env パース機能（コメント, export キーワード, シングル/ダブルクォートとバックスラッシュエスケープ対応）。
    - 必須環境変数取得ヘルパ `_require`。
    - Settings クラスを提供し、各種設定プロパティを公開（J-Quants / kabuAPI / LINE / DuckDB / SQLite / Paper Trading / 監視閾値 / PID ファイル / 環境判定等）。
    - `KABUSYS_ENV`, `LOG_LEVEL`, `PAPER_FILL_MODE` 等の値検証ロジックを実装。

- 監視・モニタリング基盤を実装。
  - monitoring_db 初期化呼び出し（init_monitoring_db を run_* スクリプトで呼ぶことで監視テーブルの存在を保証）。
  - SystemMonitor を使った単一実行 check_once ループ。

- Paper Trading 検証ツールを追加。
  - tools/paper_verification_report.py
    - コマンドラインツール: 指定期間の Paper Trading DB を集計して検証レポートを出力。
    - 指標: 稼働率（uptime %）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（avg/max/P95）など。
    - デフォルト閾値と Pass/Fail 判定基準を定義（稼働率 99.0%、fill 90.0%、send 95.0%、P95 latency 200 ms）。
    - DB 存在チェック / SQLite の SQL 実行時の OperationalError 耐性（テーブル不足時は N/A を出力）。
    - コマンドライン引数で期間・DB パス指定可能。

- ポートフォリオ構築・ポジションサイジング機能を追加（純粋関数群）。
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア降順・同点は signal_rank でブレーク）。
    - 重み算出: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコア 0 の場合は等分にフォールバックと警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限判定と候補フィルタ（既存保有のセクターエクスポージャー計算、sell_codes を考慮）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（フォールバックロジックと警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の割当方法に対応（risk_based / equal / score）、単元株（lot_size）での丸め、per-position と aggregate の上限、cost_buffer（手数料・スリッページ見積）を考慮したスケーリング、残差分の lot 単位での再配分ロジックを実装。
    - リスクベースの株数計算（許容リスク率、損切り率を使用）を実装。

- 研究（Research）用モジュールを追加（ファクター計算・特徴解析）。
  - research/factor_research.py
    - モメンタム: calc_momentum（1M/3M/6M リターン、MA200乖離、欠測データ処理）。
    - ボラティリティ/流動性: calc_volatility（ATR20、相対ATR、平均売買代金、出来高比率）。
    - バリュー: calc_value（raw_financials から最新財務を取り、PER/ROE を計算）。
    - 各関数は DuckDB 接続を受け、prices_daily / raw_financials を参照して結果を返す設計。
  - research/feature_exploration.py
    - 将来リターン calc_forward_returns（可変ホライズン、入力バリデーション、単一クエリで取得）。
    - IC（Information Coefficient） calc_ic（スピアマンのランク相関、必要件数の検証）。
    - ファクター統計 summary: factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク）。
  - research/__init__.py に主要関数をエクスポート。

- AI ニュース NLP スコアリングを実装（OpenAI 経由）。
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI にバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むワークフローを実装。
    - 設計上の特徴:
      - ニュース対象ウィンドウを JST ベースで計算（前日 15:00 〜 当日 08:30 JST を UTC に変換）。
      - 1 リクエストあたり最大 20 銘柄のバッチ処理、1 銘柄あたりの記事件数と文字数に上限（記事数上限/文字数上限でトリム）。
      - 再試行ポリシー（429/タイムアウト/5xx に対する指数バックオフ、上限回数）。
      - レスポンス検証とスコアの ±1.0 クリップ。
      - 部分失敗時に既存スコアを保護するため該当コードのみ DELETE→INSERT で差分更新（atomic な全体置換を避ける）。
      - OpenAI API キー未設定時は ValueError を送出。

- ユーティリティ関数群を追加。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定 set_process_priority（Windows / POSIX を吸収）。
    - CPU アフィニティ固定 set_cpu_affinity（最初 N コアに固定、引数検証、権限不足例外を警告扱いでスキップ）。
    - 権限不足や未対応 OS の場合は警告ログでスキップする堅牢設計。

Changed
- （初期リリースのため特記事項なし）

Fixed
- （初期リリースのため特記事項なし）

Security
- OpenAI API を使用する処理（ai/news_nlp.score_news）は API キーの未設定で早期にエラーを出すことで不正な呼び出しを防止（ValueError）。

Notes / Known limitations
- 一部の関数は外部リソース（prices_daily, raw_financials, monitoring DB 等）の存在を前提とするため、テーブル未作成時は CLI ツールが N/A を表示したり単純に 0 を返す設計になっている（運用時は初期化が必要）。
- position_sizing の lot_size は現状固定（将来は銘柄別 lot_map 対応予定）。
- apply_sector_cap の既存保有エクスポージャー計算は price_map が欠損（0.0）だと過少見積りになる可能性があり、将来的にフォールバック価格の導入を検討。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされる。自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

以上。必要であれば、各項目をファイル単位でより細かく分けた CHANGELOG や、今後の開発予定（Roadmap）を追加作成します。どの粒度での記載を希望しますか？