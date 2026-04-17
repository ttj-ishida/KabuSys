# Changelog

すべての注目すべき変更点を記録します。慣例に従い主要な変更はセクションに分類しています（Added / Changed / Fixed / Known issues / Notes）。このファイルはコードから推測して作成しています。

※ 参照: Keep a Changelog 準拠

## [0.1.0] - 2026-04-17
初回リリース（コードベースから推定）。

### Added
- 監視・実行の起動スクリプトを追加
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし警告ログを出力。
    - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループ終了。
    - 監視処理では Settings にかかわらず本番の sqlite_path を使用して DB を初期化（init_monitoring_db）。
    - duckdb を併用した接続を確立。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite DB（data/paper_trading.db がデフォルト）を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ・PID 管理・スレッドベースのセッション管理を備える。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・環境変数の読み込み
  - config.py
    - Settings クラス導入（各種環境変数をプロパティとして取得・検証）。
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で判定）。
    - .env/.env.local の読み込みルール（OS 環境変数を保護、override の挙動）。
    - export 形式やクォート付き値、インラインコメントなどを考慮した .env パーサを実装。
    - KABUSYS_ENV / LOG_LEVEL の許可値チェック、PAPER_FILL_MODE のバリデーションなどを含む。
    - 各種パス（duckdb_path, sqlite_path, paper_sqlite_path, pid_file_path, kill_flag_path）や監視閾値（cpu/memory/disk）のプロパティを提供。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのソート・上位 N 抽出（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（全スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限により候補を除外するロジック（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。
    - 単元（lot_size）丸め、per-position の上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer を用いた保守的なコスト見積り、残差処理による追加配分などを実装。
    - 未取得価格（price が欠損）のハンドリングログや将来的な拡張点（銘柄別 lot_size）への TODO コメントあり。

- 研究・ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（欠損データを考慮）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を算出（target_date 以前の最新財務データを取得）。
  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21）での将来リターン計算（入力検証あり）。
    - calc_ic: ファクターと将来リターンに対する Spearman ランク相関（IC）を計算（有効レコードが 3 未満で None を返す）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティ。

- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む設計。
    - ニュースウィンドウの計算（JST ベース -> UTC に変換）を提供（calc_news_window）。
    - バッチ送信（最大 20 銘柄）、JSON Mode 出力を期待、スコアのクリップ、429/ネットワーク/5xx に対する指数バックオフリトライ設計、レスポンス検証などを実装予定。
    - OpenAI API キーの解決（引数優先、環境変数 OPENAI_API_KEY を参照）を実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・P95 レイテンシ等を集計して判定（PASS/FAIL）を出力する。
    - 日付フィルタ、P95 計算、欠損テーブルに対する寛容なハンドリング（OperationalError をキャッチして N/A とする）を実装。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority(level): Windows / POSIX（Linux, Darwin, FreeBSD）に対応した優先度設定。権限不足や未対応 OS の場合は警告ログを出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン固定する機能（例外ハンドリングあり）。

### Changed
- パッケージメタ情報
  - kabusys.__init__.py に __version__ = "0.1.0" を設定。

- 環境変数読み込みロジックの強化
  - .env パーサの強化（export プレフィックス、クォート・エスケープ、インラインコメント処理）により .env ファイルの互換性を向上。
  - 自動読み込みはプロジェクトルート検出が失敗した場合はスキップする（配布後の安全性向上）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト向け）。

### Fixed
- .env 読み込み失敗時に警告を出すようにして静かに失敗する問題を扱う（ファイル読込の OSError を warnings.warn で通知）。

### Known issues / Notes
- ai/news_nlp.py はファイル末尾が途中で切れている（コードが断片的）。具体的には記事取得部分（_fetch_articles 等）以降が未表示／未実装の可能性があるため、本番運用前に実装完了・テストが必要。
- portfolio/position_sizing.py と portfolio/risk_adjustment.py にいくつかの TODO コメントあり：
  - price が欠損した場合のフォールバック価格（前日終値等）の未実装。
  - 将来的に銘柄別 lot_size を導入する余地あり。
- process_priority の優先度設定は OS 権限に依存するため、非特権環境では動作しない（警告ログを出してスキップ）。
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」設計になっているため、開発者が意図せず本番 DB に書き込むリスクがある（運用ポリシーに注意）。
- paper_verification_report は DuckDB ではなく SQLite の paper_trading DB を対象としているため、DuckDB 側データとの整合性は別途確認が必要。

### Security
- ai/news_nlp.py で OpenAI API キーを環境変数から取得するが、キー管理は利用者側で適切に行う必要あり（ログ出力にキーを含めない等の注意が必要）。

---

今後の提案（コードから推測）
- ai/news_nlp の未実装部分を完成させ、単体テストを追加する。
- run_monitoring の DB 使用ポリシー（環境による切替）を設定で明示して意図せぬ本番 DB 書き込みを防ぐオプションを追加する。
- portfolio の価格欠損時フォールバックや銘柄別 lot_size サポートを実装する。
- DuckDB & SQLite 両方を操作する処理について、トランザクションや接続クローズ周りの E2E テストを充実させる。

以上。