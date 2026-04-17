# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

現在のリリース方針: 初回リリースを含むバージョン単位で記載します。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ導入: kabusys 名前空間と初期バージョン情報を追加。
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

- 設定/環境変数管理機能を追加（堅牢な .env 自動読み込みを含む）。
  - src/kabusys/config.py
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env / .env.local の自動読み込み（読み込み順: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - export KEY=val 形式やクォート付き値、inline コメントなどを正しくパースする .env パーサーを実装。
    - 環境変数取得ラッパー _require() を導入し、未設定時に分かりやすい例外を発生させる。
    - Settings クラスを実装し、以下のプロパティ等を提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須/任意設定
      - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
      - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
      - KABUSYS_ENV のバリデーション（development / paper_trading / live）
      - 各種監視閾値（CPU/MEM/DISK）や PID ファイルパスなど

- 実行・監視エントリポイントを実装。
  - src/kabusys/run_execution.py
    - ExecutionEngine の起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント抽象化、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、EngineConfig / ExecutionEngine の起動処理を追加。
    - 実行中は data/stop_requested.flag による外部停止検知（フラグがある場合は起動を行わない / 走行中に検知すれば engine.stop() で停止）。
    - execution.pid を出力する pid_file の扱い。
  - src/kabusys/run_monitoring.py
    - SystemMonitor を用いた監視ループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバック。
    - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らず本番監視 DB を参照する設計）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループ終了。

- 監視 DB 初期化ユーティリティ（init_monitoring_db）の利用を導入（冪等に監視テーブルを保証）。
  - run_execution.py / run_monitoring.py で init_monitoring_db を呼び出し、テーブルがない場合も安全に起動可能に。

- プロセス優先度・CPU affinity 設定ユーティリティを追加。
  - src/kabusys/utils/process_priority.py
    - set_process_priority(level) を実装（"high" / "normal" / "low"）。
    - Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収して nice / priority を設定。
    - 権限不足や未実装 API に対しては警告ログでフェールセーフにスキップ。
    - set_cpu_affinity(cpu_count) を追加し、指定したコア数にプロセスをピン留め可能（安全なエラーハンドリングあり）。

- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存）。
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）で上位 N を選出。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（全スコア 0 の場合は等配分へフォールバック）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限超過時に候補をフィルタリング（unknown セクターは除外免除）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とデフォルトフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じて銘柄ごとの発注株数を算出。
    - lot_size 単位で丸め、aggregate cap（available_cash） を超える場合はスケールダウンして残差を lot 単位で再配分するロジックを実装（手数料/スリッページのための cost_buffer を考慮）。

- 研究 / リサーチ機能を追加（DuckDB を使ったファクター計算・解析）。
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily, raw_financials を参照）。
    - 200日 MA、ATR20、各種モメンタム（1M/3M/6M）等を計算。データ不足時は None を返す。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターン一括取得（引数でホライズン制御）。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・欠損除外・有効レコード閾値判定を実装）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・基本統計量サマリーを実装。
    - rank() は浮動小数丸めで ties 誤検出を防止する処理を追加。

- Paper Trading 検証レポート生成ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - CLI 実行可能なレポートジェネレータを提供（--from / --to / --db オプション対応）。
    - PAPER_TRADING_SQLITE_PATH 環境変数対応（デフォルト data/paper_trading.db）。
    - システム稼働率 / 注文成功率 / 送信率 / レイテンシ（avg/max/P95） / リスク却下数などを集約して出力。
    - P95 計算ユーティリティ、SQL の存在チェックと sqlite3.OperationalError に対する安全処理を実装。
    - 合格/不合格の閾値（稼働率 99%、成功率 90% 等）を定義し判定を出力。

- OpenAI を用いたニュース NLP スコアリング基盤を追加（初期実装）。
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄毎にテキストを生成し、OpenAI（gpt-4o-mini）でセンチメント（-1.0〜1.0）を生成、ai_scores テーブルへ書き込む処理を設計・一部実装。
    - 機能ハイライト: タイムウィンドウ計算（JST→UTC 変換）、記事集約（記事数・文字数トリム）、バッチ送信（最大 20 銘柄）、JSON Mode のレスポンスバリデーション、スコアクリップ（±1.0）、エクスポネンシャルバックオフ（429/ネットワーク/5xx）など。
    - API キー解決（api_key 引数 > OPENAI_API_KEY 環境変数）、未設定時は ValueError を送出。
    - （注）ファイルは大きく実装されているが、このコミット時点で最後のフェッチ処理が途中で切れている部分あり（後続コミットで完成予定）。

### Changed
- 環境変数 / 設定の扱いをより安全に。
  - .env パーサーが export 形式とクォートエスケープ、inline コメント処理をサポート。
  - .env.local は .env の上書きとして扱う（OS 環境変数は常に保護）。
  - Settings のいくつかのプロパティは入力値のバリデーションを行い、不正値は ValueError を発生させる（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。

- 監視・実行スクリプトの挙動修正 / 安全化。
  - run_execution: 起動前に停止フラグをチェックしていればエンジンを起動しない。
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値や 0/負値は警告ログ出力の上でデフォルトにフォールバック。
  - どちらのスクリプトも起動直後に set_process_priority("high") を呼び出して優先度を引き上げようとする（失敗時は警告を出して継続）。

- position_sizing のスケーリングロジックを改善。
  - aggregate cap 超過時のスケールダウン後、lot_size 単位で残余キャッシュを用いて端数配分（fractional remainder に基づく再配分）を行うことで、より多くの有効ポジションを確保するロジックを追加。
  - price が欠損（0 や None）の場合は該当銘柄をスキップし、安全に動作するように調整。

- apply_sector_cap の挙動:
  - 現在値計算で sector_map にないコードは "unknown" 扱いにして上限チェックから除外（未知セクターはブロックしない）。

- research モジュールの SQL は DuckDB を前提に最適化（window 関数・LEAD/LAG の利用）。パフォーマンスを考慮してスキャン範囲にカレンダーバッファを導入。

### Fixed
- DB 接続のクローズを保証。
  - run_execution.py / run_monitoring.py 内で finally ブロック等により sqlite3 / duckdb の接続を必ず close するようにした。

- paper_verification_report の堅牢性向上。
  - DB ファイルが存在しない場合の分かりやすいエラーメッセージ出力を追加。
  - 各種クエリでテーブル未存在時に sqlite3.OperationalError をキャッチしてデフォルト値でレポート生成を継続。

- process_priority の例外ハンドリングを強化。
  - psutil の AccessDenied / NotImplementedError 等をキャッチして警告ログを出すように変更（権限のない環境でも起動可）。

- feature_exploration.rank() の ties 処理を改善し、浮動小数の丸め誤差による ties 検出漏れを回避。

### Security
- 環境変数の取り扱いにおいて OS 側の既存環境変数を .env ファイルで上書きしないデフォルト動作を採用（.env.local は明示的に上書きが可能だが OS 環境変数は protected）。

### Notes / Known issues
- src/kabusys/ai/news_nlp.py は大部分が実装済みですが、スクリプト末尾の一部（記事取得→API送信フローの継ぎ目）がこの時点で途中で切れているため、完全動作のためには後続コミットでの補完が必要です（現在は設計・多くの処理が実装済みで、API キー関連の例外やバリデーションは整備済み）。
- Paper Trading の挙動は paper_sqlite_path による DB 分離で安全化されていますが、モックブローカーの挙動（fill_mode の詳細や部分執行のシミュレーション）は運用テストを推奨します。

---

過去の履歴はこのファイルに順次追加していきます。バグ修正や機能追加は該当バージョンの下に追記してください。