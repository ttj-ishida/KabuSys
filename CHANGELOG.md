# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

※ 本 CHANGELOG はソースコードから推測して作成しています。

## [Unreleased]

### 追加予定 / TODO
- position_sizing: 銘柄ごとの lot_size（単元）を stocks マスタなどから取得する拡張の検討（コード内に TODO）。
- risk_adjustment: price が欠損（0.0）の場合のフォールバック（前日終値や取得原価など）対応の検討（コード内に TODO）。

---

## [0.1.0] - 2026-04-13

初回リリース — 基本機能一式を追加。

### 追加
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 環境設定（kabusys.config）
  - Settings クラスを実装し、環境変数経由で各種設定（API トークン、DB パス、監視閾値、実行環境フラグ等）を取得。
  - .env 自動読み込み機能を実装（プロジェクトルートの .git または pyproject.toml を探索し .env/.env.local を読み込み）。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - OS 環境変数を保護するための上書きポリシー（protected set）を導入。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - `KABUSYS_ENV` と `LOG_LEVEL` の検証、および `PAPER_FILL_MODE` の検証ロジックを追加。

- プロセス実行ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム非依存でプロセス優先度を設定する `set_process_priority(level)` を実装（Windows / POSIX に対応、psutil 利用）。
  - CPU affinity を設定する `set_cpu_affinity(cpu_count)` を実装。
  - 権限不足や非対応プラットフォーム時はログ警告でフォールバック。

- 実行系エントリースクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境に関わらず本番用 sqlite_path を使用。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 SQLite DB を使用し、本番 DB と完全に分離（`PAPER_TRADING_SQLITE_PATH`）。
    - BrokerClientFactory を介してブローカークライアントを生成（paper_trading では Mock を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 起動時にプロセス優先度を "high" に設定。

- 監視 DB 初期化
  - `init_monitoring_db` を run 系スクリプトで呼び出して監視テーブルの存在を保証（冪等な初期化）。

- DuckDB 統合
  - 各種研究・AI モジュールで DuckDB 接続を使用してデータ（prices_daily / raw_financials / raw_news など）を参照。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - シグナル選定 `select_candidates`（スコア降順、タイブレークに signal_rank）。
    - 等重配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコア 0 の場合は等重にフォールバックし警告）。
  - risk_adjustment:
    - セクター集中制限を適用する `apply_sector_cap`（既存保有のセクターエクスポージャを計算し上限超過セクターの新規候補を除外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear 対応、未知レジームは警告の上 1.0 でフォールバック）。
  - position_sizing:
    - `calc_position_sizes` を実装。allocation_method（"risk_based" / "equal" / "score"）に対応。
    - 単元株（lot_size）で切り捨て・丸め、per-position 上限、aggregate cap（available_cash 超過時のスケーリング）、cost_buffer（手数料・スリッページ保守見積）を組み込み。
    - aggregate スケーリング時の端数配分ロジック（fractional remainder）を実装し、残余キャッシュで lot 単位を再配分。

- 研究（kabusys.research）
  - factor_research:
    - `calc_momentum`: 1M/3M/6M リターン・MA200 乖離等を計算。
    - `calc_volatility`: ATR20、ATR/close、20日平均売買代金、出来高比率を計算。
    - `calc_value`: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - 各ファンクションは DuckDB 接続を受け取り SQL により実行。
  - feature_exploration:
    - `calc_forward_returns`: 指定したホライズンの将来リターンを一括で取得。
    - `calc_ic`: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 未満は None）。
    - `rank` / `factor_summary`: ランク関数、基本統計量集計（count/mean/std/min/max/median）を提供。
  - 研究用 API は外部 API に依存せず、DuckDB の prices_daily/raw_financials のみ参照する設計。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出し、ai_scores テーブルへ書き込み。
  - バッチ処理（最大 20 銘柄/コール）、記事数/文字数トリム（最大記事数・最大文字数制限）によるトークン肥大化対策を実装。
  - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
  - レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時に他銘柄スコアを保護するための差分置換（DELETE → INSERT）を採用。
  - news ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）ユーティリティを提供。
  - OpenAI API キー未設定時はエラーを投げる、またはスキップ挙動で堅牢に動作する設計。

- ツール（kabusys.tools）
  - paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - レポート内容: システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）など。
    - フィルタは --from / --to / --db オプションで指定可能。環境変数 `PAPER_TRADING_SQLITE_PATH` も参照。
    - PASS/FAIL の基準値（稼働率 99%, 成功率 90% 等）を定義し判定を行う。
    - レイテンシ P95 計算のために全値取得および P95 算出実装。

### 変更
- なし（初回リリースのため新規追加が中心）。

### 修正 / 既知の注意点
- env パーサの実装により .env の柔軟な記述に対応。ただし極端に複雑な .env 構成では期待動作しない可能性あり。
- process_priority / cpu_affinity は権限やプラットフォームに依存するため、失敗時はログ警告でスキップする実装。
- portfolio.risk_adjustment のセクターエクスポージャ計算では price が 0.0 の場合に過少認識される可能性があり、将来的にフォールバック価格導入を想定（コード中に TODO）。
- DuckDB の executemany に関する挙動に注意（空パラメータでの実行回避ロジックを考慮）。

### セキュリティ
- API キー等の秘匿情報は環境変数で管理する設計。`.env` 自動読み込みは無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。

---

（以降のリリースはここに追記してください）