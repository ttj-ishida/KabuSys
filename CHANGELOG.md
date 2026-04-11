# Changelog

すべての重要な変更点をこのファイルに記録します。  
以下は提供されたコードベースから推測して作成した変更履歴です。

フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-11
### Added
- 基本バージョン 0.1.0 を追加（パッケージ定義: kabusys.__version__ = "0.1.0"）。
- 実行用スクリプトを追加:
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。起動時にプロセス優先度を設定し（set_process_priority("high")）、SQLite / DuckDB に接続してセッション実行（engine.run_session()）を行う。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（データ分離：data/paper_trading.db を想定）を使用し、モック・ブローカーを利用する設計をサポート。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て、RiskConfig / EngineConfig を用いた設定で起動する。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動。
- 設定管理モジュールを追加（config.py）:
  - .env 自動ロード機構を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env / .env.local の読み込み順序、OS 環境変数の保護（protected keys）、自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを提供（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、KILL_FLAG_PATH、各種しきい値、KABUSYS_ENV/LOG_LEVEL 判定ユーティリティなど）。
  - env / log_level のバリデーション（許容値チェック）を追加。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）:
  - portfolio_builder.py:
    - select_candidates: スコア降順、同点時は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄のスコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（max_sector_pct）で新規候補を除外。既存保有のうち当日売却予定は除外。未知セクター ("unknown") は上限適用除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear をサポート、未知レジームは警告の上 1.0 にフォールバック）。
  - position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に応じた株数・発注数決定。単元株(lot_size)で丸め、per-stock 上限 / aggregate cap / cost_buffer を考慮したスケーリングと再配分ロジックを実装。
- 研究用モジュールを追加（kabusys.research）:
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の SQL ウィンドウ関数を利用）。
    - calc_volatility: ATR20、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務を取得）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得するクエリを実装。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。3 件未満は計算不能として None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と統計要約（count/mean/std/min/max/median）を実装。
  - research パッケージのエクスポートを追加（zscore_normalize を含む）。
- AI 関連モジュールを追加（kabusys.ai）:
  - news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）へ送り銘柄ごとのセンチメント(ai_score)を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）や記事集約、1銘柄あたり文字数制限・記事数上限の実装、最大 BATCH_SIZE=20 でのバッチ送信、API 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフ）、レスポンス検証、スコア ±1.0 クリップ、部分失敗時に他銘柄の既存スコアを保護するための部分 DELETE→INSERT のトランザクション処理を実装。
    - OpenAI 呼び出し部は _call_openai_api として分離（テスト用に差し替え可能）。
  - regime_detector.py:
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを重み付けして日次の市場レジーム ('bull'/'neutral'/'bear') を判定するロジックを実装（MA: 70%、マクロ: 30%）。
    - target_date 未満のデータのみを使用する等、ルックアヘッド防止の設計。
    - API エラー時は macro_sentiment=0.0 で継続するフェイルセーフを実装。
- ユーティリティを追加（kabusys.utils）:
  - process_priority.py:
    - set_process_priority(level): Windows / POSIX を吸収しクロスプラットフォームで優先度設定（high/normal/low）。権限不足や未対応 OS は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め（None で無効化）。入力検証と権限エラー処理あり。
- パッケージの __all__ / エクスポート整理: portfolio / research モジュールで主な関数を __all__ に追加。

### Changed
- 設定読み込みの振る舞いを明確化:
  - OS 環境変数が優先され、.env は上書きされない（.env.local は override=True で上書きするが OS 環境変数は保護される）。
  - 自動ロードはプロジェクトルートが見つからない場合はスキップ。
- DuckDB / SQLite を組合わせた処理パターンを採用:
  - 監視・実行・研究・AI いずれも DuckDB 接続を受け取り SQL を活用している。
- 日付取得方法の方針:
  - 主要な処理（AI スコアリング / レジーム判定等）は内部で datetime.today() / date.today() を直接使わず、引数 target_date を使う方式でルックアヘッドバイアスを防止する設計に統一。

### Fixed
- 環境変数・入力値の堅牢性を向上:
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出し、警告のうえデフォルト値（60 秒）にフォールバックするロジックを追加。
  - PAPER_FILL_MODE の無効値を検出して ValueError を投げるバリデーションを追加。
  - KABUSYS_ENV / LOG_LEVEL の無効値検証を追加。
- DuckDB 互換性対策:
  - ai_scores 書き込み時、DuckDB 0.10 の executemany の空リスト制約に対応するため、空チェックを入れてから executemany を呼ぶ実装に修正（トランザクションとロールバックガード含む）。
- API 呼び出しの堅牢性:
  - OpenAI 呼び出しに対して 429/接続/タイムアウト/5xx を対象に指数バックオフで再試行する実装を追加し、一部エラーはフェイルセーフでスキップするようにした。

### Security
- OpenAI API キーの取り扱い:
  - score_news / regime_detector は api_key 引数を受け、None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げるようにして API キーの存在を明示的に要求。

### Notes / その他（設計上の想定・既知事項）
- 多くの関数は「純粋関数」かつ副作用を抑える設計（DB 参照の限定、日時引数の明示など）で実装されており、テストしやすさを意識した設計がなされていると推測される。
- 将来の拡張余地（例: 銘柄ごとの lot_size をマスタで持つ、価格フォールバックの改善等）について TODO コメントで言及あり。
- 一部処理はログ出力（info/debug/warning/exception）を充実させており、運用時のトラブルシュートを考慮している。

---
注: 上記は提供されたソースコードの内容から推測してまとめた変更履歴です。リポジトリの過去のコミット履歴や実際のリリース管理に基づくものではなく、コードに現れている機能・振る舞いを反映しています。必要であれば、より正確なコミット単位の CHANGELOG 化（各コミットの要約を時系列で列挙）も作成できます。