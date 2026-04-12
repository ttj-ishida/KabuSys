Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

Unreleased
----------

（なし）

[0.1.0] - 2026-04-12
-------------------

Added
- 初回リリース — KabuSys (v0.1.0)
  - パッケージ全体のエントリポイントと基本モジュールを追加。
  - バージョン: __version__ = "0.1.0"

- 実行 / 監視用スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じた DB 分離:
      - 本番: 通常の sqlite_path を使用。
      - paper_trading: settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、MockBrokerClient により本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority）。
    - duckdb 接続を利用してリサーチ等と連携。
    - RiskManager / OrderManager / Reconciler 等の組み立てを行い engine.run_session() を実行。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - デフォルトポーリング間隔は 60 秒。MONITOR_POLL_INTERVAL 環境変数で上書き可能（不正値はデフォルトにフォールバックし警告ログを出力）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する（監視データは共有する設計）。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出 .git / pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサ: export 形式、クォート内のエスケープ、インラインコメントの取り扱い等に対応。
    - Settings クラスで各種環境設定をプロパティとして提供:
      - DB パス: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
      - PID/KILL フラグパス、しきい値 (CPU/MEM/DISK)
      - PAPER_FILL_MODE の検証（instant/partial/never/reject）
      - ログレベル、環境 (development/paper_trading/live) の検証
      - jquants/kabu/LINE 等の API トークン取得（必須チェックは _require で実装）

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選定、同点は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を考慮したセクター集中上限フィルタ（"unknown" セクターは検査対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数 (bull=1.0, neutral=0.7, bear=0.3)。未知レジームは 1.0 にフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数配分方式に対応（risk_based / equal / score）。
      - lot_size による丸め、max_position_pct、max_utilization、cost_buffer による保守的見積り。
      - aggregate cap 超過時のスケーリングと残差処理（ロット単位で再配分）の実装。
      - price 欠損時のスキップやログ出力。

- リサーチ / ファクタ計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（200 日未満は None）。
    - calc_volatility: ATR(20)、相対 ATR、20 日平均売買代金・出来高比率。データ欠損時の NULL ハンドリング。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。EPS 欠損時は None。
    - DuckDB を直接クエリして高速に集計する設計。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算。レコード不足 (n<3) や分散 0 の場合は None。
    - factor_summary / rank: 基本統計量とランク付け（同順位の平均ランク）。
  - research/__init__.py にて主要関数を公開（zscore_normalize は data.stats からインポート）。

- AI / ニュース NLP
  - ai/news_nlp.py
    - raw_news を集約して OpenAI API (gpt-4o-mini) にバッチ送信し、銘柄毎のセンチメントを ai_scores に書き込む処理を実装。
    - ニュース対象時間ウィンドウは JST 基準（前日15:00～当日08:30）を UTC に変換して照合。
    - バッチサイズ、トークン肥大化対策（記事数・文字数トリム）、最大再試行 (_MAX_RETRIES)、指数バックオフ、JSON レスポンス検証、スコアの ±1.0 クリップなどの堅牢化を実装。
    - OPENAI_API_KEY 必須（引数または環境変数）。API 失敗時は部分スキップして継続するフェイルセーフ方針。
    - （処理の最後の書き込み部分はコード内で ai_scores への置換戦略を採用：対象コードのみ DELETE → INSERT することで部分失敗に対する既存データ保護を意図）

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX (Linux, Darwin, FreeBSD) を吸収し優先度設定を行う。権限不足等は警告でスキップ。
    - set_cpu_affinity(cpu_count): 最初の N コアにピン留めする機能。未対応環境や権限エラーは警告でスキップ。
  - utils パッケージの初期化モジュール追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime), 注文成功率 (fill rate), 送信率 (send rate), P95 レイテンシ 等。
    - デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200ms）。
    - --from/--to/--db オプションに対応。DB が存在しない場合のエラー表示。
    - SQLite 内のテーブル欠損に対する安全ハンドリング（OperationalError をキャッチして N/A 表示）。

Changed
- パッケージ構成と名前空間を整備し、主要 API を __all__ で公開（portfolio / research）。

Fixed
- （初回リリースのため既知のバグ修正履歴なし。コード中に TODO コメントを残し将来改善点を明示:
  - position_sizing の price 欠損時のフォールバック価格使用、
  - apply_sector_cap の price 欠損時の取り扱い等）

Notes / 補足
- 設定・挙動に関する重要点:
  - 自動 .env 読み込みはプロジェクトルートが特定できない場合はスキップされる（配布後 CWD に依存しない設計）。
  - MONITOR_POLL_INTERVAL は正の整数であることを期待。0 以下や非整数はデフォルトにフォールバックして警告を出力。
  - PAPER_FILL_MODE に不正な値が設定されると ValueError を送出する（実行前に環境変数を確認してください）。
  - OpenAI を利用する機能は API キー必須。ネットワークや 429/5xx 等の一時エラーは内部でリトライするが、キー未設定時は即時例外を投げる。

Breaking Changes
- なし（初回リリース）

Acknowledgements
- 初期実装では実行周り（Engine / Broker）と監視（SystemMonitor）の連携を想定した設計となっており、運用時の DB パス・環境変数に注意してください。