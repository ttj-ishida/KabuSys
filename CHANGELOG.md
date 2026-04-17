CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリース日: 2026-04-17

0.1.0 - 2026-04-17
------------------

Added
- 初期リリースを追加（パッケージバージョン: 0.1.0）。
- 実行系 / 監視系起動スクリプトを追加
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用の専用 SQLite DB(data/paper_trading.db 既定)を利用するよう分離。
    - 停止フラグ(data/stop_requested.flag) と PID 管理(data/execution.pid) による安全な起動/停止制御を実装。
    - 実行エンジンは別スレッドで稼働し、停止フラグを監視して graceful stop を実行。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用する設計（重要な動作）。
    - 停止フラグによるループ終了、例外発生時もログ出力して次ポーリングへ継続。

- 設定/環境変数管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み実装（プロジェクトルート判定は .git または pyproject.toml）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
    - .env パーサの強化: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理に対応。
    - Settings クラスを導入し、主要設定（DB パス、API トークン、Paper Trading 用オプション、監視閾値等）をプロパティとして提供。
    - 必須変数取得ヘルパー _require()（未設定時は ValueError を送出）。
    - 新たに使用する/期待する環境変数の例:
      - JQUANTS_REFRESH_TOKEN（必須）、KABU_API_PASSWORD（必須）
      - DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE
      - PID_FILE_PATH、KILL_FLAG_PATH、KILL_FLAG_CLEAR_ON_START
      - CPU/MEM/DISK 閾値（CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT）
      - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL

- Portfolio 関連の純粋関数群（DB 非依存、メモリ内計算）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補抽出（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重配分。全スコアが 0 の場合は警告と等配分へフォールバック。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用（unknown セクターは上限除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知値は 1.0 でフォールバックし警告）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 発注株数の算出ロジック（risk_based / equal / score）。
    - lot_size（単元）に基づく丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer による保守的コスト見積りをサポート。
    - aggregate スケーリング後に端数 (lot 単位) の再配分ロジックを実装（残余資金で分配）。

- Research / 統計解析機能（DuckDB ベース、外部 API 非依存）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（必要データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、平均売買代金、出来高比等を算出（欠損制御あり）。
    - calc_value: raw_financials から最新の財務情報を取得し PER / ROE を計算。
    - DuckDB を用いたウィンドウ関数による実装で大量データでも効率的に計算。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン先までの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。利用可能レコード < 3 の場合は None を返す。
    - rank: 同順位は平均ランクで処理（丸めで ties 判定の安定化）。
    - factor_summary: count / mean / std / min / max / median を計算。

- AI / ニュース NLP
  - src/kabusys/ai/news_nlp.py（ニューススコアリング機能を提供）
    - calc_news_window: スコア対象のニュース時間ウィンドウ計算（JST ベース → UTC に変換）。
    - score_news: raw_news / news_symbols を集約し OpenAI API へバッチ送信して銘柄別 ai_score を ai_scores テーブルへ書き込むワークフローを実装（バッチサイズ、文字数上限、記事数上限、スコアクリップ、リトライ等の保護機構あり）。
    - OpenAI API へのキーは引数または環境変数 OPENAI_API_KEY を使用。不在時は ValueError。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数的バックオフでリトライ。
    - 部分失敗時も既存スコアを保護するよう、更新対象コードのみ DELETE → INSERT を行う設計。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度 (high/normal/low) の設定を提供。権限不足や未対応 OS の場合は警告で安全にスキップ。
    - set_cpu_affinity(cpu_count): 現プロセスを先頭 N コアにピン留め（無指定は全コア）。引数検証あり。
    - 起動スクリプト（run_monitoring/run_execution）は起動直後に set_process_priority("high") を呼ぶように統一。
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 向け検証レポート生成ツールを追加（CLI）。
    - 検証指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシ。
    - デフォルト閾値を定義し、PASS/FAIL 判定を標準出力で出力。SQLite DB パスは --db または PAPER_TRADING_SQLITE_PATH。

Changed
- パッケージ構成を初期化
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ に列挙。

Fixed
- （初期リリースのため既知の実装上の注意点を明記）
  - .env ファイルの読み込みで OS 環境変数が保護されるよう protected 機構を導入（.env.local の override 時も OS 環境を上書きしない）。
  - DuckDB への executemany 実行前にパラメータが空でないことを想定した設計（ニューススコア更新時の部分失敗保護）。

Notes / Migration
- 重要な挙動メモ
  - run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番監視 DB）を使用します。開発や paper_trading 環境で監視を分離したい場合は sqlite_path を別途指定してください。
  - run_execution は paper_trading 環境で settings.paper_sqlite_path を使い本番 DB から分離します。
  - MONITOR_POLL_INTERVAL: 0 以下や不正な値は警告ログを出し既定値 (60 秒) にフォールバックします。
  - PAPER_FILL_MODE: 有効値は "instant" | "partial" | "never" | "reject"。不正値は ValueError。
  - 必須環境変数(JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD) が未設定だと例外が発生します。.env.example を参照して設定してください。
  - OpenAI を使う機能は OPENAI_API_KEY の設定が必要です。

Security
- 現在の変更点に関する直接的なセキュリティ修正はありません。API キー等の機密情報は環境変数で管理する想定です。.env の取り扱いに注意してください（リポジトリにコミットしない等）。

Acknowledgements / Other
- DuckDB を活用したオンメモリかつ高速な分析クエリにより、ファクター計算・研究機能を効率的に実装しています。
- 本リリースは初期実装です。今後テストカバレッジの拡充、エラーハンドリングの強化、ログ/メトリクスの詳細化を予定しています。

もし特定ファイルの変更点や、リリースノートへ追記したい詳細（例: 重要な設計判断、既知の制約、既存ユーザー向けの移行手順）があれば教えてください。追加で反映します。