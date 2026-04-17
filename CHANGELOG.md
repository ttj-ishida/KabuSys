# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
当該リリースは、コードベースから推測可能な機能追加・設計意図・挙動改善点をまとめたものです。

全体方針:
- データベースは SQLite（監視用）および DuckDB（時系列ファクター計算等）を併用。
- Paper Trading と本番は DB を分離し、発注系の挙動をモック化して検証可能に設計。
- 外部 API 呼び出し（OpenAI / ブローカー等）は明確に抽象化・フェイルセーフ化。
- .env の自動読み込みはプロジェクトルート検出に依存し、安全な上書き制御を提供。

Unreleased
---------
（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------
Added
- 実行エントリ／デーモン系
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient（BrokerClientFactory 経由）を使用し、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）に記録して本番 DB と分離。
    - execution.pid の管理、停止フラグ（data/stop_requested.flag）による安全停止対応を実装。
    - エンジンを別スレッドで起動して監視するループを実装（停止時は engine.stop() を呼出し安全終了）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトへフォールバックして警告を出力。
    - 監視処理は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視用 DB として統一）。
    - process priority を最初に high に設定する処理を導入（utils/process_priority を利用）。

- 設定管理
  - config.py: Settings クラスを追加し、環境変数 / .env / .env.local から安全に設定を取得。
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD に依存しない）。
    - .env 読み込みは OS 環境変数を保護する protected 機構を導入（.env.local は override=True）。
    - 複雑な .env 行（export プレフィックス、クォート、エスケープ、インラインコメント）に対応する独自パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - 各種設定プロパティを実装（DB パス、PID/kill フラグ、監視しきい値、PAPER_FILL_MODE の検証、env/log_level の検証など）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順、同点は signal_rank 昇順でタイブレーク。上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等金額へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用。既存ポジションのセクター別エクスポージャを計算し上限超過セクターの新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: 市場レジーム(bull/neutral/bear) に応じた投下資金乗数を提供。未知のレジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: risk_based / equal / score）。
      - risk_based: 許容リスク率・stop_loss に基づくサイズ計算。
      - equal/score: 重み・max_utilization・max_position_pct に基づく計算。
      - lot_size（単元株）で丸め、cost_buffer を加味した aggregate cap スケーリング（利用可能現金を超える場合のスケールダウンと残差に対する優先付け割付）を実装。
      - 価格欠損（<=0）時はスキップし、ログ出力。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily を用いて計算。
    - calc_volatility: ATR(20)/相対ATR/平均売買代金/出来高比率を計算。true_range の NULL 伝播を適切に扱う設計。
    - calc_value: raw_financials から直近財務指標を取得し PER/ROE を算出。
    - いずれもデータ不足時の None ハンドリングとパフォーマンスを考慮したスキャンレンジを実装。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト: 1,5,21）を一度のクエリで取得。ホライズン検証あり。
    - calc_ic / rank / factor_summary: Spearman ランク相関（IC）計算、平均・分散・中央値等の統計サマリを標準ライブラリのみで提供。ties（同順位）の平均順位処理や丸めによる ties 検出漏れ回避を実装。
  - research/__init__.py: 各関数群をエクスポート（zscore_normalize を data.stats から取り込み）。

- AI ニュース NLP
  - ai/news_nlp.py: OpenAI (gpt-4o-mini) を用いたニュースセンチメント解析処理を導入。
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウ計算（calc_news_window）。
    - 複数銘柄をまとめて最大 20 銘柄ずつバッチ送信、JSON Mode を期待するプロンプト設計、スコアを ±1.0 にクリップ。
    - 429/ネットワーク/5xx に対する指数的バックオフリトライ、レスポンスバリデーション、部分成功時に既存スコアを保護する DELETE→INSERT 戦略などフェイルセーフ設計。
    - API キーの解決（引数 or OPENAI_API_KEY 環境変数）、未設定時は ValueError。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - CLI (--from / --to / --db) による期間指定。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を算出して PASS/FAIL 判定（しきい値はファイル内定数で定義）。
    - P95 計算、日付フィルタのパラメタ化、DB 存在チェック、テーブル欠如時の安全フォールバックを実装。

- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収してプロセス優先度設定を提供（high/normal/low）。
    - set_cpu_affinity によりプロセスを先頭 N コアに固定可能。アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

Changed
- 環境変数パースの改良
  - .env パーサが export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等をサポート。これにより .env の柔軟性を向上。
- DB 接続ポリシー
  - 監視（run_monitoring）は環境にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用する明示的ポリシーを採用。
  - run_execution は paper_trading 時に専用 DB を使用するように変更（本番 DB と完全分離）。

Fixed
- 設定値バリデーション強化
  - PAPER_FILL_MODE の許容値を検証し、不正値は ValueError を発生させるようにした（明確なエラーメッセージ）。
  - KABUSYS_ENV / LOG_LEVEL の値検証を追加し、不正値は ValueError。
- ポーリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL のパースにおいて 0 以下や非整数が与えられた場合に警告しデフォルト値へフォールバックするように変更（time.sleep での ValueError を回避）。
- ファクター/統計処理の堅牢化
  - NULL / データ不足 / 0 除算などのケースを考慮し、None を返すか安全に無視する実装に統一。
  - calc_ic: 有効レコード数が 3 未満や分散が 0 の場合は None を返す。

Security
- API キー取り扱い
  - OpenAI API キーは明示的に引数で渡すか OPENAI_API_KEY 環境変数から解決。未設定時は例外で早期検出（不注意な情報漏洩を防止）。
- .env の読み込みは OS 環境変数を protected として扱い、デフォルトで OS 環境変数を上書きしない安全なロード順序（OS 環境 > .env.local > .env）。

Notes / Known limitations
- ai/news_nlp.py はバッチ処理・レスポンス検証など多くの安全策を備える一方で、API 呼び出し部分の実装詳細（部分的な実装・切断処理等）は実行環境依存のためデバッグが必要となる場合があります。
- position_sizing の価格欠損時の fallback は現在ログ出力のみ（TODO: 前日終値や原価を使ったフォールバックの可能性を注記）。
- apply_sector_cap は "unknown" セクターを保護（上限適用外）としています。マスタデータの完全性に依存するため sector_map の整備を推奨します。
- DuckDB の executemany 等の挙動（バージョン差）に注意。ai/news_nlp の一括 INSERT/DELETE 前に params が空でないことを確認する実装方針あり。

Contributing
- バグ報告・改善提案は issue を立ててください。環境変数や DB パス周りの変更は既存の自動ロード・保護機構との互換性を確認のうえ行ってください。

License
- このコードベースのライセンス表記はソース内に明記されているものに従ってください。