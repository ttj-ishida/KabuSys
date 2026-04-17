CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
日付はコードベースに基づくリリース推定日（本ファイル作成日: 2026-04-17）です。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-17
初回リリース。自動売買システム KabuSys のコア機能群を追加。

### 追加 (Added)
- パッケージ基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージの公開 API を `kabusys` パッケージの `__all__` で定義。

- 環境設定 / ロード機構（kabusys.config）
  - .env / .env.local 自動ロード機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を探索して検出（CWD 非依存）。
    - OS 環境変数を尊重し、`.env.local` による上書きが可能。
    - 自動ロードを無効化するためのフラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサー: export プレフィックス、クオート、エスケープ、インラインコメント処理に対応。
  - 設定クラス `Settings` を追加。主要プロパティ:
    - J-Quants / kabuステーション / LINE API の設定取得
    - DB パス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト: data/monitoring.db）、Paper Trading 用 `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）
    - Paper Trading 固有: `paper_fill_mode`（有効値: "instant" | "partial" | "never" | "reject"）
    - 監視・PID/killフラグ関連: `pid_file_path`, `kill_flag_path`, `kill_flag_clear_on_start`
    - 監視閾値: `cpu_threshold_pct`, `memory_threshold_pct`, `disk_threshold_pct`
    - 環境判定: `env`（有効値: development / paper_trading / live）および `is_live`, `is_paper`, `is_dev`
    - ログレベル検証: `log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- 実行・監視起動スクリプト
  - SystemMonitor 用起動スクリプト `run_monitoring.py`
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効扱いしてフォールバック）。
    - 監視処理は KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様。
    - 停止フラグ `data/stop_requested.flag` を検知してループを終了。
    - DuckDB と SQLite の接続管理を行い、最後にクローズする。
    - 実行開始時にプロセス優先度を "high" に設定。

  - ExecutionEngine 用起動スクリプト `run_execution.py`
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db）に記録。実運用 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動。
    - 停止フラグ検知でエンジン停止。PID ファイル path 管理（data/execution.pid）。
    - 初期処理でプロセス優先度を "high" に設定。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を import して起動スクリプトで利用（監視テーブルの存在保証）。

- プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level: "high" | "normal" | "low")
    - Windows: psutil の優先度定数を利用。
    - POSIX (Linux, Darwin, FreeBSD): nice 値を設定。
    - 未対応 OS や権限不足時は警告ログを残してスキップ。
  - set_cpu_affinity(cpu_count: int | None)
    - 指定コア数にプロセスを固定。無効値チェックと権限不足ハンドリングあり。

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分、スコア正規化配分（全スコア 0 の場合は等配分にフォールバック）。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限(max_sector_pct) を評価して候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull=1.0, neutral=0.7, bear=0.3、未知は警告後 1.0）。
    - apply_sector_cap 内には価格欠損時の TODO コメント（将来的に前日終値等でフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）
      - 単元株（lot_size, デフォルト 100）で丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングを実装。
      - risk_based: リスクパーセンテージとstop_lossで株数決定。
      - aggregate cap のスケールダウン後、残余で端数を lot 単位で再配分するロジックを実装。
    - 将来的な拡張点: 銘柄別 lot_size の導入を想定した TODO。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB の prices_daily から計算。データ不足時は None。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。true_range の NULL 伝播制御あり。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0 の場合は None）。
    - 計算に使用する窓や日数は定数化（MA200、ATR20 等）。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一回のクエリで取得。horizons の妥当性チェックあり。
    - calc_ic: Spearman ランク相関（IC）をランク化（同順位は平均ランク）して計算。有効レコードが 3 未満で None を返す。
    - rank / factor_summary: ランク化、基本統計量（count/mean/std/min/max/median）。
  - research パッケージの public API を __all__ で公開（zscore_normalize を kabusys.data.stats から取り込み）。

- ツール類（kabusys.tools）
  - paper_verification_report
    - Paper Trading の検証レポート生成 CLI。
    - コマンドライン引数: --from, --to（YYYY-MM-DD）、--db（DBパス）。
    - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 生成する指標:
      - システム安定性（総ポーリング数、エラー数、稼働率）
      - 注文関連（総注文数、Filled, Sent、成立率・送信率）
      - シグナル精度（Created / Sent）
      - リスク却下数（risk_logs）
      - API レイテンシ（平均/最大/P95）
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率（Filled/Created） >= 90.0%
      - 送信率 (Sent/Created) >= 95.0%
      - P95 レイテンシ <= 200 ms
    - レポートは標準出力へ出力。DB テーブルが無い場合は N/A や 0 を返すフェイルセーフ実装。

- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して OpenAI （gpt-4o-mini）でセンチメントを算出、ai_scores テーブルに書き込む設計を追加。
  - 実装方針（主な特徴）:
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換）を対象。
    - 1 回の API 呼び出しで最大 20 銘柄をバッチ処理、1 銘柄あたり最大記事数 と 文字数でトリム。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフおよび上限回数のリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ・部分的書き換え（成功したコードのみ置換）によるフェイルセーフ。
  - API キー未設定時は ValueError を送出して明示的に失敗させる設計。
  - （注）news_nlp モジュールはファイル末尾が途中で切れている形跡があり、実装が未完である可能性がある（開発中の関数継続あり）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 既知の問題 / 注意点 (Known issues / Notes)
- news_nlp モジュールの一部が途中で切れている（ソース末尾が不完全）。動作させるには未完部分の実装補完が必要。
- apply_sector_cap の価格欠損（price が 0.0）の扱いについて注記あり。将来的に前日終値や取得原価を使ったフォールバックを検討する必要がある。
- position_sizing の設計は現在単元株数 lot_size を全銘柄共通で扱う。将来的に銘柄別 lot_map に対応する改修を予定。
- run_monitoring は監視データ収集に本番 sqlite_path を使用するため、テスト環境で同じ DB に書き込まないよう運用上の注意が必要。
- Process priority / CPU affinity の設定は権限やプラットフォームに依存し、失敗時は警告のみ（処理継続）。

### マイグレーション / 運用メモ (Migration / Operational notes)
- 環境変数:
  - 自動 .env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
  - Paper Trading 用 DB を分離するので、ペーパートレード実行時は `KABUSYS_ENV=paper_trading` を設定すること（この場合 paper DB を使用）。
  - OpenAI を利用するニュース NLP 機能を使う場合は `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key を渡すこと。
  - `MONITOR_POLL_INTERVAL` で監視ポーリング間隔を秒単位で指定可能（デフォルト 60 秒）。
  - `PAPER_FILL_MODE` の有効値: "instant" | "partial" | "never" | "reject"。

- データベース:
  - DuckDB と SQLite を併用。DuckDB は大規模なリサーチ・時系列計算、SQLite は実行 / 監視 / ロギング用途を想定。
  - paper_trading モードでは paper 用 SQLite を使用し、本番データと分離。

- ログレベル:
  - Settings.log_level で検証を行う。無効値は例外となる。

以上がコードベースから推測できる変更・機能一覧です。必要であれば、各ファイルごとの詳細な仕様書や、未完実装箇所のリストアップ（TODO）を作成します。どの情報を優先して出力しましょうか？