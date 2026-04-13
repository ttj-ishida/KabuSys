# Change Log

すべての変更は「Keep a Changelog」形式に従って記載しています。  
この CHANGELOG は提示されたコードベースの内容から推測して作成しています（実際のコミット履歴ではありません）。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- ドキュメント・メタ情報の更新やマイナー修正を予定。

## [0.1.0] - 2026-04-13
初回リリース（コードベースから推測）。

### 追加 (Added)
- アプリケーションコア
  - kabusys パッケージの初期バージョンを追加。パッケージバージョンは __version__ = "0.1.0"。
  - 全体設定管理クラス Settings を実装（環境変数の読み取り、検証を提供）。
  - .env 自動ロード機能を実装（プロジェクトルート検出、.env / .env.local 読み込み、OS 環境変数保護対応）。
  - _parse_env_line による柔軟な .env パース（export プレフィックス、クォート・エスケープ、インラインコメント対応）。

- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV に応じて paper_trading（MockBrokerClient）と本番を分離。paper_trading 時は専用 SQLite（data/paper_trading.db）を使用。
    - DB 初期化（監視テーブルの冪等な保証）、DuckDB 連携、各コンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker_errors 等）を導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を利用）。
    - SQLite / DuckDB のクローズ処理を保証。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位 N 選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: 既存保有を基にセクター別上限（max_sector_pct）を評価し、上限超過セクターの新規候補を除外。
      - 売却予定銘柄を除外してエクスポージャー算出可能。
      - "unknown" セクターは上限適用外として扱う。
    - calc_regime_multiplier: market レジームに応じた投入資金乗数（bull/neutral/bear -> 1.0/0.7/0.3）を提供。未知レジームは 1.0 でフォールバック（警告ログ）。
  - portfolio.position_sizing:
    - calc_position_sizes: 各銘柄の発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
      - lot_size（単元株）丸め、stop_loss_pct に基づく risk_based 計算、per-position 上限や aggregate cap のスケーリングを実装。
      - cost_buffer による手数料/スリッページ見積りの保守的評価を実装。
      - aggregate cap 超過時のスケールダウンと残余キャッシュ利用による端数配分ロジックを実装。

- 研究/リサーチ機能（DuckDB 利用）
  - research.factor_research:
    - calc_momentum: モメンタム指標（mom_1m/mom_3m/mom_6m、MA200乖離）を prices_daily から計算。
    - calc_volatility: ATR20、ATR/price（atr_pct）、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新レコード選択ロジック含む）。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括取得するクエリを実装（horizons 検証あり）。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（結合・None除外・最小件数チェック）。
    - rank / factor_summary: ランク変換、基本統計（count/mean/std/min/max/median）を提供。
  - research.__init__ で主要関数をエクスポート。

- AI / ニュースNLP
  - ai.news_nlp:
    - raw_news / news_symbols を集約し、OpenAI API（gpt-4o-mini、JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）をスコアリングして ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄 / コール）、記事・文字数トリム（最大記事数/文字数制限）対応。
    - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ（上限あり）。
    - レスポンス検証（構造、既知コード、数値型）、スコアを ±1.0 にクリップ。
    - 書き込みは対象コードに限定した置換（DELETE → INSERT）で部分失敗時の既存スコア保護。
    - calc_news_window により JST ベースのニュースウィンドウを UTC naive datetime で計算（前日15:00〜当日08:30 JST 相当）。
    - OpenAI API キー未指定時は例外を投げる仕様。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority: Windows (psutil の priority constants) / POSIX (nice 値) の差を吸収して優先度設定を行う。未対応 OS は警告ログでスキップ。
    - set_cpu_affinity: カレントプロセスを最初の N コアに固定する機能を追加（引数検証・例外ハンドリング、権限エラーは警告でスキップ）。
  - utils.__init__ を追加。

- ツール
  - tools.paper_verification_report:
    - Paper Trading の検証レポート出力 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 日付範囲オプション (--from / --to) と --db オプションをサポート。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ、リスク却下数 などを算出して PASS/FAIL 判定を出力。
    - P95 実装（簡易パーセンタイル）、しきい値はソース内で定義（稼働率 99%、成功率 90% 等）。
    - DB 存在チェックと sqlite3.OperationalError を考慮したフェールセーフ処理を実装。

- モニタリング DB
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。

### 変更 (Changed)
- 設定の動作
  - .env 自動読み込みの優先順位を明確化：OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の上書き動作（override フラグ）と protected（OS 環境変数保護）を導入。

- 監視・実行のデフォルト挙動
  - run_monitoring は常に本番 sqlite_path を参照するよう明記（環境変数に依存しない監視向けの確実性）。
  - run_execution は paper_trading 環境用に DB を分離（paper_sqlite_path を使用）して実運用 DB と完全分離。

### 修正 (Fixed)
- 環境変数読み込みの堅牢化
  - _parse_env_line によるクォート内バックスラッシュのエスケープ処理、コメント解釈の改善により .env の誤パースを軽減。
  - MONITOR_POLL_INTERVAL の不正値（0以下や非整数）を検出してデフォルト値にフォールバックする処理を追加（警告ログ付き）。
- ポートフォリオ関連の数値計算における安全弁とログ出力を整理（価格欠損時のスキップ、スケールダウン時の端数配分の安定化など）。

### 破壊的変更 (Breaking Changes)
- なし（提示コードからは既存 API を壊すような変更は確認できません）。

### 脆弱性 (Security)
- OpenAI API キーは外部に出力せず、api_key 引数または環境変数 OPENAI_API_KEY を参照する仕様。未設定時は明示的にエラーを返す。

---

注記:
- 上記はコード内容を読み取り推測してまとめた CHANGELOG です。実際のリリースノートやコミットメッセージを参照していないため、細部は実際の履歴と異なる可能性があります。詳細な差分やコミット単位の変更履歴が必要な場合は、実際の Git 履歴（git log / git diff）を元に正確な CHANGELOG を生成することを推奨します。