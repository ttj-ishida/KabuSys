# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  
リリースは SemVer に従います。

## [Unreleased]
- 今後の変更予定・作業中の項目をここに記載します。

## [0.1.0] - 2026-04-13

### 追加 (Added)
- 基本パッケージを初期実装・公開
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として設定。

- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - 環境に応じて本番/ペーパー取引用 DB を分離（KABUSYS_ENV=paper_trading 時は PAPER_TRADING_SQLITE_PATH を使用）。  
    - BrokerClientFactory 経由でブローカークライアントを生成。OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine.run_session() を実行。  
    - RiskConfig のデフォルト値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を定義。  
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒、無効な値は警告のうえデフォルトにフォールバック）。  
    - Monitoring 用 DB は環境にかかわらず本番 sqlite_path を使用して接続・初期化。  
    - 起動時にプロセス優先度を "high" に設定。

- コンフィグ/環境変数管理
  - config.Settings クラスを実装し、環境変数をプロパティで取得する API を提供。  
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。  
    - .env の読み込み順序: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による無効化をサポート）。  
    - .env パーサを堅牢化（コメント・クォート・export プレフィックス・エスケープ対応）。  
    - 各種設定プロパティを実装（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH / CPU/MEM/DISK 閾値 / LOG_LEVEL / KABUSYS_ENV 等）。  
    - PAPER_FILL_MODE の検証（instant/partial/never/reject のみ許容）や KABUSYS_ENV 値検証を追加。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート（score 降順、signal_rank タイブレーク）と上位選出。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額配分にフォールバック（WARNING）。

  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックにより候補除外（sell_codes を除外して当日売却予定を考慮）。"unknown" セクターは上限を適用しない。
    - calc_regime_multiplier: market regime に基づく投下資金乗数（bull/neutral/bear をマップし、未知の値は 1.0 にフォールバックして警告）。

  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数決定ロジックを実装。  
      - リスクベース、等金額・スコア加重の両方式をサポート。  
      - lot_size（単元株）、max_position_pct、max_utilization、cost_buffer に基づく aggregate cap スケーリング処理を実装。  
      - スケーリング時には端数処理（lot_size 単位）と残余キャッシュに基づく追加配分ロジックを考慮。

- リサーチ / ファクタ計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算（DuckDB SQL 実装）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせ PER / ROE を計算。

  - research.feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得する汎用実装。
    - calc_ic: スピアマンランク相関に基づく IC（Information Coefficient）計算。
    - rank / factor_summary: ランキングと基本統計量（count/mean/std/min/max/median）を計算。

  - research パッケージエクスポートを整備（zscore_normalize を含む）。

- AI ニュース NLP スコアリング
  - ai.news_nlp:
    - raw_news / news_symbols を集約して OpenAI API (gpt-4o-mini) に対してバッチでセンチメント評価を実行、結果を ai_scores テーブルへ書き込み。  
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 範囲）を計算して記事抽出。  
    - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたりの記事・文字数トリムを実装（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。  
    - エラー対策: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API キー未設定時の ValueError、レスポンスのバリデーション、スコアクリップ（±1.0）。  
    - 部分失敗に備えて、更新は対象コードに限定して DELETE→INSERT を行うことで他コードデータを保護。

- ツール
  - tools.paper_verification_report:
    - Paper Trading 検証レポート生成スクリプトを追加（コマンドライン引数 --from/--to/--db をサポート）。  
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）等を集計。  
    - 判定基準（稼働率・成功率・送信率・P95）を定義し PASS/FAIL を出力。  
    - DB がない／テーブルが存在しない場合の例外処理（sqlite3.OperationalError を捕捉して N/A 表示）を実装。

- ユーティリティ
  - utils.process_priority:
    - set_process_priority(level): Windows と POSIX（Linux/Mac/FreeBSD）それぞれに対応した優先度設定を実装（psutil を使用）。未対応 OS やアクセス拒否時は警告ログでスキップ。  
    - set_cpu_affinity(cpu_count): 指定コア数に対する CPU affinity 設定を追加（無効時は全コア使用・エラー時は警告）。  
    - どちらも例外耐性を持ち、運用環境での安全な呼び出しを想定。

- DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼んで監視テーブルの存在を保証（冪等）。

### 変更 (Changed)
- 既存コードに対する堅牢化・フェイルセーフの追加
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもループ継続するように例外処理を追加（ログを出力して次ポーリングへ）。  
  - MONITOR_POLL_INTERVAL の不正値に対する警告とフォールバック処理を実装。  
  - calc_score_weights: スコア合計が 0 の場合のフォールバック（等金額配分）と警告ログを追加。  
  - calc_regime_multiplier: 未知のレジーム値に対する警告とフォールバック値 1.0 を追加。  
  - .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

- DuckDB / SQLite の利用方針明示
  - research / ai / tools で DuckDB / SQLite を明確に使用。実データアクセスは prices_daily / raw_financials / raw_news 等のテーブルに限定。

### 修正 (Fixed)
- .env パーサの挙動を改善
  - クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱い等の不整合を解消。

- レポート/集計の堅牢性向上
  - paper_verification_report がテーブル未存在時にクラッシュするのを防ぎ、デフォルト値／N/A でレポートを出力するように修正。

- プラットフォーム差分の取り扱い
  - process_priority の各種例外（AccessDenied / AttributeError / NotImplementedError）を捕捉し、起動失敗を回避。

### セキュリティ (Security)
- OpenAI API キーの取り扱いについて、環境変数または明示的引数のいずれかで供給しない場合は ValueError を発生させ、暗黙的に未指定のまま API を呼ばないように実装。

---

注:
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴・意図とは差異がある可能性があります。必要であれば各モジュールの実装箇所や想定ユースケースに基づいて更に細分化した変更履歴を作成します。