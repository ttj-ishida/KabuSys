# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現時点の変更はありません）

## [0.1.0] - 2026-04-13

初回リリース。以下の主要機能・ユーティリティを追加しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
- 環境設定 / 設定読み込み（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - OS 環境変数を保護するための読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env ファイルの柔軟なパース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等をサポート）。
  - 各種設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック
    - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH のデフォルトパス
    - PAPER_FILL_MODE（paper_trading 用のモック約定モード。instant/partial/never/reject をサポート）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等の監視周り設定
    - CPU/MEM/DISK の閾値設定（CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 等の検証付き取得
- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッション実行。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続を使用（duckdb_path）。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や整数以外）はデフォルトにフォールバックして警告を出力。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。
- 監視 DB 初期化ユーティリティ
  - monitoring_db 初期化呼び出しを run 系スクリプトで実行（冪等に監視テーブルを保証）。
- プロセス優先度 / CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加。Windows / POSIX（Linux, macOS, FreeBSD）に対応し、適切な nice 値や Windows 優先度定数を設定。未対応 OS や権限不足時は警告を出力して安全にスキップ。
  - set_cpu_affinity(cpu_count) を追加。指定コア数にプロセスをピンニング（権限不足や未サポート環境では警告してスキップ）。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順・タイブレークにより上位 N 件を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックして WARNING）
  - risk_adjustment
    - apply_sector_cap: 既存保有を元にセクター集中上限をチェックし、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知レジームは 1.0 でフォールバック）
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出。損切り率、risk_pct、max_position_pct、max_utilization、lot_size、cost_buffer（手数料・スリッページ見積）等を考慮したアルゴリズムを実装。aggregate cap 超過時のスケールダウンと lot_size 単位での再配分ロジックを備える。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（prices_daily を DuckDB で参照）
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算
  - feature_exploration
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを計算（複数 horizon を一度に処理）
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）
    - factor_summary / rank: 基本統計量・ランク付けユーティリティ
  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats 経由）を含める
- AI / ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いたニュースセンチメントスコアリング機能を追加
    - ターゲット窓: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive で計算）
    - raw_news / news_symbols を銘柄ごとに集約（記事数と文字数に上限を設ける: _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
    - バッチ送信（1 API コール当たり最大 20 銘柄、gpt-4o-mini を指定）、JSON Mode による厳密な JSON 出力を期待
    - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（上限あり）
    - レスポンス検証、スコアクリッピング（±1.0）、ai_scores テーブルへの安全な置換（部分失敗時も他銘柄の既存スコアを保護）
    - OPENAI_API_KEY が未設定の場合は ValueError を送出
- ツール（kabusys.tools）
  - paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI ツールを追加
    - オプション: --from / --to（日付フィルタ）, --db（DB パス）
    - 指標:
      - システム稼働率（system_status）
      - 注文成功率 / 送信率（trade_logs）
      - リスク却下数（risk_logs）
      - レイテンシ（avg / max / P95）
    - Pass/Fail 基準を定義（稼働率 >= 99.0%, 成功率 >= 90%, 送信率 >= 95%, P95 <= 200 ms）
    - 空データやテーブル未存在時は安全に N/A を表示し続行

### Changed
- デフォルト動作・安全策
  - run_monitoring は監視データを書き込む DB として常に settings.sqlite_path（本番）を使用する設計に明示的に合わせた。
  - run_execution は paper_trading 環境のときに paper_sqlite_path を使って本番データと分離するよう設計。
  - .env の読み込みで OS 側の環境変数を保護するため、既存の OS 環境キーは上書きされない（ただし .env.local は override=True で読み込めるが protected により OS 環境は守られる）。
  - process_priority の実装は権限不足や未サポート OS の場合に例外を投げず警告ログで済ませる安全設計。

### Fixed / Robustness
- 環境値の検証とフォールバック
  - MONITOR_POLL_INTERVAL の不正値に対して警告しデフォルトにフォールバック（time.sleep に渡せない非正の値を処理）。
  - PAPER_FILL_MODE の不正値チェックと明確なエラーメッセージ。
  - KABUSYS_ENV / LOG_LEVEL などの検証を実装し、不正な値で早期にエラーを出すことで誤設定による潜在的な誤動作を低減。
- DB クエリ・集計の堅牢化
  - paper_verification_report の各クエリはテーブル未存在や OperationalError を捕捉して N/A を返すようにしているため、部分的に未データでもレポート生成を継続可能。
  - research / factor 計算はデータ不足時に None を返す、ウィンドウサイズチェックを行うなど安全化。

### Notes / その他
- DuckDB と SQLite の両方を利用する設計（DuckDB はリサーチ/ファクター計算、SQLite は監視や取引ログ等の永続化を想定）。
- 現状一部の TODO コメント（例: position_sizing の銘柄別 lot_size 対応、apply_sector_cap の price フォールバック等）が残っており、将来の改善ポイントとして残しています。
- OpenAI integration はキー管理と API 利用制限に注意して運用してください（API キーは OPENAI_API_KEY または score_news の api_key 引数で指定）。

---

今後のリリースではテスト整備、ドキュメント強化（API 仕様、設定例、運用手順）、および監視・再起動ロジックの追加などを予定しています。