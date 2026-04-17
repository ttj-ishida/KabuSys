# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装（KabuSys v0.1.0）。
  - パッケージメタ情報: `__version__ = "0.1.0"`。
- 実行系
  - run_execution 起動スクリプトを追加。
    - プロセス開始時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合、paper_trading 用の専用 SQLite DB（既定: `data/paper_trading.db`）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて `ExecutionEngine` を起動。
    - エンジンはスレッドで実行され、`data/stop_requested.flag` による停止監視を行う。実行中に停止フラグが立てられた場合は安全に停止する。
    - PID ファイル（既定: `data/execution.pid`）をサポート。
- 監視系
  - run_monitoring 起動スクリプトを追加。
    - プロセス優先度を "high" に設定。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path（既定: `data/monitoring.db`）を使用。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 停止フラグ（`data/stop_requested.flag`）でループ終了。
    - 例外はログ出力して次のポーリングへ継続（頑健性を重視）。
- 設定管理
  - `kabusys.config.Settings` を実装。
    - 環境変数読み込みの自動処理（プロジェクトルートを .git または pyproject.toml から検出）。
    - `.env` / `.env.local` の自動ロード（OS 環境変数は保護）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込み無効化可能。
    - `.env` のパーサは `export KEY=val`、クォート文字列（バックスラッシュエスケープ対応）、インラインコメントの取り扱いなどに対応。
    - 各種設定プロパティ（DB パス、PID パス、KABUSYS_ENV 検証、LOG_LEVEL 検証、Paper Trading 設定、監視閾値など）を提供。無効な値は ValueError を発生させる保護付き。
- Portfolio（銘柄選定・配分・ポジションサイズ）
  - `kabusys.portfolio.portfolio_builder`
    - select_candidates: スコア降順 + signal_rank タイブレークで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額およびスコア加重配分。スコアが全て 0 の場合は等配分にフォールバックし警告。
  - `kabusys.portfolio.risk_adjustment`
    - apply_sector_cap: セクター集中制限（既存保有のセクター比率が上限を超える場合、新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: マーケットレジーム（bull/neutral/bear）に応じた投下資金乗数。（未知レジームは警告を出して 1.0 にフォールバック）
  - `kabusys.portfolio.position_sizing`
    - calc_position_sizes: リスクベース / 等配分 / スコア配分に対応した株数決定。損切り・risk_pct・max_position_pct・max_utilization・単元株（lot_size）・コストバッファを考慮。
    - aggregate cap（総投下額が利用可能現金を超えた場合のスケールダウン）と、スケール後の端数処理（lot_size 単位での再配分）を実装。
    - price 欠損時のスキップやデバッグログを適切に出力。
    - TODO: 将来的な lot_size を銘柄別に対応する拡張の注記あり。
- 研究モジュール（DuckDB ベースのファクター計算・調査）
  - `kabusys.research.factor_research`
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を計算。データ不足は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意して実装。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS 不在は None）。
  - `kabusys.research.feature_exploration`
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。範囲検証を行い、単一クエリで効率的に計算。
    - calc_ic / rank: スピアマン（ランク相関）による Information Coefficient（IC）計算、ランク付けロジック（同順位は平均ランク）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - `kabusys.research.__init__` で上記関数を公開。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading の検証レポート生成ツール（CLI）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定（閾値はソース内で定義）。
    - DB パスは `--db` 引数 / 環境変数 `PAPER_TRADING_SQLITE_PATH` / デフォルトの優先順で解決。
    - P95 計算、欠損テーブルに対する耐性（OperationalError をキャッチして N/A 扱い）を実装。
- AI / ニュース NLP（部分実装）
  - `kabusys.ai.news_nlp` を追加（ニュースセンチメントスコアリングの骨組み）。
    - OpenAI（gpt-4o-mini）を用いたニュース→銘柄別スコア化の設計を実装。
    - バッチ処理、トークン肥大化対策、リトライ（429/ネットワーク/5xx 用の指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分成功時のテーブル置換戦略などの設計が反映されている。
    - 注意: ファイルは途中で切れている（実装途中）ため、完全動作に必要な内部関数や DB 書き込み処理が未完了の可能性あり。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - set_process_priority(level): Windows / POSIX(Linux/Mac/FreeBSD) に対応してプロセス優先度を設定。未対応 OS は警告でスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数へプロセスをピンニングするユーティリティ。権限不足や未対応環境では警告でスキップ。

### Changed
- （設計）監視プロセスが実行環境に依存せず常に本番用 monitoring DB を使用する仕様を明示（監視の独立性/一貫性確保）。
- `.env` 読み込みの優先順位と挙動を明文化（OS 環境 > .env.local > .env）。`.env.local` は既存 OS 環境を保護しつつ上書き可能。

### Fixed
- ポーリング間隔環境変数の不正値対策:
  - `MONITOR_POLL_INTERVAL` の値が 1 未満や非整数のときにデフォルト（60 秒）へフォールバックし、警告ログを出力するように修正（time.sleep へ不正値渡し回避）。
- DuckDB クエリ等で NULL と COUNT / AVG の扱いを慎重に扱うことで誤った集計やゼロ除算を防ぐ実装上の安全策を導入（factor_research / volatility / value 等）。

### Deprecated
- なし。

### Removed
- なし。

### Security
- OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用。未設定時は明示的に ValueError を出して処理を中断（誤使用防止）。

### Notes / Known issues
- `kabusys.ai.news_nlp` は設計が詳細に記述されているが、ソースが途中で切れており（ファイル末尾が未完）、実際の DB 書き込みや全ての補助関数が未実装の可能性があります。利用時は実装完了を確認してください。
- position_sizing における価格欠損時の挙動について注記（price が欠損するとエクスポージャーが過少見積りされる可能性がある）—将来的に前日終値や取得原価などのフォールバックを検討する旨の TODO が残されています。
- プロセス優先度や CPU affinity の設定は権限によって失敗する場合があり、その場合は警告ログでスキップします（動作に影響はない想定）。

---

今後のリリースでは、AI モジュールの完了、単体テスト・統合テストの追加、銘柄別 lot_size 対応、及び運用上の監視/アラート拡張を予定しています。必要であればこの CHANGELOG を基にリリースノートやデプロイ手順を生成します。