# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」準拠です。  
このファイルは、与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です（推定内容を含みます）。

全体方針:
- 主要な追加機能・モジュール、CLI、環境変数、既知の挙動（フォールバックや安全策）を中心に記載しています。
- 日付は本ドキュメント作成日です。

## [0.1.0] - 2026-04-12

### Added
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報:
    - パッケージ名: kabusys
    - バージョン: 0.1.0

- 実行/監視用エントリースクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 起動時にプロセス優先度を "high" に設定（psutil 経由）。
    - DB 接続: 本番環境と paper_trading 環境を分離。paper_trading 時は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用。
    - BrokerClientFactory を通じてブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を呼び出す。
    - DuckDB 接続を受け取り、実行中に使用。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし警告ログを出力。
    - 監視は環境に関わらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録。
    - DuckDB 接続も確立し、監視データベース初期化関数（init_monitoring_db）を呼ぶ。
    - Ctrl+C (KeyboardInterrupt) でループを正常終了し、DB コネクションをクローズ。

- 設定・環境変数管理モジュールを追加 (config.py)
  - .env 自動ロード機能
    - プロジェクトルート（.git または pyproject.toml を検索）を基準に .env と .env.local を読み込む。
    - OS 環境変数を保護する仕組み（protected keys）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val, クォート、エスケープ、インラインコメントなどに対応。
  - Settings クラスで主要設定をプロパティ経由で提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など必須値取得メソッド。
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）。
    - PAPER_FILL_MODE（instant|partial|never|reject）を検証して返す。
    - 監視関連: pid_file_path, kill_flag_path, kill_flag_clear_on_start, cpu/memory/disk 閾値。
    - 環境判定プロパティ: env, is_live, is_paper, is_dev。
    - LOG_LEVEL 値検証。

- 取引関連コンポーネント（execution）を組み立てる基盤を追加（実装の一部は外部ファイルで想定）。
  - RiskManager に初期設定を渡す例（デフォルト値をコード内で決定）:
    - max_position_pct=0.20
    - max_utilization=0.80
    - rate_limit_per_sec=5
    - circuit_breaker_errors=10
    - circuit_breaker_window_sec=60
    - max_drawdown=0.20
    - initial_portfolio_value = broker.get_available_cash()

- 監視データベース初期化ユーティリティ（monitoring_db.init_monitoring_db）を利用する呼び出しを追加（監視テーブルの存在を冪等に保証）。

- プロファイル構築・ポートフォリオ関連の純粋関数群を追加（portfolio パッケージ）。
  - portfolio_builder.py
    - select_candidates(buy_signals, max_positions=10): スコア降順で上位 N を選択。タイブレークは signal_rank（昇順）。
    - calc_equal_weights(candidates): 等金額配分を返す。
    - calc_score_weights(candidates): スコア正規化配分。全スコアが 0 の場合は等金額配分にフォールバックし WARNING を出力。
  - risk_adjustment.py
    - apply_sector_cap(...): 既存保有と price_map を元にセクター集中を評価し、上限を超えたセクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier(regime): 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告ログ。
  - position_sizing.py
    - calc_position_sizes(...): allocation_method="risk_based" / "equal" / "score" をサポートし、lot_size（単元）やコストバッファを考慮した株数を算出。aggregate cap（available_cash）を越える場合はスケールダウンし、端数は lot 単位で再配分するロジックを持つ。

- 研究（research）関連モジュールを追加（duckdb を用いたファクター計算 / 解析）。
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility(conn, target_date): 20日 ATR、ATR%（atr/close）、平均売買代金、出来高比を計算。
    - calc_value(conn, target_date): raw_financials と prices_daily を結合して PER / ROE を計算（最新の財務レコードを選択）。
    - 全関数は DuckDB を使用し、prices_daily / raw_financials テーブルのみ参照する設計。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons): 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。有効レコード < 3 の場合は None を返す。
    - rank(values): 同順位は平均ランクを返す（float を round() して ties の検出を安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
  - research パッケージは外部に pandas を必要とせず標準ライブラリ + duckdb で動作する設計。

