# Changelog

すべての重要な変更点をここに記載します。形式は "Keep a Changelog" に準拠します。

履歴について:
- 日付はコード内の文脈（ドキュメントやコメント）および本リポジトリの現在の状態に基づいて推測しています。
- 実装内容はソースコードから推察した機能説明・改善点です。

## [Unreleased]

（無し）

## [0.1.0] - 2026-04-12

### Added
- 全体
  - プロジェクト初期リリース。日本株自動売買システム KabuSys の基礎機能を実装。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を定義。

- 設定管理
  - 環境変数と .env 自動ロード機能を実装（`kabusys.config`）。
    - プロジェクトルートは `.git` または `pyproject.toml` を辿って自動検出。
    - `.env` と `.env.local` の優先順位ルール（OS環境 > .env.local > .env）を実装。
    - `.env` パースはコメント行、`export KEY=val`、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 必須環境変数取得（未設定時は ValueError を送出）を提供。
    - 各種設定プロパティを提供（DBパス、PID / kill flag パス、閾値、環境種別判定等）。

- 実行エンジン
  - ExecutionEngine 起動スクリプト（`src/kabusys/run_execution.py`）。
    - プロセス優先度を高に設定して起動するユーティリティ呼び出しを実行。
    - 本番/ペーパートレーディングで DB を分離（`PAPER_TRADING_SQLITE_PATH` を使用）。paper_trading 環境では MockBroker を利用する設計。
    - ブローカー、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、`ExecutionEngine.run_session()` を起動。
    - Execution に必要なリスク設定（max_position_pct、max_utilization、rate_limit 等）をデフォルトで設定。

- 監視（Monitoring）
  - SystemMonitor ポーリングループ起動スクリプト（`src/kabusys/run_monitoring.py`）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（`init_monitoring_db`）と DuckDB 接続を確立してループで `monitor.check_once()` を定期実行。
    - 監視は環境にかかわらずプロダクション用 sqlite を使用する仕様（設計上の注記）。

- ポートフォリオ構築（Portfolio）
  - 候補選定と重み計算（`kabusys.portfolio.portfolio_builder`）
    - 候補のスコア降順ソート (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。
    - スコアが全て 0 の場合のフォールバック（等金額配分）と警告ログ出力。
  - セクター制限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - セクター集中が閾値を超える場合に新規候補を除外する `apply_sector_cap`。
    - レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear をサポート、未知はフォールバック）。
  - 株数決定・投下資金制約（`kabusys.portfolio.position_sizing`）
    - リスクベース / 等配 / スコア配分に応じた発注株数計算 `calc_position_sizes`。
    - lot（単元）丸め、1銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer を使った保守的見積り、残差処理ロジックを実装。
    - 将来拡張点（銘柄別 lot_size 管理等）をドキュメント化。

- 研究（Research）
  - ファクター計算（`kabusys.research.factor_research`）
    - Momentum（1/3/6か月リターン、MA200乖離）、Volatility（ATR20、出来高等）、Value（PER, ROE）の計算を DuckDB SQL を用いて実装。不足データ時に None を返す挙動。
  - 特徴量探索（`kabusys.research.feature_exploration`）
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関による IC 計算、ファクター統計サマリー、ランク付けユーティリティを実装。
    - Pandas 等外部依存を持たず標準ライブラリと DuckDB で実装。
  - 研究用 API をまとめるパッケージエクスポート（`kabusys.research.__init__`）。

- AI / ニュース NLP
  - ニュース記事のセンチメントスコアリング（`kabusys.ai.news_nlp`）。
    - OpenAI（gpt-4o-mini）を用いて銘柄ごとに -1.0〜1.0 のスコアを算出し、ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）に基づく記事選定、1銘柄あたりの最大記事数 / 文字数トリム、20銘柄単位のバッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアクリップ（±1.0）など耐障害性を考慮した設計。
    - OpenAI API キー解決ロジック（引数 > 環境変数）と未設定時の ValueError。

- ユーティリティ
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）。
    - Windows と POSIX（Linux / macOS / FreeBSD）で差分を吸収して `set_process_priority` と `set_cpu_affinity` を提供。
    - アクセス権限不足や未実装 API に対するフォールバックロギングを実装。

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）。
    - 指定期間の system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定（閾値はソース内定義）でレポートを標準出力に出力。
    - P95 計算、各種安全策（テーブル欠如時のハンドリング）を実装。
    - CLI 引数で期間指定（--from / --to）と DB パス指定（--db）をサポート。

### Changed
- なし（初回リリースのため新規実装が中心）

### Fixed
- なし（初回リリース）

### Notes / Implementation details / Design decisions
- .env パーシングは細かなケース（引用符・エスケープ・インラインコメント）に対応しており、テスト容易性と本番配布後の堅牢性を考慮。
- Paper Trading は本番 DB と完全分離する設計。環境変数 `KABUSYS_ENV=paper_trading` を設定することで専用 DB と MockBroker を用いた挙動を行う。
- DuckDB を分析用に活用し、ファクター計算やニュース NLP の前処理で SQL ベースの集計を主に行う設計。
- Execution / Monitoring の起動スクリプトはいずれもプロセス優先度を「最初」に設定する点を強調。サーバー上での安定稼働を意識した設計。
- いくつかの箇所で将来的な拡張点（例: 銘柄別 lot_size、価格フォールバック、より精緻なエラーハンドリング）が TODO コメントとして残されている。

---

この CHANGELOG はソースコード（ドキュメント文字列とコメントを含む）に基づいて作成しています。差分（コミット単位の履歴）がある場合は、実際のコミットログに基づいて更に詳細な履歴を作成することをおすすめします。必要であれば、個々のファイルや機能ごとにより詳細な「変更点」や「既知の制限」を追記します。