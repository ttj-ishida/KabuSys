CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

Unreleased
----------

- （現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-13
--------------------

Added
- 初回リリース (v0.1.0) — KabuSys のコア機能群を実装。
  - 基本情報
    - パッケージバージョンを __version__ = "0.1.0" として設定。
    - プロジェクト全体で SQLite (監視用) と DuckDB (時系列/分析用) を併用する設計を採用。
  - 起動スクリプト
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを実装。
      - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き対応（デフォルト 60 秒）。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する仕様。
      - プロセス優先度を set_process_priority("high") で設定して起動。
    - run_execution.py
      - ExecutionEngine 起動スクリプトを実装。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB（data/paper_trading.db をデフォルト）と MockBrokerClient（BrokerClientFactory 経由）を使用し、本番 DB と分離。
      - Engine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立てて実行。
      - RiskManager に対するデフォルト設定値を明示（max_position_pct 等）。
  - 設定・環境読み込み
    - config.py
      - .env/.env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
      - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env パーサは export 句、クォート、エスケープ、インラインコメントなどに対応。
      - Settings クラスを実装し、主要な環境変数をプロパティ経由で取得（各種検証・デフォルト値・型変換を行う）。
      - PAPER_FILL_MODE の入力検証、KABUSYS_ENV / LOG_LEVEL の許容値チェックを実装。
  - モニタリング DB 初期化
    - monitoring.monitoring_db:init_monitoring_db を初期化に利用（起動時に監視テーブル存在を保証）。
  - ユーティリティ
    - utils/process_priority.py
      - Windows / POSIX(Linux/Mac/FreeBSD) に対応したプロセス優先度設定（set_process_priority）。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
      - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。
  - ポートフォリオ構築
    - portfolio/portfolio_builder.py
      - 銘柄選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
      - 同点時のタイブレークロジック（score 降順、signal_rank 昇順）。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
      - apply_sector_cap は既存保有のセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
      - calc_regime_multiplier は "bull"/"neutral"/"bear" をマップ、未知値は警告の上でフォールバック 1.0。
    - portfolio/position_sizing.py
      - position sizing ロジック（risk_based / equal / score）を実装。
      - 単元株（lot_size）で丸め、per-position 上限や aggregate cap を考慮してスケールダウンするアルゴリズムを導入。
      - cost_buffer により手数料・スリッページ分を保守的に見積もる。
      - aggregate スケール後の端数処理で残余キャッシュを活用する公平な再配分ロジックを実装。
  - リサーチ・ファクター
    - research/factor_research.py
      - momentum / volatility / value の各ファクター計算を DuckDB 上の prices_daily / raw_financials を参照して実装。
      - MA200 や ATR、各種リターン等を SQL ウィンドウ関数で効率的に算出。データ不足時は None を返す安全設計。
    - research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計要約（factor_summary）、ランク関数（rank）を実装。
      - 外部ライブラリに依存せず純 Python 実装（標準ライブラリのみ）。
    - research/__init__.py で主要 API を公開。
  - AI ニュース NLP
    - ai/news_nlp.py
      - raw_news を OpenAI API (gpt-4o-mini) に送信して銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウの計算（前日 15:00 JST 〜 当日 08:30 JST 相当）や銘柄ごとの記事集約、1銘柄あたりの文字数制限、チャンク（最大 20 銘柄）単位での API 呼び出し、リトライ（指数バックオフ）、結果検証、スコアクリップなどを実装。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading 用の検証レポート生成 CLI を実装。--from/--to/--db オプションに対応。
      - system_status / trade_logs / risk_logs などの集計を行い、稼働率・注文成功率・送信率・P95 レイテンシ等を表示および PASS/FAIL 判定（閾値はソース内で定義）。
      - DB が存在しない場合のエラーメッセージ出力や、DuckDB/SQLite の OperationalError を読み替える堅牢性を実装。
  - その他
    - 細かなログ出力やデバッグ情報を各モジュールに追加。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Known issues / Notes
- config._find_project_root は .git / pyproject.toml を基準にプロジェクトルートを探索するため、配布後の環境では自動ロードがスキップされる可能性がある点に注意。
- position_sizing の apply_sector_cap 内で price が欠損（0.0）だとエクスポージャーの過少見積につながる旨の TODO コメントあり（将来的な価格フォールバックの検討が必要）。
- process priority / cpu affinity の設定は権限や OS に依存し、失敗時は警告を出してスキップする挙動。
- ai/news_nlp の実装は API 呼び出しや結果整形の堅牢化を目指しているが、部分失敗時の部分的な書き込み保護やレスポンス検証の詳細は運用時に追加のテスト推奨。

ライセンス、セキュリティ
- セキュリティ関連の記載は今回のコードからは特別な修正はありません。API キー等の機密情報は環境変数で管理する設計になっています。

（注）上記は提供されたコードの内容から推測してまとめた CHANGELOG です。実際のリリースノートにはリリース日・作者・既知のバグ修正などをプロジェクト運用方針に合わせて追記してください。