- AI ニュース NLP スコアリングモジュールを追加（ai/news_nlp.py）。
  - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルに書き込む。
  - 実装上の特徴:
    - バッチサイズ: 20 銘柄 / API コール
    - JSON Mode を前提とした出力検証（{"results":[{"code":"XXXX","score":0.0}, ...]} 形式を期待）
    - スコアを ±1.0 にクリップ
    - 最大リトライ回数、指数バックオフ（429 / ネットワーク / 5xx 等に対応）
    - 1 銘柄あたりの最大記事数（_MAX_ARTICLES_PER_STOCK=10）と最大文字数（_MAX_CHARS_PER_STOCK=3000）でトリム
    - ニュース収集ウィンドウは JST ベースで定義（target_date の前日 15:00 JST 〜 当日 08:30 JST、内部的には UTC に変換）
    - API キーは引数 api_key または OPENAI_API_KEY 環境変数から取得。未設定なら ValueError を発生。

- ユーティリティ（utils）を追加。
  - process_priority.py
    - set_process_priority(level): Windows/Linux/macOS を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）を設定。未サポート OS はスキップし警告ログ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め。cpu_count=None のときは変更しない。小さすぎる値は ValueError。
    - 失敗時（AccessDenied 等）は警告でスキップ。

- コマンドラインツールを追加。
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI。
    - オプション: --from, --to（日付 YYYY-MM-DD）、--db（SQLite DB パス）。
    - デフォルト DB: PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - 出力内容:
      - システム安定性: 総ポーリング数、エラー数、稼働率（%）
      - 注文成功率 / 送信率 / リスク却下数
      - API レイテンシ: avg, max, P95（P95 は全 latency_ms 値から計算）
      - Pass/Fail 判定（閾値はソースに定数で埋め込み）
        - 稼働率 >= 99.0%
        - 注文成功率 >= 90.0%
        - 送信率 >= 95.0%
        - P95 レイテンシ <= 200 ms
    - DB にテーブルが存在しない場合でも安全にデフォルト値で出力（sqlite3.OperationalError をキャッチして N/A 扱い）。

- パッケージエクスポートの定義（__init__.py など）。
  - kabusys.__init__: __version__ = "0.1.0"
  - kabusys.portfolio.__init__, kabusys.research.__init__ にて主要関数を公開。

### Changed
- （初回リリースに相当するため「追加」中心。内部のログメッセージや設計コメントにより挙動の意図を明確化。）

### Fixed
- （このリリース内では特定のバグ修正情報は無し。実装は例外処理やフォールバック（無効 env 値、DB テーブル欠如、API キー未設定、psutil の権限不足など）を多数取り入れて耐障害性を確保している。）

### Security
- 環境変数や API キーの扱いに注意する旨を実装内で考慮。
  - Settings._require により必須値未設定時は早期にエラーを出す。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストの安全性向上）。

### Notes / Known behaviours
- run_monitoring は「環境にかかわらず」Settings.sqlite_path（本番監視 DB）を使用する仕様。意図的に本番監視 DB を共通利用する設計になっているため、開発環境での実行時は注意が必要。
- run_execution は paper_trading 環境であれば paper_sqlite_path（分離された DB）を使用するため、発注ログ等は本番 DB と完全分離される。
- calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックしロギングする（予期せぬゼロスコア分布への保護）。
- position_sizing の lot_size は現状全銘柄共通の想定（将来的に銘柄別対応の拡張を予定）。
- research モジュールは pandas 等外部 heavy 依存を避け、DuckDB + 標準ライブラリで実装されている。

---

将来的なリリースでは、下記のような項目が想定されます:
- テストカバレッジの追加（ユニットテスト / 統合テスト）
- 実行エンジン / モニタの graceful shutdown の拡張
- ブローカーやストレージの設定をより柔軟にするための設定拡張
- ai/news_nlp のレスポンスバリデーション強化・ロギング改善
- position_sizing の銘柄別単元サポート（lot_map）など

（注）本 CHANGELOG は提供されたソースコードを基に推測して作成しています。運用やリリース管理の実際の履歴に合わせて適宜編集してください。