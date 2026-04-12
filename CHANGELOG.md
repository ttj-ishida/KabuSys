# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣習に従います。  

## [0.1.0] - 2026-04-12
初回リリース。以下の主要コンポーネントと機能を追加しました。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として追加。

- 設定管理 (`kabusys.config`)
  - .env 自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサーは `export KEY=val` 形式、クォート（シングル/ダブル）やバックスラッシュエスケープ、インラインコメント処理に対応。
  - 必須環境変数取得用ヘルパー `_require()` と各種設定プロパティを提供:
    - J-Quants / kabu API / LINE トークン、DB パス (DuckDB / SQLite)、paper trading 用 DB パス、PID/KILL フラグパス、リソース閾値 (CPU/MEM/DISK) など。
  - 環境名検証 (`KABUSYS_ENV`: development/paper_trading/live) や `LOG_LEVEL` 検証を実装。
  - `PAPER_FILL_MODE`（paper trading の擬似約定挙動）をサポート。許容値: "instant" / "partial" / "never" / "reject"（デフォルト: "instant"）。不正値は ValueError。

- 実行系起動スクリプト
  - Execution エントリポイント: `kabusys.run_execution`
    - プロセス優先度を起動時に "high" に設定（`kabusys.utils.process_priority.set_process_priority`）。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 専用 SQLite DB（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と完全分離。
    - ブローカークライアントは `BrokerClientFactory.create(settings)` により環境に応じて生成（モックの利用を想定）。
    - 注文周りコンポーネントを組み立てて `ExecutionEngine.run_session()` を実行。
    - 実行前に監視用テーブルが存在することを保証するため `init_monitoring_db()` を呼び出し（冪等）。
    - DuckDB 接続も使用（`settings.duckdb_path`）。

  - Monitoring エントリポイント: `kabusys.run_monitoring`
    - プロセス優先度を "high" に設定。
    - 監視は常に本番用 SQLite パス (`settings.sqlite_path`) を使用（環境に依存しない）。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。0 以下や不正な値はデフォルトにフォールバックし警告を出力。
    - `SystemMonitor.check_once()` を定期実行するポーリングループ。例外は捕捉してログ化した上で次回ポーリングへ継続。KeyboardInterrupt による終了処理を実装。
    - DuckDB 接続も使用。

- 監視 DB 初期化ユーティリティ
  - `kabusys.monitoring.monitoring_db.init_monitoring_db` を利用して監視テーブルの存在を保証（Execution / Monitoring 起動時に呼び出し）。

- プロセス/CPU ユーティリティ (`kabusys.utils.process_priority`)
  - Windows と POSIX (Linux/Mac/FreeBSD) を吸収する `set_process_priority(level)` を実装（psutil を利用）。
  - `set_cpu_affinity(cpu_count)` を追加し、最初の N コアにプロセスをピン留め可能。権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築モジュール (`kabusys.portfolio`)
  - `portfolio_builder.py`
    - buy シグナルの候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を追加。
    - スコア合計が 0 の場合は等金額配分にフォールバックし警告を出す挙動を実装。
  - `risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を追加（既存保有時価を参照し上限を超えるセクターの新規候補を除外）。"unknown" セクターは上限判定から除外。
    - 市場レジームに応じた乗数 `calc_regime_multiplier` を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知は警告の上 1.0 フォールバック）。
  - `position_sizing.py`
    - 銘柄ごとの株数算出 `calc_position_sizes` を実装。
    - 複数の配分方式をサポート: "risk_based", "equal", "score"。
    - lot_size（単元株）単位で丸め、1 銘柄上限・総投下上限（aggregate cap）のスケーリングロジックを実装。
    - cost_buffer による保守的な約定コスト見積もりを考慮。
    - 価格欠損時のスキップやデバッグログを追加。

- 研究・ファクター計算モジュール (`kabusys.research`)
  - `factor_research.py`
    - モメンタム、ボラティリティ、バリュー系ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（200 行未満は None）。
      - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率（ウィンドウ内データ不足時は None）。
      - calc_value: raw_financials と prices_daily を結合し PER / ROE を算出（EPS が 0/欠損の際は None）。
    - DuckDB を用いた SQL ベースの実装、target_date パラメータ駆動。
  - `feature_exploration.py`
    - 将来リターン計算 (`calc_forward_returns`)：複数ホライズン対応、入力検証あり。
    - IC（Spearman の ρ）計算 (`calc_ic`)、ランク変換ユーティリティ (`rank`)。
    - ファクター統計サマリー (`factor_summary`) を追加。
  - `research.__init__` で必要な API を再エクスポート（zscore_normalize など）。

- AI ニュース NLP (`kabusys.ai.news_nlp`)
  - raw_news を OpenAI API（デフォルトモデル gpt-4o-mini）でセンチメント化し、銘柄別スコアを ai_scores テーブルへ登録する機能を実装。
  - 処理の主要点:
    - ニュース収集ウィンドウ計算 (`calc_news_window`)：target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して使用）。
    - 記事を銘柄毎に集約し、1 銘柄あたり記事数・文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄ずつを 1 API コールで送信（_BATCH_SIZE）。
    - 429、ネットワークエラー、Timeout、5xx に対して指数バックオフでリトライ（最大リトライ回数あり）。
    - レスポンス検証後、スコアを ±1.0 にクリップし、部分更新（対象コードのみ DELETE→INSERT）で既存スコア保護。
    - API キーは引数または環境変数 `OPENAI_API_KEY` で供給。未設定時は ValueError。

- ツール
  - Paper Trading 検証レポート (`kabusys.tools.paper_verification_report`)
    - コマンドラインから paper trading の検証レポートを生成するスクリプトを追加。
    - デフォルト DB: `data/paper_trading.db`（`PAPER_TRADING_SQLITE_PATH` で上書き可能）。
    - 指標・判定基準:
      - 稼働率 (uptime) >= 99%,
      - 注文成功率 (fill rate) >= 90%,
      - 送信率 (send rate) >= 95%,
      - P95 レイテンシ <= 200 ms
    - P95 計算、各種集計クエリ（system_status / trade_logs / risk_logs）や N/A 考慮、CLI 引数 `--from`, `--to`, `--db` を提供。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 非推奨
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### セキュリティ
- OpenAI API キーの取り扱いは環境変数参照か引数で明示的に渡す方式。キー未設定時は処理を中止して例外を送出し、誤認識での公開を防止。

---

注:
- 多くのモジュールは DuckDB / SQLite の特定テーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, system_status, trade_logs, risk_logs 等）を前提としています。実行前にスキーマとデータ準備が必要です。
- プラットフォーム差異や権限不足によりプロセス優先度や CPU affinity の設定が行えない場合は警告を出力してスキップします。
- デフォルト値や閾値はソースコード内の docstring / 定数に明記しています。必要に応じて環境変数や設定を調整してください。