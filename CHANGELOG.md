# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に従います。  
このファイルは、配布されているソースコードの内容から推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-04-12
最初の公開リリース（コードベースから推測）。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行/監視スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper DB（デフォルト `data/paper_trading.db`）を使用し、MockBrokerClient 経由で完全に本番 DB と分離して実行する。
    - 実行開始時にプロセス優先度を "high" に設定。
    - ExecutionEngine の構成（OrderManager, OrderRepository, RiskManager, Reconciler など）を組み立て、自動的にセッションを実行する。
    - RiskManager に対してデフォルトの RiskConfig を適用（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。
    - 監視は環境設定にかかわらず本番用 `sqlite_path` を使用して監視 DB を初期化・更新する。
    - プロセス優先度を "high" に設定して起動。

- 設定管理
  - config.py: 環境変数/.env 管理モジュールを追加。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、`.env` / `.env.local` を自動読み込み（OS 環境変数優先、`.env.local` は上書き、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` 行パーサは `export KEY=val`、シングル/ダブルクォート、エスケープ、インラインコメント処理などに対応。
    - Settings クラスを提供し、多数のプロパティ経由で設定を取得:
      - J-Quants / kabu API / LINE トークン、データベースパス（duckdb/sqlite/paper_sqlite）、
      - 監視用パス（pid_file, kill_flag 等）、しきい値（CPU/MEM/DISK）、
      - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV のバリデーション（development/paper_trading/live）など。
    - settings = Settings() のインスタンスをモジュールで提供。

- ポートフォリオ構築関連（純粋関数）
  - portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（タイブレークに signal_rank）と上位 N 抽出。
    - calc_equal_weights, calc_score_weights: 等金額配分およびスコア正規化配分（全スコア 0 の場合は等配分にフォールバックして警告）。
  - position_sizing.py
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）を実装。
      - risk_based: 許容リスク率・損切り率を用いた株数算出。
      - lot_size（単元）で丸め、per-stock 上限・aggregate 上限（available_cash）を考慮したスケーリングと残差処理を実装。
      - cost_buffer を用いた概算コストによる保守的な算出。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、上限を超えるセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト値と unknown でのフォールバック動作）。

- 研究（research）モジュール（DuckDB を使用）
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比などを計算（true_range の NULL 伝播を慎重に扱う実装）。
    - calc_value: raw_financials と結合して PER / ROE を算出（最新期データの取得ロジックを実装）。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - calc_ic: スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - rank: 同順位は平均ランクを採る安定したランク関数（丸めで ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の基本統計量サマリを提供。
  - research/__init__.py から適切にエクスポート。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約し、銘柄毎に最大記事数・文字数をトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、API レスポンスの検証、スコアの ±1.0 クリップを実装。
    - スコアは ai_scores テーブルへ置換（対象コードのみ DELETE → INSERT）することで部分失敗時の既存データ保護を行う。
    - score_news の引数で api_key を明示可。未指定か空文字列の場合は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を送出。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows と POSIX（Linux / Darwin / FreeBSD）に対応してプロセス優先度（nice / HIGH_PRIORITY_CLASS）を設定。未対応 OS はスキップして警告。
    - set_cpu_affinity(cpu_count): 最初の N コアに CPU affinity を設定（引数 None で無設定）。権限不足や未対応環境では警告を出してスキップ。
  - utils パッケージ基礎ファイルを追加。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出。
    - CLI 引数で期間指定（--from / --to）および DB パス指定（--db）。
    - 判定基準（閾値）を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 latency 200ms）。
    - P95 の計算、NULL/テーブルなしの場合のフォールバック処理、出力フォーマットを提供。

- DuckDB/SQLite 連携
  - 多数のモジュールが duckdb.DuckDBPyConnection / sqlite3.Connection を受け取り SQL を用いてデータを取得・計算するように実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 環境変数・設定の堅牢性向上
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非数）で ValueError を防ぎ、デフォルトにフォールバックして警告を出すように実装。
  - .env パーサでの引用符・エスケープ・コメントの扱いを明示的に実装し、実行環境依存のパース差異を吸収。
  - PAPER_FILL_MODE の入力検証を追加し、不正値時に ValueError を送出。

- ロバストネス
  - run_monitoring のループ内で monitor.check_once() が例外を投げてもループを継続し、例外ログを出力して次ポーリングへ移行するように実装（フェイルセーフ設計）。
  - tools/paper_verification_report で対象テーブルが存在しない場合に sqlite3.OperationalError を補足して適切に N/A / 0 を返すようにした。

### Security
- OpenAI API キーは明示的に引数または環境変数から読み取る設計。未設定時は ValueError を発生させ、意図しない認証情報漏洩リスクを低減。

### Notes / Behavior
- 監視（run_monitoring）は「環境にかかわらず」本番 sqlite_path を使用して監視テーブルを初期化する仕様。運用時のデータ分離に注意。
- 実行（run_execution）は KABUSYS_ENV=paper_trading の場合 paper_db を使用し、本番 DB と分離する設計。
- 研究系モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB で完結するよう実装されている。
- position_sizing の aggregate キャップ処理では lot_size（単元）による丸めや残差を考慮した再配分ロジックを備える。
- ai/news_nlp は JSON モード期待のシステムプロンプトと厳密なレスポンス検証の上でスコアを算出するため、OpenAI 側の応答フォーマットに依存する点に留意。

---

この CHANGELOG はソースコードから機能や設計方針を推測して作成しています。実際のリリースノートや変更履歴として利用する場合は、コミット履歴やリリース管理情報に基づく確認・追記を推奨します。