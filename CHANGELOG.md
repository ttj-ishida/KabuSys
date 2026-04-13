# Changelog

すべての重要な変更はこのファイルに記載します。本ファイルは「Keep a Changelog」形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-13
初回リリース — コードベースの主要機能群を追加。

### Added
- 全体
  - パッケージ初期リリース。自動売買システム「KabuSys」のコア機能群を実装。
  - バージョン情報を `kabusys.__init__` にて `0.1.0` として定義。

- 起動スクリプト
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトへフォールバック）。
    - 監視プロセスは KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視データは本番 DB を参照/記録）。
    - 起動時にプロセス優先度を "high" に設定。
    - 例外発生時はログに例外情報を出力して次のポーリングまで待機するフェイルセーフ実装。
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、専用の paper-trading SQLite DB（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - ブローカークライアントは Factory 経由で生成（Paper 時は Mock を使用想定）。
    - ExecutionEngine の依存コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler）を組み立てて `run_session()` を実行。

- 設定管理
  - `config.py`
    - .env 自動ロード機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - .env パースの実装強化（export、クォート内エスケープ、インラインコメント処理、無効行スキップ等に対応）。
    - Settings クラス実装（多数のプロパティを提供）:
      - DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
      - PID / kill flag 設定
      - 閾値設定（CPU/MEM/DISK の閾値）
      - 環境種別検証（KABUSYS_ENV: development / paper_trading / live のみ許容）
      - PAPER_FILL_MODE の検証（"instant" / "partial" / "never" / "reject"）
      - LOG_LEVEL の検証
    - 必須環境変数取得用のヘルパ `_require()` を提供（未設定時は ValueError を送出）。

- プロセス管理ユーティリティ
  - `utils/process_priority.py`
    - プラットフォーム差（Windows / POSIX 系）を吸収してプロセス優先度を設定する `set_process_priority(level)` を追加。
    - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を追加（権限不足や未対応環境ではログ警告でスキップ）。
    - psutil を利用しつつ、AccessDenied 等の例外を安全にハンドリングしてフォールバック。

- ポートフォリオ構築
  - `portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates()`（スコア降順、同点は signal_rank 昇順でタイブレーク）。
    - 重み計算 `calc_equal_weights()`（等額配分）と `calc_score_weights()`（スコア加重、全スコアが 0 の場合は等分にフォールバック）。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限 `apply_sector_cap()` を実装（既存保有のセクター別エクスポージャーが上限を超える場合に当該セクターの新規候補を除外）。
      - unknown セクターは上限判定の対象外（除外しない）。
      - 当日売却予定の銘柄をエクスポージャー計算から除外可能。
      - TODO として価格欠損時のフォールバック処理を記載。
    - 市場レジームに基づく乗数 `calc_regime_multiplier()`（"bull"→1.0, "neutral"→0.7, "bear"→0.3、未知レジームは 1.0 にフォールバック）。
  - `portfolio/position_sizing.py`
    - 発注株数計算 `calc_position_sizes()` を実装。
      - allocation_method = "risk_based" | "equal" | "score" をサポート。
      - リスクベース計算（risk_pct, stop_loss_pct）と等比率系の配分をサポート。
      - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
      - aggregate cap 超過時のスケールダウンロジック（スケールに基づく floor と lot 単位での再配分）を実装。
      - cost_buffer により手数料・スリッページを保守的に反映。
      - TODO: 将来的な銘柄別 lot_size の導入について記載。

- リサーチ / ファクター計算
  - `research/factor_research.py`
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してファクターを計算する純粋関数を提供:
      - calc_momentum(): mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA の要件チェックあり）
      - calc_volatility(): ATR20、ATR相対値、20日平均売買代金、出来高比率
      - calc_value(): PER, ROE（raw_financials の latest レコードを参照）
    - スキャンウィンドウや窓幅等の定数はモジュール内で定義。
    - DuckDB のウィンドウ関数を活用して効率的に計算。
  - `research/feature_exploration.py`
    - 将来リターン計算 calc_forward_returns()（複数ホライズン対応、ホライズンのバリデーションあり）。
    - IC（Spearman）計算 calc_ic()、および補助の rank() 実装（同順位は平均ランク、丸めで ties 検出の安定化）。
    - factor_summary(): 基本統計量（count/mean/std/min/max/median）を算出。
    - 設計方針として DuckDB と標準ライブラリのみを使用（pandas 等に依存しない）。

- AI / ニュース NLP
  - `ai/news_nlp.py`
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を計算して ai_scores テーブルへ書き込む処理を追加。
    - 主な仕様:
      - ニュースウィンドウは target_date の「前日 15:00 JST ～ 当日 08:30 JST」に対応（UTC に変換して DB 検索）。
      - 1 銘柄あたり最大記事数と最大文字数でトリム（デフォルト: 10 件、3000 文字）。
      - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE = 20）。
      - レート制限やネットワークエラー・5xx を対象に指数バックオフでリトライ（最大 3 回）。
      - レスポンス検証、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護するための差分置換手順（DELETE + INSERT）を採用。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得。未指定時は ValueError。
      - フェイルセーフ設計： API 全体が失敗してもプロセスは続行（個別チャンク失敗の影響を最小化）。

- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading 検証レポート生成 CLI を追加。
    - 検証指標（稼働率・注文成功率・送信率・P95 レイテンシ等）を集計して標準出力へ出力。
    - デフォルトの閾値を定義（稼働率 99.0%、注文成功率 90.0%、送信率 95.0%、P95 レイテンシ 200 ms）。
    - 日付フィルタ (--from / --to) と DB パス指定 (--db) をサポート。PAPER_TRADING_SQLITE_PATH 環境変数を優先して使用。
    - DuckDB を使わず SQLite の monitoring テーブルを参照して集計する想定。
    - 欠損テーブルに対しては sqlite3.OperationalError を捕捉して N/A 表示にフォールバック。

- パッケージエクスポート
  - `portfolio/__init__.py`、`research/__init__.py` に主要 API をエクスポートして使いやすくした。

### Changed
- 初版リリースのため特になし（新規実装）。

### Fixed
- 初版リリースのため特になし。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーの取り扱いは環境変数または明示的引数で解決。未設定時は明示的にエラーを出すことで誤使用を抑止。

---

補足 / 注意点（コード上の設計メモ）
- 多くの関数は外部副作用を極力排し、DuckDB / SQLite 接続を引数で受け取る純粋関数的な設計を採用している（ユニットテストが容易）。
- いくつかの箇所に将来の拡張・改善を示す TODO コメントあり（例: 価格欠損時のフォールバック、銘柄別 lot_size）。
- 実行環境依存の操作（process priority, cpu affinity）は権限不足や未対応 OS の場合に警告ログを出して安全にスキップする実装。
- 監視・実行スクリプトは起動時に DB コネクションを作成し、finally ブロックで必ずクローズするよう設計されている。