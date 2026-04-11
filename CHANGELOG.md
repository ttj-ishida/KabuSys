# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルは、コードベースから推測可能な追加機能・設計方針・重要な挙動（デフォルト値、フォールバック、環境変数等）をまとめたものです。

## [Unreleased]

## [0.1.0] - 2026-04-11

### Added
- 初回公開: KabuSys のコア機能群を実装
  - 全体
    - パッケージ metadata: __version__ = "0.1.0"
    - Settings クラスによる環境変数/設定管理モジュールを実装。.env / .env.local の自動読み込み機能（プロジェクトルート探索）を提供し、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env パーサーの実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理などに対応。
    - 環境変数の保護（OS 環境変数を protected として上書き抑止）をサポート。
    - Settings による各種設定プロパティ:
      - J-Quants / kabu API / LINE トークン類の取得
      - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - Paper Trading の挙動（PAPER_FILL_MODE）と検証（有効値制約）
      - 監視関連（PID ファイル、kill flag、閾値）
      - 環境種別検証（KABUSYS_ENV: development / paper_trading / live）
      - ログレベル検証（LOG_LEVEL）
  - 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを実装。
      - 起動時にプロセス優先度を high に設定（best-effort）。
      - Paper Trading 環境（KABUSYS_ENV=paper_trading）の場合は settings.paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
      - DuckDB と SQLite 接続の初期化、監視テーブルの冪等初期化を実施。
      - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
      - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を構成し、initial_portfolio_value を broker.get_available_cash() で初期化。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。0 以下や不正な値は警告を出してデフォルトにフォールバック。
      - Monitoring は環境（KABUSYS_ENV）に関わらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を high に設定（best-effort）。
  - utils
    - process_priority モジュールを実装:
      - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）を吸収して優先度（high/normal/low）を設定。権限不足等は警告ログでスキップ。
      - set_cpu_affinity(cpu_count): 最初の N コアにピン留めするユーティリティ。引数検証と権限エラーをハンドリング。
  - portfolio（ポートフォリオ構築）
    - portfolio_builder:
      - select_candidates: BUY シグナルを score 降順、同点は signal_rank 昇順でソートして上位 N を選択。
      - calc_equal_weights: 等金額配分を計算。
      - calc_score_weights: スコア加重配分を計算。全銘柄スコア合計が 0 の場合は等金額配分へフォールバック（WARNING ログ）。
    - risk_adjustment:
      - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: レジームに応じた投下資金乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
    - position_sizing:
      - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく株数決定を実装。lot_size（単元）で丸め、per-position と aggregate の上限（max_position_pct / max_utilization）を適用。cost_buffer を考慮した投資合計のスケーリング、端数処理のための fractional remainder による追加配分ロジックを実装。
  - research（因子 / 解析）
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB のウィンドウ関数で計算。データ不足時は None を返す。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。欠損や行数不足に対する扱いを明確化。
      - calc_value: raw_financials から target_date 以前の最新財務を取得し PER/ROE を計算（EPS が 0/NULL の場合は PER を None）。
    - feature_exploration:
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。horizons の検証（正の整数かつ <= 252）を実施。
      - calc_ic: スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）や分散 0 の場合は None。
      - rank, factor_summary: 同順位の平均ランク処理、各カラムの count/mean/std/min/max/median を計算。
  - ai（LLM を用いた機能）
    - news_nlp:
      - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ設計（JST ベースで前日 15:00 〜 当日 08:30、内部は UTC naive datetime）を提供（calc_news_window）。
      - バッチ処理: 最大 20 銘柄/チャンク、1 銘柄あたり最大記事数・文字数制限でプロンプト肥大化を抑制。
      - API リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ、その他のエラーはスキップ。
      - レスポンス検証: JSON 抽出、results の構造検証、未知コードの無視、スコアの数値検証、±1.0 にクリップ。
      - DB 書き込みは部分失敗耐性を意識し、「対象コードのみ DELETE → INSERT」を行う（DuckDB の executemany 空リスト制約に配慮）。
      - テスト用フック: _call_openai_api をモック差し替え可能。
    - regime_detector:
      - ETF (1321) の MA200 乖離（_calc_ma200_ratio）と、raw_news のマクロキーワードに基づく LLM 評価（macro_sentiment）を重み合成して市場レジーム（'bull' / 'neutral' / 'bear'）を日次判定する処理を実装。
      - ルックアヘッド防止: prices_daily のクエリは target_date 未満のデータのみ使用。
      - LLM 呼び出し失敗時は macro_sentiment = 0.0（中立）で継続するフェイルセーフを採用。
      - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を行う設計。

### Changed
- N/A（初回リリースのため「追加」中心の記載）

### Fixed
- N/A（ソースからは明示的なバグフィックス履歴は検出できず、堅牢化・フォールバック実装として箇所を設計段階で補完）

### Notes / Implementation details / 動作上の重要な挙動
- 環境変数ロード
  - 自動ロード順: OS 環境 > .env.local > .env。OS 環境は protected として .env/.env.local による上書きを防止。
  - .env のパースは export プレフィックス、クォート内のエスケープ、インラインコメントの扱いをサポート。
- DB の使い分け
  - monitoring 関連は環境に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用。
  - run_execution は paper_trading 環境時に settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
- OpenAI / 外部 API の耐障害性
  - 一部の LLM 呼び出しでリトライ・バックオフ・フェイルセーフ（デフォルト値にフォールバックして処理継続）を採用し、API 障害時に処理全体を停止しない設計。
- データ不足時のフォールバック
  - ファクター/MA/ATR 等の計算で十分な履歴がない場合は None（または中立値 1.0 など）を返し、上位処理で適切に扱えるようにしている。
- ロギング
  - 多くの関数で警告/デバッグ/情報ログを出力するようにしており、運用時のトラブルシュートを想定。

### For developers / 備考
- unittest 等で LLM 呼び出しをテスト可能にするため、news_nlp._call_openai_api を unittest.mock.patch で差し替えられるよう設計されている。
- DuckDB クエリはウィンドウ関数を多用しており、大量データに対するスキャン範囲を限定する工夫（カレンダーバッファ）をしているため、パフォーマンスを保ちやすい設計。

---

この CHANGELOG は、提示されたソースコードの実装内容と docstring / 実装上の挙動から推測して作成しています。実際のリリースノート作成時には、コミット履歴や PR の説明に基づいて追加修正・追記してください。