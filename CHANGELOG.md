# Changelog

すべての注記は Keep a Changelog の方針に従い、重要な変更点を分類して記載しています。

履歴
- 0.1.0 - 2026-04-17
  - 初回リリース

## [0.1.0] - 2026-04-17

### 追加 (Added)
- パッケージ初期実装を追加。
  - kabusys パッケージの基本情報（__version__ = 0.1.0）。
- 実行関連スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading モード（MockBrokerClient を使用）を切り替え、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用。
    - エンジンの PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）の検出に基づく安全な終了処理。
    - コンポーネント組み立て: BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine。
    - RiskManager 初期設定値（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10 他）。
    - DuckDB を分析用 DB として接続。
- 監視関連スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視データを書き込む設計（data/monitoring.db がデフォルト）。
    - 停止フラグファイルでループを終了、KeyboardInterrupt 対応。
    - 起動時にプロセス優先度を "high" に設定する呼び出しを行う。
- 設定・環境変数管理
  - config.py
    - Settings クラスを導入し、環境変数から設定を安全に取得するユーティリティを提供。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）を実装。.env.local は .env を上書きする優先度。
    - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DuckDB / SQLite / Paper Trading / 監視閾値 / ログレベル / 環境判定等）。
    - PAPER_FILL_MODE の入力検証（instant|partial|never|reject）。
    - KABUSYS_ENV の妥当性検証（development, paper_trading, live）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア順で選別。
    - calc_equal_weights, calc_score_weights: 等分配およびスコア加重配分（スコア合計が 0 の場合は等分配にフォールバックして警告）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限ロジック。既存保有のセクター割合が上限を超える場合に該当セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（未定義レジームは 1.0 でフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・現金・既存ポジション等から注文株数を決定する主要ロジック。
      - allocation_method として "risk_based" / "equal" / "score" をサポート。
      - lot_size（単元）対応、price の欠損はスキップ。
      - max_position_pct、max_utilization、cost_buffer による per-position / aggregate キャップ、キャッシュ不足時のスケールダウン（端数処理で lot 単位に丸めるロジック）を実装。
- 研究・リサーチ機能
  - research.factor_research
    - calc_momentum, calc_volatility, calc_value: DuckDB 上の prices_daily / raw_financials テーブルからモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - スライディングウィンドウや必要行数チェック（例: MA200 のデータ不足時は None を返す等）。
  - research.feature_exploration
    - calc_forward_returns: 将来リターンを複数ホライズンで一度に計算する汎用関数（horizons の検証あり）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。使用可能レコードが少ない場合は None。
    - rank, factor_summary: ランク付け（同順位は平均ランク）、ファクター基本統計量（count/mean/std/min/max/median）。
  - research パッケージは zscore_normalize をデータ統計ユーティリティとして公開（kabusys.data.stats 依存）。
- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成ツール（CLI）。
    - --from / --to / --db オプションで期間・DB を指定可能。デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ等を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルト閾値: 稼働率 >= 99.0%、注文成功率 >= 90.0%、送信率 >= 95.0%、P95 レイテンシ <= 200 ms。
- AI ニュース NLP（部分実装）
  - ai.news_nlp
    - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む設計を実装。
    - バッチ処理（1 回あたり最大 20 銘柄）、最大記事数・文字数制限（記事最大 10 件、最大 3000 文字/銘柄）を導入。
    - 429/ネットワーク/5xx などに対する指数バックオフ再試行、レスポンスの厳密な JSON 検証、スコアクリッピング（±1.0）を実装予定。
    - ニュース収集ウィンドウの JST→UTC 変換ロジック（前日 15:00 JST ～ 当日 08:30 JST に対応）を実装。
    - （注）ファイル末尾で処理が途中で切れているため一部実装は未完。

### 変更 (Changed)
- 初回リリースのため既存リポジトリからの変更履歴はなし（新規導入）。

### 修正 (Fixed)
- 初回リリースのため既存バグ修正履歴はなし。

### セキュリティ (Security)
- 初版では特にセキュリティ脆弱性に関する注記は無し。ただし OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で提供する設計であり、取り扱いに注意が必要。

## 既知の注意点 / 将来的な改善案（コードから推測）
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、開発環境での誤操作に注意が必要。テスト用の分離が望ましい場合は設定追加を検討。
- position_sizing の price 欠損（0.0）のフォールバックが未実装（TODO コメントあり）。前日終値や取得原価によるフォールバックを検討すると良い。
- ai.news_nlp の処理は部分的に未完（ファイル切断）。API 呼び出し周りの堅牢化や部分失敗時の部分的書き換えロジック（DELETE+INSERT の保護）は設計に組み込まれているが、実装完了とテストが必要。
- .env 自動ロードは便利だが、CI/テスト環境で意図しない環境変数の注入を避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD による明示的無効化を推奨。
- process_priority の設定は psutil の権限制約により失敗する場合があるため、失敗時は警告ログを出してスキップする実装になっている（AccessDenied をハンドリング）。

---

その他の詳細は各モジュールの docstring とコード内コメントを参照してください。