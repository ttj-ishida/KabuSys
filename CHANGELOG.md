# Changelog

すべての非互換性のある変更は明記します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  

全般: ソースコードから推測して記載しています（実装の意図・挙動をコードベースから要約）。

## [0.1.0] - 2026-04-16

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ用ファイル (`data/stop_requested.flag`) による安全停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加（utils.process_priority を利用）。
    - SQLite / DuckDB 接続の初期化とクリーンなクローズ処理を実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の専用 SQLite（`data/paper_trading.db` または環境変数で指定）を使用して本番 DB と分離する実装。
    - BrokerClient のファクトリ経由生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て処理を実装。
    - スレッドで ExecutionEngine をデーモン実行し、停止フラグ検知時に engine.stop() を呼び出して安全に停止する仕組みを追加。
    - 実行用 PID ファイルのパス管理を実装。

- 設定管理
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
    - ロード順は OS 環境 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env ファイルのパースを堅牢化（export プレフィックス、クォート文字列、インラインコメントの扱い、保護された OS 環境変数の扱い）。
    - Settings クラスを導入し、必要な環境変数/設定値をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等）。
    - 各種設定値にバリデーション（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等）を追加。

- ポートフォリオ構築（純関数群）
  - portfolio.portfolio_builder
    - 候補銘柄選定（score 降順、同点は signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - セクター集中上限を適用する apply_sector_cap（既存保有を考慮し、売却予定銘柄を除外可能）。
    - 市場レジームに応じた投下比率 multiplier を返す calc_regime_multiplier（bull/neutral/bear のマッピング、未知はフォールバック）。
  - portfolio.position_sizing
    - 株数決定ロジック calc_position_sizes を実装。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - lot_size（単元株）による丸め、max_position_pct や max_utilization による上限、cost_buffer を使った保守的見積り
      - aggregate cap（全銘柄合計が利用可能現金を超える場合のスケーリング）と端数の再配分アルゴリズム

- 研究（Research）モジュール
  - research.factor_research
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）を DuckDB 上の prices_daily/raw_financials を参照して計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
  - research.feature_exploration
    - 将来リターンの計算 calc_forward_returns、IC（Spearman ρ）計算 calc_ic、ランク変換 rank、ファクター統計 summary を実装。
    - Pandas 等外部依存なしで標準ライブラリと DuckDB を利用する設計。
  - research.__init__ exports に zscore_normalize（data.stats 経由）等を追加。

- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から以下を集計し、簡易レポートを標準出力へ出力:
    - システム安定性（稼働率/エラー数）
    - 注文成功率（Created/Filled/Sent）
    - シグナル精度（送信率・リスク却下数）
    - API レイテンシ（avg/max/P95）
    - Pass/Fail 判定用の閾値を定義（稼働率99%、成功率90% 等）
    - 日付フィルタ（--from / --to）や --db オプションをサポート

- AI / ニュース NLP
  - ai/news_nlp.py を追加（ニュース記事のセンチメントを OpenAI API（gpt-4o-mini）でスコアリングし ai_scores テーブルへ書き込むワークフローを実装）。
    - 処理は銘柄ごとの記事集約、トークン肥大化対策（記事数上限／文字数上限）、最大 20 銘柄／バッチで API 送信、429 や 5xx に対する指数バックオフリトライ、レスポンスの厳格な JSON バリデーション、スコアの ±1.0 クリップ、部分失敗に備えた差分更新を行う設計。
    - 対象ニュースウィンドウの計算関数 calc_news_window を実装（JST ベースの前日 15:00 ～ 当日 08:30 相当を UTC に変換）。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度（set_process_priority）と CPU affinity（set_cpu_affinity）を設定するユーティリティを実装（psutil 利用、Windows と POSIX の差分を吸収、失敗時は警告でスキップ）。

### 変更
- 監視挙動の明示化
  - run_monitoring.py は Monitoring 用 DB に環境に依らず Settings.sqlite_path（いわゆる "本番" sqlite_path）を使用する実装になっている（環境変数 KABUSYS_ENV にかかわらず本番 DB を参照する点は注意）。

- Execution 起動時の DB 分離
  - run_execution.py は `settings.is_paper` 判定により paper_trading 用の SQLite を使用するように変更 / 明示（paper_trading 環境では本番 DB と完全分離）。

- .env 読み込み順と保護
  - .env ファイルの自動ロード時に OS 環境変数を保護（既存 OS 環境変数はデフォルトで上書きされない）、ただし .env.local は上書き可能で OS 環境は保護される仕様を導入。

- ロギング / 起動時メッセージ
  - run_monitoring.py / run_execution.py 起動時に KABUSYS_ENV をログに出力し、ポーリング間隔や停止フラグ検知のログを追加。

### 修正（バグ修正/堅牢化）
- MONITOR_POLL_INTERVAL の入力検証
  - `_get_poll_interval()` 実装により、環境変数が不正（非整数または 0 以下）の場合にデフォルト値（60 秒）にフォールバックして警告ログを出すように修正。time.sleep に渡す不正値による例外回避を目的とする。

- .env パーサの堅牢化
  - export プレフィックス対応、クォート文字列内部のバックスラッシュエスケープ処理、インラインコメントの適切な扱い等により .env の不正読み込みによる問題を低減。

- DuckDB / SQLite テーブル初期化
  - init_monitoring_db(sqlite_conn) を起動前に呼び出し、監視用テーブルが存在しないケースでも冪等に初期化されるように改善（監視ツール / 実行エンジン双方で実行）。

- 欠損値耐性
  - research / portfolio / tools の各クエリ・計算ルーチンで NULL / データ不足時の安全な None 返却や N=0 時の処理が丁寧に扱われるようになった（例: P95 計算で空リストは None を返す、ファクター集計でデータ無しは N/A 表示）。

### 破壊的変更（注意点）
- 監視データベースの参照先
  - run_monitoring.py が環境に関係なく Settings.sqlite_path（デフォルト: data/monitoring.db）を使用するようになったため、開発環境や paper_trading 環境で実行すると本番の monitoring DB を参照してしまう可能性があります。テストや開発環境で別 DB を使いたい場合は設定の見直し（環境変数で SQLITE_PATH を上書きする等）が必要です。

- 環境変数の必須チェック
  - Settings の一部プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError を送出するため、これらを使用するコードパスを実行する際には環境変数の設定が必須です。

### セキュリティ
- OpenAI API キーの取り扱い
  - ai/news_nlp.score_news は引数 `api_key` または環境変数 `OPENAI_API_KEY` を参照し、未設定時は ValueError を送出して処理を中断する安全策を導入（キー漏洩対策はコード外の運用を想定）。

---

注記:
- 上記はリポジトリに含まれるソースコードの実装内容から推測した変更点・機能一覧です。動作詳細や追加の変更は実際のコミット履歴やテスト結果を参照してください。