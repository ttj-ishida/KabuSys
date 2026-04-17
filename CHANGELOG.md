# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。重要度の高い変更点をカテゴリ別にまとめています。コードベースの内容から推測して作成しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期機能群を追加（自動売買システム「KabuSys」）。
  - パッケージバージョンを `0.1.0` として定義（src/kabusys/__init__.py）。
- 設定・環境読み込み（src/kabusys/config.py）
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を基準）。
  - .env/.env.local の自動読み込みを実装。OS 環境変数を保護して上書き制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env パーサーの実装（コメント、export 構文、クォート内のエスケープ等に対応）。
  - 各種設定プロパティを提供（J-Quants, kabu API, LINE, DB パス, 監視しきい値、環境判定等）。
  - PAPER_FILL_MODE の検証（有効値検査）・Paper Trading 用 SQLite パス（PAPER_TRADING_SQLITE_PATH）を追加。
- 実行・監視用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - 環境に応じた DB 選択（paper_trading は専用 DB で完全分離）。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine を起動するワークフローを追加。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にシャットダウンする仕組みを実装。
    - 実行用 PID ファイル (data/execution.pid) をサポート。
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化とポーリングループを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する挙動を明示。
    - 停止フラグ検出でループを終了、例外はログ出力して次回ポーリングへ継続。
- utilities（src/kabusys/utils/process_priority.py）
  - クロスプラットフォームのプロセス優先度設定ユーティリティを追加（Windows / POSIX を吸収）。
  - CPU affinity 設定関数を追加（利用可能なコア数を考慮、例外時は警告でスキップ）。
  - アクセス権限不足等に対する安全なフォールバック（警告ログ）を実装。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分を提供（スコア合計が 0 の場合はフォールバック）。
  - セクター制約・レジーム乗数（risk_adjustment.py）
    - apply_sector_cap: 既存保有を基にセクター集中上限を評価し新規候補を除外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは警告後 1.0 でフォールバック。
  - 株数決定・制約処理（position_sizing.py）
    - risk_based / equal / score の allocation_method に対応した発注株数計算。
    - 単元（lot_size）、手数料等のバッファ（cost_buffer）、max_position_pct・max_utilization に基づく集約上限スケーリングを実装。
    - 利用可能現金を超える場合のスケーリングと端数（lot 単位）処理を安定して行うアルゴリズムを実装。
- 研究モジュール（src/kabusys/research/*）
  - factor_research.py: Momentum / Volatility / Value ファクター計算を実装（DuckDB を用いた SQL ベース）。
    - mom (1m/3m/6m), MA200 乖離, ATR20, 相対 ATR, 平均売買代金 等を計算。
    - データ不足に対する None 処理、ウィンドウのスキャン範囲に余裕を持たせた実装。
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - calc_forward_returns は任意ホライズンに対応（検証・入力検査あり）。
    - calc_ic は ties を考慮したランク変換を用いた Spearman ρ を実装。
  - research パッケージのエクスポートを整備（zscore_normalize などと合わせてエクスポート）。
- ツール（src/kabusys/tools/paper_verification_report.py）
  - Paper Trading の検証レポート生成スクリプトを追加。
    - CLI (--from / --to / --db) を備え、指定期間の system_status / trade_logs / risk_logs を集計してレポートを標準出力へ出力。
    - 閾値: 稼働率、注文成功率、送信率、P95 レイテンシ等の Pass/Fail 判定ロジックを実装。
    - P95 計算、欠損データに対する安全なフォールバックを実装。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込む処理を設計・実装。
  - 処理フロー: 時間ウィンドウ計算、銘柄別記事集約（文字数・記事数の制限）、バッチ送信（最大 20 銘柄）、JSON 応答の厳格検証、スコアクリッピング、部分書換による耐障害性。
  - リトライ（429/ネットワーク/5xx）に対する指数バックオフ、API キー解決（引数または環境変数 OPENAI_API_KEY）を実装。
  - （注）ファイル末尾が途中で切れている箇所があり、fetch_articles 以降の実装は続きがあることが示唆される。

### Changed
- DB 初期化の堅牢化
  - run_execution と run_monitoring の起動時に monitoring テーブルの存在を保証するため init_monitoring_db を呼び出す（冪等に呼べる設計）。
- 設定の整備
  - KABUSYS_ENV の検証を追加し、不正値で ValueError を投げるように（valid: development, paper_trading, live）。
  - LOG_LEVEL の検証を追加。
- run_monitoring
  - MONITOR_POLL_INTERVAL の解析を堅牢化（不正値や 0 以下はデフォルトへフォールバックし、警告ログを出す）。
  - 監視プロセスは常に本番 sqlite_path（settings.sqlite_path）を参照する仕様を明記。
- process_priority ユーティリティ
  - 未対応 OS や権限不足時に警告を出して処理をスキップする挙動に変更（安全性向上）。

### Fixed
- run_execution/run_monitoring のリスク低減
  - 停止フラグ（data/stop_requested.flag）による即時停止検出を追加・強化し、デーモンスレッドの安全な停止・終了処理を実装。
  - time.sleep に 0 以下の値を渡して ValueError が発生するケースを防止（MONITOR_POLL_INTERVAL のバリデーションで対処）。
- position_sizing の集約スケーリング
  - aggregate cap 超過時に小数端数を lot 単位で扱い、残余キャッシュを用いて再配分するロジックを追加して投資額の利用効率を改善。

### Deprecated
- 特になし（初期リリース相当のため破壊的変更は無し）。

### Removed
- 特になし。

### Security
- 環境変数の自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。これによりシステム環境変数が .env によって不意に上書きされるのを防止。

---

## 0.1.0 - 初期リリース（推定）
- 上記の機能群を初期リリースとしてまとめています：
  - 設定管理、実行/監視スクリプト、プロセス優先度ユーティリティ、ポートフォリオ構築（選定・重み付け・ポジションサイズ）、リスク調整、研究モジュール（ファクター計算・解析）、Paper Trading 検証ツール、AI ニューススコアリングの基盤。

注: この CHANGELOG は提示されたソースコードに基づいて推測して作成したものです。リリース日・一部の実装詳細（内部 API の挙動や未提示のモジュール実装）はコードの断片から推測しています。必要であれば、個別ファイルごとの詳細な変更点一覧（関数追加・引数変更など）として補強できます。