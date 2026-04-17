# CHANGELOG

すべての注目すべき変更を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。

最新の変更は常に一番上にあります。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンとして kabusys v0.1.0 を追加。
  - settings インスタンスを通じた環境変数ベースの設定管理を導入（.env/.env.local の自動ロード機構を含む）。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数を保護する仕組み（protected keys）を導入。
  - 各種設定プロパティ（DB パス、API トークン、監視閾値、ログレベル、env 判定など）を提供。
  - 環境変数の構文解析はクォート・エスケープ・インラインコメント・export 形式に対応。

- 実行関連
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV により paper_trading 実行時は paper_trading 専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じたブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による安全な停止処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 監視関連
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（monitoring 用 DB 初期化処理を含む）。
    - 停止フラグ検知・例外発生時のログ出力・接続クローズを安全に行う。
    - 起動時にプロセス優先度を "high" に設定。

- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム非依存でのプロセス優先度設定（Windows, POSIX を吸収）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加。
    - アクセス権限不足などのケースをログで扱いスキップするフェイルセーフ実装。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順（同点は signal_rank）で候補選択。
    - calc_equal_weights, calc_score_weights: 等配分およびスコア加重配分（全スコアが0の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を評価し、上限超過セクターの新規候補を除外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値は警告のうえ 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元（lot_size）、手数料・スリッページ見積り（cost_buffer）、ポジション上限・aggregate cap、スケーリングおよび残差分配ロジックを実装。

- リサーチ（DuckDB を用いたファクター計算）
  - research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（target_date 以前の最新財務レコードを参照）。
    - DuckDB の SQL ウィンドウ関数を活用し、データ不足時は None を返す設計。
  - research/feature_exploration.py:
    - calc_forward_returns: 指定 horizon に対する将来リターンを一括取得（horizons の妥当性チェックを実施）。
    - calc_ic: スピアマンランク相関（IC）を計算。データ不足・ゼロ分散時は None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と統計サマリー機能を実装。
  - research/__init__.py で主要 API を公開（zscore_normalize は data.stats から再エクスポート）。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（gpt-4o-mini）でセンチメントスコア化し、ai_scores テーブルへ保存する設計を追加。
    - タイムウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）機能を提供（calc_news_window）。
    - バッチ処理（1 回の API 呼び出しあたり最大 20 銘柄）、トークン肥大化対策（1 銘柄あたり記事数・文字数制限）、429/ネットワーク/5xx に対する指数バックオフとリトライロジック、レスポンスのスキーマ検証、スコアの ±1.0 クリップ、部分成功時の部分更新戦略を想定した設計ドキュメントを実装。
    - OpenAI API キー解決と未設定時の ValueError を実装。
    - （注）ファイル末尾で記事取得処理が途中で切れている箇所があり、完全な実装は未完です（実行時には該当部分の実装完了が必要）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成 CLI を追加（--from/--to/--db オプション対応）。
    - 検証指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を算出し、閾値による PASS/FAIL 判定を出力。
    - DB 存在チェック、SQL の OperationalError によるフォールバック対応を実装。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

### 注意事項 / 補足
- run_monitoring は監視用テーブルを初期化する際に本番 sqlite_path を使用します。監視データは環境に依存せず本番 DB を参照する設計になっています（意図的な分離）。
- run_execution は paper_trading 環境時に paper_trading 専用 DB を使用し本番と分離します。paper_trading の挙動は Settings.paper_fill_mode の値に依存します（"instant" / "partial" / "never" / "reject" を検証）。
- process_priority の設定は OS に依存するため、権限がない場合や未対応プラットフォームでは警告ログを出してスキップします。
- ai/news_nlp.py に関しては記事集約部分の実装が途中で切れているため、実行可能状態にするには該当箇所の完成が必要です。

---

（この CHANGELOG はコードベースの現状から機能と設計意図を推測して作成しています。実際のコミット履歴やリリースノートがある場合はそちらに合わせて更新してください。）