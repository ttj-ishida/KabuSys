# Changelog

すべての注記は Keep a Changelog の形式に従います。  
慣例: 変更は主にコードベースから推測して記載しています（実装や仕様の意図に基づく要約）。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-12
初回公開リリース。自動売買システム「KabuSys」の核となる機能群を実装しています。

### Added
- 全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - DuckDB と SQLite を併用するデータアクセス基盤を導入（prices_daily / raw_financials 等の分析用、monitoring / paper_trading 用の SQLite）。
- 設定 / 環境読み込み（kabusys.config）
  - .env / .env.local の自動読み込み機構を導入（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 読み込みルール:
    - OS 環境変数は保護し、.env.local が .env を上書きできる。
    - export プレフィックス対応、クォート・エスケープ対応、インラインコメントの挙動制御。
  - Settings クラスを提供し、各種設定値（DBパス、APIトークン、監視閾値、PAPER_FILL_MODE, KABUSYS_ENV など）をプロパティで取得可能に。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
- 実行 / 監視プロセス
  - 実行エントリ: run_execution.py
    - ExecutionEngine の起動スクリプトを提供。ExecutionEngine は Broker、OrderManager、OrderRepository、RiskManager、Reconciler を組み合わせてセッションを実行。
    - paper_trading 環境では MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）に記録して本番 DB と分離。
    - duckdb を分析向けに接続して使用。
  - 監視エントリ: run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用するように実装。
    - 起動時にプロセス優先度を上げる仕組みを最初に実行。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順選抜（同点は signal_rank でタイブレーク）。
    - calc_equal_weights, calc_score_weights: 等金額およびスコア加重の重み計算（スコア全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有含めたセクター毎エクスポージャを算出し、上限を超えるセクターの候補を除外。unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数の計算（未知レジームは 1.0 で警告付きフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。lot_size（単元）丸め、per-stock 上限・aggregate 上限のスケーリング、および cost_buffer による保守的評価を実装。
- 研究・ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）を計算。必要データ不足時は None を返す実装。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPSが0やNULLのときは None）。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）を一度のクエリで取得可能に実装。horizons のバリデーションを実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード数が3未満なら None）。
    - factor_summary, rank: 基本統計量とランク付けユーティリティを実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）をエクスポートしている。
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI を用いたニュースのセンチメントスコアリングモジュールを実装。
  - 処理内容:
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づき記事を集約。
    - 1 銘柄あたり最大記事数・最大文字数でトリム。
    - 最大 20 銘柄 / チャンクで OpenAI（gpt-4o-mini）へ送信（JSON Mode を想定）。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスをバリデートし、スコアを ±1.0 にクリップして ai_scores テーブルへ書き込み（部分失敗に備えた差し替え戦略）。
  - API キーは引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError を投げる。
- ツール（kabusys.tools）
  - paper_verification_report: paper trading 用 SQLite を読み、システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定する CLI レポート生成スクリプトを追加。閾値を定義して PASS/FAIL を判定。
  - CLI 引数: --from / --to / --db をサポート（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）。
- ユーティリティ（kabusys.utils）
  - process_priority:
    - set_process_priority(level): Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
    - set_cpu_affinity(cpu_count): 指定コア数へ CPU affinity を設定（None は設定しない）。権限不足等は警告してスキップする。
  - 共通ログや例外処理の挙動を整備。

### Changed
- 設計上の注意点・動作仕様の明確化
  - run_monitoring は monitoring 用 DB 初期化（init_monitoring_db）を行い、常に本番 sqlite_path を使用する。監視は環境切替に依存させない設計。
  - run_execution は paper_trading モード時に DB を分離し、監視テーブルがない場合でも init_monitoring_db を呼び冪等に存在を確保する。
  - Settings のプロパティは各種環境変数のバリデーションを行う（LOG_LEVEL, KABUSYS_ENV, PAPER_FILL_MODE 等）。
  - ファクター計算 / 研究モジュールは DuckDB 依存の SQL を主体に実装し、外部 API へアクセスしない方針を明記。
  - ニュース NLP はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない実装方針を採用。

### Fixed / Robustness improvements
- .env パーサーの強化
  - export プレフィックス、クォートされた値内のバックスラッシュエスケープ、コメントの扱い（スペース前の # をコメントとみなす等）をサポートし、より現実的な .env フォーマットに耐性を持たせた。
  - 読み込みに失敗した場合は警告を出し処理を継続（テスト環境での堅牢性向上）。
- ポーリング間隔の安全管理
  - MONITOR_POLL_INTERVAL に不正値（0 以下や非整数）が設定された場合、デフォルト値にフォールバックしてログに警告を出す（time.sleep の ValueError を回避）。
- 計算時の NULL / 0 ハンドリング
  - ファクター計算（momentum, volatility, value）やレポート生成時にデータ不足・NULL に対する安全処理（None を返す、計算可能性チェック）を追加。
  - position_sizing 等で価格が欠損（0 や None）の場合はスキップするようにして誤発注リスクを低減。
- 外部操作失敗時のフェイルセーフ
  - process_priority / cpu_affinity 設定時の権限不足や未実装関数に対し、例外を握りつぶして警告に留める実装（実行継続性を確保）。
  - AI スコアリングの API エラー時はチャンク単位でリトライまたはスキップし、他の銘柄処理を保護する。

### Notes / Known limitations
- 一部の TODO コメントが存在（例: price のフォールバック手段、銘柄別 lot_size のサポート等）。
- position_sizing と sector_exposure の価格欠損時の過少見積りによりブロックが外れる可能性がある旨の注記がある（将来的に前日終値等のフォールバックを検討）。
- OpenAI を利用する AI モジュールは API 利用に伴うコストやレート制限の取り扱いに注意が必要。

---

脚注:
- 本 CHANGELOG は提供されたソースコードの実装とドキュメンテーション文字列から推測して作成しています。実際の運用上の仕様や追加の変更点がある場合は、それに応じて更新してください。