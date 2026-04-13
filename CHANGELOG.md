# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
注: 以下の変更点は提示されたコードベースの内容から推測して記載しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期構成。バージョン情報を `kabusys.__version__ = "0.1.0"` として定義。
- 設定読み込み / 環境変数 (`kabusys.config`)
  - プロジェクトルート検出機能を追加（.git または pyproject.toml を基準に探索）。プロジェクト配布後も CWD に依存せず自動 .env ロードが可能に。
  - `.env` / `.env.local` の自動読み込み機能を実装。OS 環境変数を保護する `protected` 機能を導入。
  - 自動ロードを無効にするための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。
  - `.env` パーサを充実化:
    - コメント行、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォート無し行でのインラインコメント判定の改善。
  - `Settings` クラスを実装し、アプリケーション全体の設定アクセサを提供（DB パス、PID/kill フラグパス、閾値、環境種別など）。
  - `PAPER_FILL_MODE` のバリデーションを追加（有効値: "instant"|"partial"|"never"|"reject"）。
  - `PAPER_TRADING_SQLITE_PATH` による paper trading 用 DB 分離設定を追加。
  - 環境種別 `KABUSYS_ENV` の検証（development / paper_trading / live）を追加。
- 実行 / 監視エントリポイント
  - `run_execution.py` を追加:
    - プロセス優先度を高く設定して実行。
    - paper_trading 環境では paper 専用 SQLite DB を使用して本番 DB と分離。
    - Broker クライアントファクトリ経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を実行。
    - DuckDB 接続を受け取り、Engine に渡す実行フローを実装。
  - `run_monitoring.py` を追加:
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視用 DB は環境にかかわらず本番の sqlite_path を使用。
    - `SystemMonitor` を初期化してループで `check_once()` を実行。例外はログに記録して次回ポーリングへ継続。
    - プロセス優先度設定を起動時に適用。
- モニタリング DB 初期化
  - `init_monitoring_db` を使用して監視用テーブルが存在することを保証（冪等）。
- ツール
  - `tools/paper_verification_report.py` を追加:
    - Paper Trading の検証レポートを生成する CLI スクリプト（--from/--to/--db オプション対応）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどの指標を計算・表示。
    - P95 計算、日付フィルタ生成、テーブルが存在しない場合のフォールバック処理を実装。
    - デフォルト DB パスは `data/paper_trading.db`。環境変数 `PAPER_TRADING_SQLITE_PATH` に対応。
    - 合格/不合格の閾値（稼働率99%、注文成功率90%、送信率95%、P95 ≤ 200ms）を定義。
- ポートフォリオ構築（純粋関数群）
  - `portfolio.portfolio_builder`:
    - シグナル選定（スコア降順、タイブレークに signal_rank）と上位 N 抽出。
    - 等金額配分とスコア加重配分（スコア合計が 0 の場合は等分へフォールバック）。
  - `portfolio.risk_adjustment`:
    - セクター集中上限の適用（既存保有時価を用いたセクター別エクスポージャ計算、売却予定銘柄の除外、"unknown" セクターは除外しない挙動）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ）を提供。未知レジームは警告の上 1.0 にフォールバック。
  - `portfolio.position_sizing`:
    - risk_based / equal / score の配分方式を実装。
    - リスクベースでの株数計算（許容リスク率、損切り幅を考慮）。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を考慮した保守的見積り。
    - スケールダウン時の再配分（端数を残差順に lot_size 単位で配分）を実装。
- ユーティリティ
  - `utils.process_priority`:
    - Windows / POSIX を透過してプロセス優先度を設定する `set_process_priority(level)` を実装。
    - CPU アフィニティを最初 N コアに固定する `set_cpu_affinity(cpu_count)` を追加（バリデーション・例外処理・ログ出力あり）。
    - 許可不足や未実装 API に対するフォールバック（警告ログ）を実装。
- リサーチ / ファクター計算
  - `research.factor_research`:
    - Momentum, Volatility, Value ファクター計算を DuckDB 上で実装（prices_daily / raw_financials を参照）。
    - MA200、ATR20、複数ホライズンのリターンなどを SQL ウィンドウ関数で計算。
    - スキャンレンジやウィンドウ長は定数化してパフォーマンスを考慮。
  - `research.feature_exploration`:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。
    - Spearman ランク相関（IC）計算、ランク付けユーティリティ（同順位は平均ランク）を実装。
    - 基本統計量（count/mean/std/min/max/median）を計算する summary 関数を実装。
  - `research.__init__` で主要関数を公開（zscore 正規化を data.stats から再エクスポート）。
- AI / ニュース NLP（下書き）
  - `ai.news_nlp` を追加（ニュース記事の OpenAI によるセンチメントスコア付与処理）。
    - ニュース収集ウィンドウの計算（JST → UTC 変換）、記事集約、銘柄ごとのトリム（記事数・文字数制限）を実装。
    - OpenAI (gpt-4o-mini) を用いたバッチ送信（最大 20 銘柄/チャンク）、JSON Mode 出力を期待。
    - 429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリップ。
    - 書き込みは対象コードのみ置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）して部分失敗の影響を最小化。
    - API キー未設定時は明示的なエラーを発生させる。

### Changed
- 設定周り
  - 環境変数優先順位を明確化：OS 環境変数 > .env.local > .env（ただし OS 環境変数は保護され上書きされない）。
- 実行フロー
  - 実行スクリプトで起動時にプロセス優先度を設定するように変更（run_execution, run_monitoring）。
- モニタリング
  - `MONITOR_POLL_INTERVAL` を導入し可変ポーリング間隔を設定可能に（不正値はログ警告のうえデフォルト使用）。
  - `SystemMonitor` の check_once 呼び出しで例外をキャッチしてループ継続するフェイルセーフ動作に。

### Fixed
- env パーサの不正な .env 行処理・クォート/エスケープの欠落に対応。
- DuckDB へ `executemany` する際の空パラメータ対策（空パラメータ時の呼び出し回避）に留意した実装。
- 各種欠損データ時の None/NULL ハンドリング（ファクター計算、レポート生成、position sizing の price 欠損時ログ・スキップ等）。

### Security
- OpenAI API キー未設定時に明示的に失敗するチェックを追加（ai.news_nlp）。

## [0.1.0] - 2026-04-13

- 初回公開と見なされるリリース（上記機能群を含む）。