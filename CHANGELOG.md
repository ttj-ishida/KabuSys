# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」準拠です。日付はリリース時点の想定日を記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-17
初回リリース。本リポジトリは日本株自動売買システム「KabuSys」の基盤機能を提供します。主な追加点は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` にて "0.1.0" として追加。

- 実行・監視用エントリポイント
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するスクリプト。
    - プロセス優先度を設定 (high)。
    - 環境ごとに SQLite DB を分離（paper_trading 時は専用 DB を使用）。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンをスレッドで実行。
    - data/stop_requested.flag の検知で安全に停止する仕組み。
    - 起動時に PID ファイルを指定可能。

  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用する（paper/trade DB 分離とは別扱い）。
    - 停止フラグ (data/stop_requested.flag) によるループ終了処理。

- 設定管理
  - `src/kabusys/config.py`
    - .env 自動ロード機能（プロジェクトルート探索 .git / pyproject.toml を基準）。
    - .env / .env.local 読み込み順序と OS 環境変数保護機構。
    - 複雑な .env パース機能（export キーワード、クォート内部のエスケープ、インラインコメントの扱い）。
    - 各種設定プロパティ（DB パス、PID ファイル、しきい値、環境判定、paper_trading 関連設定など）。
    - PAPER_FILL_MODE のバリデーションと PAPER_TRADING_SQLITE_PATH サポート。

- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定 select_candidates、等金額/スコア重み calc_equal_weights / calc_score_weights（スコア全て 0 の場合のフォールバックと警告）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限 apply_sector_cap（既存ポジションのセクター別エクスポージャ計算と候補除外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数の計算 calc_position_sizes（risk_based / equal / score 対応）。
    - lot_size（単元株）に基づく丸め、per-position 上限、aggregate cap によるスケールダウンと端数処理。

- 研究・ファクター計算
  - `src/kabusys/research/factor_research.py`
    - モメンタム（1/3/6 ヶ月）、MA200乖離、ATR、流動性指標、財務指標（PER/ROE）などの DuckDB ベース計算関数（calc_momentum, calc_volatility, calc_value）。
    - SQL ウィンドウ関数を活用した効率的な実装。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計 summary（factor_summary）などのユーティリティ。
    - 外部依存を極力排した純 Python 実装（pandas 不使用）。
  - `src/kabusys/research/__init__.py` エクスポートの整備。

- ニュース NLP スコアリング
  - `src/kabusys/ai/news_nlp.py`
    - raw_news を OpenAI API（gpt-4o-mini 想定）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理。
    - ニュース収集ウィンドウ（JST ベースの前日15:00〜当日08:30 を UTC に変換）を算出するユーティリティ（calc_news_window）。
    - バッチ処理、1銘柄あたり記事・文字数制限、スコアクリッピング、リトライ（429/5xx/接続障害に対する指数バックオフ）等の堅牢性設計。
    - APIキーの検証（環境変数 OPENAI_API_KEY または引数で指定）。

- ツール類
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプト（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを計算して PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタリング、DB 存在チェックを実装。
  - `src/kabusys/tools/__init__.py`（パッケージ化のみ）

- 監視 DB 初期化連携
  - `src/kabusys/monitoring/monitoring_db.py`（参照されているが本体は省略）：監視用テーブル初期化を各プロセス起動時に呼び出す形で冪等に保証。

- プロセス優先度 / CPU affinity ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - set_process_priority(level) — Windows / POSIX の差分を吸収して優先度設定。
    - set_cpu_affinity(cpu_count) — 最初の N コアにプロセスを固定する機能。
    - 失敗時はログ警告でスキップ（AccessDenied 等の例外対策）。

### Changed
- 設計方針や実装注意点をコード内ドキュメントとして多数追加（PortfolioConstruction.md / StrategyModel.md 相当の参照を明示）。
- DuckDB / SQLite を併用するアーキテクチャを前提に設計（duckdb は分析用、sqlite は運用ログ/監視用）。

### Fixed
- calc_score_weights:
  - 全銘柄スコアが 0 の場合に等金額配分へフォールバックするよう修正（WARN ログ追加）。
- .env パーサー:
  - クォート内バックスラッシュエスケープ、インラインコメント、export プレフィックスの扱いを改善。

### Security
- OpenAI API キーに関しては環境変数参照を明示し、未設定時は明示的にエラーにすることで誤動作を防止。

### Notes / Known limitations
- news_nlp の書き込みは「該当銘柄のみ置換（部分的 DELETE→INSERT）」を想定しており、部分失敗時に既存スコアを保護する設計。ただし完全なトランザクション制御は DuckDB/SQLite の制約に依存。
- position_sizing では price が欠損（0.0）の場合のフォールバックが未実装（TODO コメントあり）。将来的に前日終値や取得原価のフォールバックを検討。
- calc_regime_multiplier は未知レジームでフォールバックしているが、戦略側で Bear レジーム時は BUY シグナル自体を生成しない仕様を想定している（説明コメントあり）。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップする（配布後の動作安定化のため）。

---

今後のリリース案としては、単体テスト追加、DuckDB スキーマ定義の文書化、news_nlp の API 呼び出し抽象化・モック化、各種エッジケース（価格欠損時のフォールバック等）の補強を予定すると良いでしょう。