KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-13
初回公開リリース。以下の主要機能・モジュールを実装しています。

### 追加
- コア
  - パッケージ初期化: kabusys パッケージ本体をバージョン "0.1.0" として公開。
  - DuckDB / SQLite を用いたローカルデータ処理・監視基盤を整備。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI エントリポイントを提供。
    - 環境に応じて paper_trading 用 DB を分離（KABUSYS_ENV=paper_trading 時は data/paper_trading.db を使用）。
    - ブローカークライアントは BrokerClientFactory 経由で生成（paper_trading 時は MockBrokerClient を想定）。
    - ExecutionEngine 起動前に監視テーブルの初期化を行う（init_monitoring_db）。
    - プロセス優先度を High に設定するユーティリティ呼び出し（set_process_priority）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動用スクリプトを提供。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL により上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV に関係なく本番 sqlite_path を使用して DB を初期化・接続。
    - プロセス優先度設定・リソースクリーンアップ（DB close）を含む。

- 環境設定 / ロード
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサ実装: export 形式やクォート内のエスケープ、行末コメント取り扱いに対応。
    - 各種設定プロパティを提供（DB パス、PID ファイル、閾値、環境判定、paper_trading のパス・fill mode 等）。
    - 設定値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）を実装。

- モニタリング
  - monitoring_db 初期化ユーティリティ（init_monitoring_db を使用する前提で実装）。
  - SystemMonitor を利用したポーリング運用（run_monitoring から呼び出し）。

- Execution / 注文管理
  - ExecutionEngine および関連コンポーネント（OrderRepository, OrderManager, Reconciler, RiskManager 等）を組み立ててセッションを実行する流れを実装（run_execution で利用）。
  - RiskConfig のデフォルト値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を設定し、初期ポートフォリオ値をブローカーの get_available_cash() から取得。

- ポートフォリオ構築（純関数群）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートして上位 N を選別。
    - calc_equal_weights / calc_score_weights: 等分配およびスコア加重配分。スコア合計が 0 の場合は等分配にフォールバック（警告ログ）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中上限を判定し新規候補を除外。売却予定銘柄を露出計算から除外可能。unknown セクターは上限適用外。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた資金乗数を返す。未知レジームは警告のうえ 1.0 でフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に基づく発注株数計算を実装。
    - 単位は lot_size（デフォルト 100）。risk_based ロジックでは stop_loss_pct と risk_pct に基づく算出。
    - aggregate cap（利用可能現金を超える場合のスケーリング）やスケールダウン後の余剰配分（lot 単位での再配分）を実装。
    - 手数料・スリッページ見積りに対応する cost_buffer パラメータを考慮。

- 研究 / ファクター計算
  - research.factor_research
    - calc_momentum: 1M/3M/6M リターン及び MA200 乖離率を計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - DuckDB を使用して prices_daily / raw_financials を効率的にスキャン。
  - research.feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを計算（horizons の検証あり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。サンプル数不足時は None。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）を提供。
  - research.__init__ で zscore_normalize（data.stats 由来）をエクスポート。

- AI / ニュース NLP
  - ai.news_nlp
    - raw_news と news_symbols を銘柄単位で集約し、OpenAI (gpt-4o-mini) に対してバッチでセンチメント分析を実行。
    - 入力トークン肥大化対策（1銘柄あたり最大記事数 / 文字数制限）。
    - バッチ処理（最大 20 銘柄/コール）、429/ネットワーク/5xx に対する指数バックオフリトライを実装。
    - レスポンス検証（JSON mode、results キー、型チェック）。スコアは ±1.0 にクリップ。
    - タイムウィンドウ: target_date 前日 15:00 JST 〜 当日 08:30 JST（UTC で変換）。
    - ai_scores テーブルへの置換書き込みは対象コードのみを削除してから挿入することで部分失敗時の保護を行う設計。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。

- ツール
  - tools.paper_verification_report.py
    - Paper Trading の検証レポート生成 CLI を提供（--from/--to/--db オプション対応）。
    - 指標: 稼働率 (uptime), 注文成功率(fill rate), 送信率(send rate), P95 レイテンシなど。
    - 基準値（PASS/FAIL 判定）を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200ms）。
    - DB が存在しない場合のメッセージ出力や、テーブル欠損時のフォールバック（N/A）に対応。

- ユーティリティ
  - utils.process_priority
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を指定コア数に固定する set_cpu_affinity を提供。アクセス拒否等は警告で回避。
    - 設定失敗時は安全にスキップしてログ出力。入力検証あり。

### 注記 / 既知の制限
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされる（パッケージ配布後の安全策）。
- risk_adjustment.apply_sector_cap: price_map に 0.0 が含まれるとエクスポージャーが過小見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO コメントあり。
- position_sizing.calc_position_sizes: 現状 lot_size は全銘柄共通で固定。将来的な拡張（銘柄別 lot_map）について TODO を記載。
- ai.news_nlp: API レスポンスの部分失敗時や外部サービス障害時はフェイルセーフとしてスキップ・継続する設計。ただし完全性は保証されない。
- research モジュールは DuckDB のテーブル（prices_daily, raw_financials）に依存。実データがない場合は空の結果や None を返す。

### 開発メモ / 将来の改善候補
- position_sizing: lot_size を銘柄別に扱う拡張、価格フォールバックロジック追加。
- news_nlp: OpenAI クライアントの細かなエラー分類やメトリクス（API レイテンシ、トークン使用量等）の計測追加。
- モニタリングの運用面: MONITOR_POLL_INTERVAL の動的変更やより高度なバックオフ実装など。

## 参考: 主要な環境変数（デフォルト値）
- KABUSYS_ENV : development | paper_trading | live（default: development）
- SQLITE_PATH : data/monitoring.db
- DUCKDB_PATH : data/kabusys.duckdb
- PAPER_TRADING_SQLITE_PATH : data/paper_trading.db
- PAPER_FILL_MODE : instant | partial | never | reject（default: instant）
- MONITOR_POLL_INTERVAL : 監視ポーリング間隔（秒、default: 60）
- OPENAI_API_KEY : OpenAI API キー
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL / CPU/MEM/DISK 閾値 等（一部は config.py で定義）

---
もし CHANGELOG に追記してほしい点（個々のコミットの差分やリリース日精査、特定の機能詳細の補足など）があれば教えてください。