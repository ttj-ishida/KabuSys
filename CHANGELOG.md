CHANGELOG
=========
すべての注目すべき変更をこのファイルに記載します。
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（なし）

0.1.0 — 2026-04-13
-----------------
初回リリース。

Added
- 基本アプリケーション構成
  - パッケージバージョンを定義: kabusys.__version__ = 0.1.0

- 実行エントリ / プロセス運用
  - run_execution.py: ExecutionEngine の起動スクリプトを追加
    - 環境に応じて paper_trading 用の専用 SQLite DB(data/paper_trading.db) を使用（KABUSYS_ENV=paper_trading）。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine.run_session() によりセッション実行。
    - 起動直後にプロセス優先度を "high" に設定。
    - 監視テーブルを冪等に初期化する init_monitoring_db 呼び出しを含む。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加
    - デフォルト 60 秒のポーリング。MONITOR_POLL_INTERVAL 環境変数で上書き可能（不正値はデフォルトにフォールバックして警告）。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。
    - DuckDB / SQLite の接続管理とクリーンなクローズを実装。

- 環境設定・ローダー
  - config.py: 環境変数読み込み・Settings クラスを追加
    - プロジェクトルート検出ロジック: .git または pyproject.toml を起点に自動的に .env / .env.local をロード（CWD 非依存）。
    - .env パーサー強化: export KEY=val 形式、クォート（シングル/ダブル）のエスケープ、インラインコメントルールに対応。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - protected 引数を用いた .env 上書き制御（OS 環境変数の保護）。
    - Settings に多数のプロパティを実装（DB パス、paper_trading 用パス、PID/KILL フラグパス、閾値、PAPER_FILL_MODE 等）および入力値バリデーション。
    - KABUSYS_ENV / LOG_LEVEL の有効値チェックを実装。

- プロセス制御ユーティリティ
  - utils/process_priority.py を追加
    - set_process_priority(level): Windows / POSIX を吸収してカレントプロセスの優先度を設定（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count): カレントプロセスを先頭 N コアにピン留め。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順で選定、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。全スコアが 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別上限 (max_sector_pct) を超える場合に新規候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数。未知レジームは 1.0 でフォールバックし警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score 各方式で発注株数を計算。
      - lot_size による丸め、per-position 上限 (max_position_pct)、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残余キャッシュによる端数割当て等を実装。
      - 価格欠損時のスキップやログ出力、単元株（lot_size）単位の調整をサポート。

- リサーチ（DuckDB ベースのファクター計算）
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を用いた Momentum / Volatility / Value ファクター群の計算を実装。
    - 実運用向けのウィンドウ長や欠損ハンドリング（必要行数未満は None）を考慮。
  - research/feature_exploration.py
    - calc_forward_returns: 翌日/翌週/翌月等の将来リターンを一括クエリで算出（horizons 検証あり）。
    - calc_ic: スピアマンランク相関（IC）計算（レコード不足時は None）。
    - factor_summary / rank: ファクター統計サマリ・ランク変換ユーティリティを実装。
  - research/__init__.py にエクスポートを追加。

- AI ニュース NLP
  - ai/news_nlp.py を追加
    - raw_news / news_symbols を集約し、OpenAI API (gpt-4o-mini) を JSON Mode で呼び出して銘柄ごとのセンチメント(±1.0)を ai_scores テーブルに書き込むロジックを実装。
    - 処理フロー: 時間ウィンドウ計算、記事トリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、銘柄チャンク処理（最大 20 銘柄／回）、429/5xx/ネットワーク故障に対する指数バックオフリトライ、レスポンス検証、スコアクリップ、部分成功時の db 更新保護（対象コード絞り込みで削除→挿入）。
    - API キーが未設定の場合は ValueError を送出。
    - ルックアヘッドバイアスを避ける設計（date.today() などを直接参照しない）。

- 運用ツール
  - tools/paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標を集計し、閾値に基づき PASS/FAIL 判定を出力。
    - 日付フィルタ (--from / --to) に対応、テーブルがない場合でも例外を握り潰して N/A 相当で出力。
    - P95 計算、フォーマットユーティリティを提供。

Changed
- データベース周り
  - 監視初期化 (init_monitoring_db) を起動スクリプト内で冪等に実行するようにし、監視テーブルの存在を保証。

Fixed
- 環境変数パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ、export 構文、インラインコメント処理などの改善により .env の読み込み精度を向上。

Notes / Implementation details
- DuckDB / SQLite を併用する設計:
  - DuckDB は主にリサーチ・ファクター計算用途、SQLite は監視・発注ログ等の軽量トランザクション用途で使用する想定。
- Paper Trading の分離:
  - paper_trading 環境では SQLite を別 DB に分離して本番データと完全分離する設計を採用。
- 安全性・フェイルセーフ:
  - 外部 API (OpenAI) の失敗はリトライ/ログ/スキップでフェイルセーフに処理。
  - 権限不足や環境差分に起因する処理（プロセス優先度/affinity 設定）は失敗しても警告を出して続行。

Acknowledgements
- 本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートはリポジトリの正式リリース履歴に基づいて更新してください。