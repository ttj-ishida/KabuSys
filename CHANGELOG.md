# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

語彙:
- "追加" = 新機能や新規モジュール
- "変更" = 既存機能の挙動変更（破壊的変更を含む場合は明記）
- "修正" = バグ修正
- "注意" = 現状の既知の制約・将来対応予定（TBD / TODO）

## [0.1.0] - 2026-04-13

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定 / ロード機構 (src/kabusys/config.py)
  - .env ファイル自動読み込みを実装（プロジェクトルートの .git または pyproject.toml を探索）。
  - .env / .env.local の読み込み順序を実装（OS 環境変数を保護する仕組みあり）。
  - 独自の .env パーサーを実装し、クォート、エスケープ、コメント、export 形式に対応。
  - 設定クラス `Settings` を導入し、アプリ全体で利用するプロパティを提供（DB パス、PID/kill ファイルパス、閾値、環境種別など）。
  - 環境変数の妥当性検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。

- 実行系起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine 起動用スクリプトを追加。
  - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - Paper Trading モード（KABUSYS_ENV=paper_trading）の場合は専用の SQLite DB（`PAPER_TRADING_SQLITE_PATH`、デフォルト `data/paper_trading.db`）を使用して本番 DB と分離する挙動を実装。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / Reconciler / RiskManager の組み立てと ExecutionEngine の起動フローを実装。
  - RiskManager に対するデフォルト `RiskConfig`（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を導入。
  - 起動前に監視テーブルの存在を保証するため `init_monitoring_db` を呼び出す（冪等）。

- 監視（モニタリング）起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor ポーリングループ起動スクリプトを追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はフォールバックして警告）。
  - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視データは本番 DB に保存）。
  - 起動時にプロセス優先度を "high" に設定。
  - 例外・KeyboardInterrupt の安全なハンドリングと DB クローズ処理を実装。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/*)
  - 銘柄選定・重み計算 (portfolio_builder.py)
    - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分（スコア合計が 0 の場合は等分配にフォールバック）。
  - セクター制約・レジーム乗数 (risk_adjustment.py)
    - apply_sector_cap: セクター集中の上限チェック（既存保有の時価を考慮、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは警告して 1.0）。
  - 株数決定・資金配分 (position_sizing.py)
    - calc_position_sizes: risk_based / equal / score の配分方式に対応。単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer を用いた保守的見積りを実装。
    - aggregate スケーリング時に残差処理（lot 単位で最も大きい残差順に追加配分）を実装。
  - 上記関数群をパッケージレベルでエクスポート。

- 監視・検証ツール (src/kabusys/tools/paper_verification_report.py)
  - Paper Trading 検証レポート生成用 CLI を追加。
  - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・リスク却下数・レイテンシ（平均/最大/P95）を集計。
  - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
  - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）に対応。DB 存在チェックと例外回避（テーブル未存在時は N/A で処理）。

- 研究系モジュール (src/kabusys/research/*)
  - ファクター計算 (factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、MA200 偏差（200 日データ不足時は None）。
    - calc_volatility: ATR20、ATR 比率、20 日平均売買代金、出来高比率。
    - calc_value: PER, ROE（raw_financials と prices_daily を組合せ）。
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 任意ホライズンの将来リターン取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算（records 結合・None 除外・有効レコード 3 未満は None）。
    - rank / factor_summary: ランク化ユーティリティと基本統計量サマリ。
  - research パッケージレベルで必要関数を再エクスポート。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し、銘柄別のスコアを ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ計算（JST 基準: 前日 15:00 ～ 当日 08:30 → UTC に変換）を実装。
  - 1 銘柄あたり記事数・文字数の上限、バッチサイズ（最大 20 銘柄）などトークン肥大化対策を実装。
  - API エラー（429、タイムアウト、ネットワーク、5xx）に対する指数バックオフリトライ、レスポンス検証、スコアクリッピング（±1.0）等の安全策を実装。
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出。

- プロセス制御ユーティリティ (src/kabusys/utils/process_priority.py)
  - set_process_priority(level) を実装（Windows と POSIX（Linux/Mac/FreeBSD）を吸収）。
  - set_cpu_affinity(cpu_count) を実装（指定が None の場合は何もしない）。
  - 権限不足や未対応 OS 時には警告を出してスキップする安全策を実装。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 注意 / 既知の制約
- ai/news_nlp.py の処理完了後に ai_scores へ書き込むロジックは部分的に記述されており（部分的にコメントや TODO が存在）、一部実装が続く箇所があります。実運用時は完全な書き込み・トランザクション処理の確認を推奨します。
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーが過少見積になる可能性がある旨の TODO コメントあり。将来的には前日終値や取得原価によるフォールバックを検討。
- .env 自動読み込みはプロジェクトルートの検出に依存するため、配布後や環境によっては自動ロードがスキップされる場合があります。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- set_process_priority / set_cpu_affinity は権限要件があり一般ユーザーでは失敗する可能性があります。失敗時は警告ログを出して処理を継続します。

### 将来の改善予定（言及）
- portfolio の lot_size を銘柄毎に持てるよう stocks マスタ導入を検討（現在は全銘柄共通の lot_size）。
- ai/news_nlp のレスポンス処理と DB 置換ロジックの堅牢化（部分失敗時の保護やトランザクション）。
- monitoring / execution の起動オプション（デーモン化やサブプロセス制御）の拡張。

---

注: 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートには追加の詳細（リリース日、互換性情報、マイグレーション手順など）を含めることを推奨します。