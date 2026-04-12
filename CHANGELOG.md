# CHANGELOG

すべての注目すべき変更履歴を Keep a Changelog 準拠で日本語にて記載します。

フォーマット:
- 各リリースには日付を付記しています。
- カテゴリは Added / Changed / Fixed / Deprecated / Removed / Security を使用しています。

## [0.1.0] - 2026-04-12
最初の public リリース。システム監視、実行エンジン、ポートフォリオ構築、リサーチ、ニュース NLP、環境設定ユーティリティ等のコア機能を実装しました。

### Added
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority を呼び出し）。
    - SQLite / DuckDB 接続を確立し、init_monitoring_db を呼んで監視テーブルを保証。
    - KeyboardInterrupt による安全な終了処理と DB クローズを実装。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite (PAPER_TRADING_SQLITE_PATH / data/paper_trading.db) を使用し本番 DB と分離。
    - 起動時にプロセス優先度を "high" に設定。
    - BrokerClientFactory を用いたブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動する run_session を呼び出す。
    - RiskManager のデフォルト設定（max_position_pct 等）を ExecutionEngine 起動時に使用。initial_portfolio_value は broker.get_available_cash() を取得して初期化。

- 環境設定
  - src/kabusys/config.py
    - .env/.env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - .env パーサ（_parse_env_line）を実装：export プレフィックス、クォート付き値、バックスラッシュエスケープ、インラインコメント取り扱いなどに対応。
    - .env 読み込みで override/protected（OS 環境変数の保護）をサポート。
    - Settings クラスを導入して環境変数をプロパティ化。J-Quants / kabu API / DB パス / PID/KILL フラグ /閾値 等を提供。
    - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の入力検証を実装（不正値は ValueError）。
    - paper_sqlite_path、duckdb_path、sqlite_path のデフォルトを定義。

- 監視・ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加（CLI: --from, --to, --db オプション）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の集計と PASS/FAIL 判定を実装。閾値はソース内定義（稼働率 99% 等）。
    - DB 存在チェック、テーブル存在欠如時のフォールバック、p95 計算、出力フォーマットを実装。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全銘柄スコアが 0 の場合に等金額配分へフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が上限を超える場合に新規候補を除外）を実装。sell_codes（当日売却予定）をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を実装。未知のレジームは警告を出して 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: 銘柄ごとの発注株数計算を実装。「risk_based」「equal」「score」方式をサポート。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash）に応じたスケーリング、cost_buffer を考慮した保守的見積り、端数配分アルゴリズムを実装。
    - 価格未取得の場合のスキップ処理やデバッグログあり。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX を吸収してプロセスの優先度を設定（psutil 利用）。未対応 OS はスキップし警告。
    - set_cpu_affinity: 最初の N コアにピン留めする機能を追加。引数検証と例外ハンドリングあり。
    - 例外（権限不足等）は警告ログによりスキップされるフェイルセーフ実装。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: モメンタム（1M/3M/6M リターン、MA200 乖離）を DuckDB SQL で実装。一定行数未満は None を返す。
    - calc_volatility: ATR20 / ATR_pct / 20日平均売買代金 / 出来高比等を実装。true_range の NULL 伝播に注意して計算。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算。target_date 以前の最新財務データを取得。

  - research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD で一括取得。horizons の検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。有効レコードが 3 未満なら None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量集計（count/mean/std/min/max/median）を実装。
    - 実装は外部ライブラリに依存せず標準ライブラリのみで完結。

  - research.__init__
    - 必要な関数群と zscore_normalize をエクスポート。

- AI ニュース NLP
  - ai/news_nlp.py
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメントスコアリングして ai_scores テーブルへ書き込む機能を実装。
    - 処理フロー: ニュースタイムウィンドウ計算（前日15:00 JST〜当日08:30 JST）、記事集約（銘柄ごとに最新 N 記事・文字数トリム）、最大 20 銘柄単位のバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンスバリデーション、±1.0 でスコアをクリップ、部分失敗時に既存スコア保護のため対象コードのみ置換（DELETE→INSERT）する方針。
    - calc_news_window を実装（UTC 変換の取り扱いを明確にしている）。
    - OpenAI API キー未設定時は ValueError を送出。

- DB / DuckDB
  - 各モジュールで DuckDB 接続を受ける設計（リサーチ / AI など）。SQLite は監視 / paper_trading 用に利用。

### Changed
- （該当なし: 初回リリースのため既存からの変更はありません）

### Fixed
- （該当なし: 初回リリースのためバグ修正履歴はありません）

### Deprecated
- （該当なし）

### Removed
- （該当なし）

### Security
- OpenAI API キーの取り扱いは明示的に引数または環境変数 (OPENAI_API_KEY) を使用。未設定時はエラー化して明示的に対処する設計。

### Notes / 注意点
- .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。パッケージ配布後にルートが検出できない場合は自動ロードはスキップされます。
- 一部関数や箇所に TODO コメントが残っています（例: price 欠損時のフォールバック、将来的な lot_size の銘柄別対応等）。
- ai/news_nlp は API 呼び出し失敗時もフェイルセーフで部分的にスキップして継続する設計だが、API 利用コストやレイテンシを考慮して運用側で適切な管理が必要です。
- run_monitoring は MONITOR_POLL_INTERVAL の不正値に対するフォールバックロジックを装備していますが、0 以下や非整数文字列は警告されデフォルトに戻ります。
- paper_trading と本番 DB は分離設計（paper_sqlite_path を利用）されており、ペーパートレード検証が本番データを汚染しないようになっています。

ご要望があれば、
- 追加で「変更点を細かくファイル単位で列挙する」、
- あるいは「リリースノート風（運用上の注意点や移行手順を重点的に）」に整形する
などの別バージョンの CHANGELOG を作成します。どちらが良いですか？