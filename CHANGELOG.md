CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

Unreleased
---------

- なし（現時点で未リリースの作業は特に記載無し）

0.1.0 - 2026-04-12
------------------

初回リリース。プロジェクト「KabuSys」のコア機能を実装しました。以下はコードベースから推測できる主要な追加・仕様です。

Added
- パッケージ初版を公開
  - バージョン: 0.1.0（src/kabusys/__init__.py）
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite / DuckDB 接続、ブラウザクライアントのファクトリ利用、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine.run_session の起動処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、プロセス優先度設定、監視 DB 初期化を行う。監視は環境（KABUSYS_ENV）に依らず本番 sqlite_path を使用する仕様。
- 設定管理
  - config.py: 環境変数/.env 自動読み込み機能（プロジェクトルート判定：.git または pyproject.toml を探索）。.env/.env.local の読み込み順・上書き挙動、保護された OS 環境変数の扱いを実装。export 形式、クォート、インラインコメント等に対応する .env パーサーを実装。多数の設定プロパティ（データベースパス、Paper Trading 関連設定、監視閾値、ロギングレベル等）と入力バリデーションを提供。
- ポートフォリオ構築ライブラリ
  - portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合に等配分へフォールバックする警告ロジックあり。
  - position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）および残差処理（lot 単位での再配分）を実装。手数料・スリッページ用の cost_buffer を考慮。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームや unknown セクターに対するフォールバック動作を定義。
- リサーチ / ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value のファクター計算を DuckDB を使った SQL + Python で実装（各ファクターのウィンドウ要件・欠損処理を厳密に取り扱い）。
  - research/feature_exploration.py: 将来リターン計算、IC（Spearman ランク相関）計算、ランク付けユーティリティ、ファクターの統計サマリを実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research/__init__.py: 主要なユーティリティを公開（zscore_normalize など）。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む機能を追加。処理の特徴：
    - ニュース時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算。
    - 銘柄ごとに記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大バッチサイズでチャンク処理（_BATCH_SIZE=20）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（最大 _MAX_RETRIES）。
    - 応答 JSON のバリデーション、スコアの ±1.0 クリップ、部分的失敗時の既存スコア保護（更新対象コードに限定して DELETE→INSERT）をサポート。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - ルックアヘッドバイアス防止のため内部で datetime.today()/date.today() を参照しない設計。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティ（set_process_priority）。Windows (psutil の priority constants) と POSIX の nice 値をハンドリング。アクセス権限不足時は警告でスキップ。CPU affinity を固定する set_cpu_affinity も追加。
- 監視・モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照される形）を init_monitoring_db で呼び出し、監視テーブルの冪等初期化を run スクリプトから保証。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。稼働率・注文成功率・送信率・レイテンシ（P95）等を集計して PASS/FAIL 判定を行う。CLI オプションで期間指定（--from/--to）と DB パス指定（--db）に対応。欠損・テーブル未存在時に堅牢にデグレード（N/A 表示）する実装。
- DuckDB / SQLite を併用するデータアクセス
  - DuckDB は履歴データやリサーチ用途、SQLite は監視/注文ログ等の永続化に利用する設計。

Changed
- なし（初回リリースに伴う追加実装が中心）

Fixed
- 複数モジュールで欠損データやテーブル非存在時の安全な取り扱いを実装
  - ファクター計算 / レポート / レイテンシ算出などで NULL / データ不足時に None を返す、または N/A 表示にフォールバックする処理を追加。
- position_sizing のスケールダウンロジックで端数処理と再配分を明確化。lot_size での丸め、上限チェックを厳密化。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーの扱いは明示的に引数または環境変数で取得し、未設定時はエラーを出す仕様。API 呼び出しはリトライとフェイルセーフ（失敗時はスキップ）を備えており、部分失敗時に他銘柄のスコアを保持するための更新戦略を採用。

Notes / 環境変数一覧（主なもの）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- SQLITE_PATH, DUCKDB_PATH: データベースファイルパス
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（分離運用）
- PAPER_FILL_MODE: Paper Trading の fill 動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- OPENAI_API_KEY: OpenAI API キー
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連パス
- LOG_LEVEL, CPU/MEM/DISK 閾値など

既知の設計上の注意点（コードからの推測）
- run_monitoring は「監視」は環境にかかわらず本番 sqlite_path を使う設計であるため、development / paper_trading の際も監視 DB の扱いに注意が必要。
- position_sizing の価格欠損時（price が 0.0）にエクスポージャーが過小見積りされる可能性があり、将来的に前日終値等のフォールバックが検討されている（TODO コメントあり）。
- .env 自動ロードはプロジェクトルート検出が失敗するとスキップされるため、配布パッケージ環境では明示的に環境変数を設定することが推奨される。

---

この CHANGELOG はリポジトリの現在のコード構成から推測して作成しています。リリース日や詳細は実際のリリース手順に合わせて更新してください。