# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の記法に準拠しています。  

注: 以下はソースコード（src/ 配下）の内容から推測して作成した変更履歴です。実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 全体
  - 初回公開想定の機能群を実装（KabuSys v0.1.0）。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行ランナー / 実行制御
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB から分離。
    - BrokerClientFactory を使ったブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine の起動処理を実装。
    - エンジンは別スレッドで実行し、 data/stop_requested.flag による外部停止制御、data/execution.pid を PID ファイルとして管理。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を組み込み、初期ポートフォリオ値は broker.get_available_cash() から取得。

  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視 DB を統一）。
    - data/stop_requested.flag によりループ停止、KeyboardInterrupt による優雅な終了処理を実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定 / 環境変数管理
  - config.py: Settings クラスを追加。
    - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パーサは `export KEY=val` 形式、クォートあり（エスケープ対応）、クォートなしでのインラインコメント処理などをサポート。
    - 環境変数未設定時に ValueError を投げる `_require()` ユーティリティを提供。
    - 主要設定プロパティを実装: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE チャネル等、DUCKDB / SQLITE パス、PID/kill flag パス、監視閾値 (CPU/MEM/DISK)、環境種別（development/paper_trading/live）とログレベル検証。
    - PAPER_FILL_MODE のバリデーション（"instant"|"partial"|"never"|"reject"）と PAPER_TRADING_SQLITE_PATH をサポート。

- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。
    - コマンドライン引数 `--from` / `--to` / `--db` により期間と DB を指定可能。
    - system_status / trade_logs / risk_logs を集計して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算し、閾値に基づいた PASS/FAIL 判定を出力。
    - P95 算出や日付フィルタ組立て、SQLite の存在確認および OperationalError のフォールバック処理を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選別（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバックし WARNING）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用。既存ポジションからセクター別エクスポージャーを計算し、上限超過セクターの当日新規候補を除外。unknown セクターは上限適用外とする仕様。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（"bull"=1.0, "neutral"=0.7, "bear"=0.3）。未知レジームは警告を出して 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based", "equal", "score"）に応じた株数決定ロジックを実装。
    - risk_based: 損切り率と許容リスク率からベース株数を計算、単元（lot_size）で丸め。
    - equal/score: ウェイトに基づく配分、per-position および aggregated cap の処理、cost_buffer による保守的見積もり、合計が available_cash を超えた場合のスケールダウンと端数再配分ロジックを実装。
    - price 欠損時のスキップやログ出力の取り扱い。
  - portfolio/__init__.py で主要関数のエクスポートを提供。

- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m と MA200 乖離（ma200_dev）を DuckDB の prices_daily を参照して計算。
    - calc_volatility: ATR(20)、相対ATR、20日平均売買代金、出来高比を計算（true_range の NULL 伝播管理、窓サイズチェック）。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS 欠損や 0 は None）。
  - research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト: [1,5,21]）の将来リターンを一括SQLで取得。パラメータ検証あり（horizons は 1〜252 の正整数）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足や分散ゼロ時は None を返す。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - research/__init__.py で主要関数をエクスポートし、zscore_normalize を data.stats から流用。

- AI / ニュース NLP
  - ai/news_nlp.py (部分実装)
    - raw_news → OpenAI (gpt-4o-mini) を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装（設計・定数・ウィンドウ計算など）。
    - 大きな設計方針を実装: トークン肥大化対策（記事数・文字数制限）、バッチ処理（最大 20 銘柄 / コール）、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、結果のクリッピング、部分更新（DELETE + INSERT で対象コードのみ置換）など。
    - calc_news_window: JST ベースのニュースウィンドウ（前日15:00〜当日08:30 JST を UTC に変換）を提供。
    - score_news: API キー解決とウィンドウ計算まで実装。以降の処理はファイル末尾で途中（切断）となっているが、設計に基づく処理フローが定義されている。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows と POSIX (Linux, Darwin, FreeBSD) を吸収し、プラットフォームに応じてプロセス優先度（high/normal/low）を設定。権限不足や未対応 OS の際は警告を出してスキップ。
    - set_cpu_affinity: 指定コア数分だけ CPU affinity を固定するユーティリティを提供。引数検証と例外ハンドリングあり。

### Changed
- .env 自動ロードの挙動を慎重に実装
  - OS 環境変数を保護するため protected セットを利用して .env.local の override を制御。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を用いた自動ロード無効化オプションを提供（テストなどで使用可能）。

- 監視ループの堅牢化
  - MONITOR_POLL_INTERVAL の値が不正（0/負数/非数）の場合は警告を出してデフォルト値（60 秒）にフォールバックする実装を追加。
  - monitor.check_once() 内で発生した例外はループを継続するようキャッチしてログ出力。

### Fixed
- 設計上の安全弁・フェイルセーフ
  - ExecutionEngine 起動前/実行中に data/stop_requested.flag を検知した場合の安全に停止する処理を追加（起動しない・停止要求に応答）。
  - Paper Trading 環境は本番 DB と完全に分離するようパス選択ロジックを修正。

### Notes / Known limitations
- ai/news_nlp.score_news の実装はファイル末尾で途中（切断）になっており、完全動作には続きの実装が必要（記事取得の集約 → OpenAI 送信 → レスポンス処理 → DB 書込の流れ）。
- position_sizing の lot_size は現状全銘柄共通（将来的に銘柄別 lot_map へ拡張する旨の TODO コメントあり）。
- apply_sector_cap は price_map に欠損があるとエクスポージャーを過少見積もる可能性がある（将来的にフォールバック価格導入を検討するコメントあり）。
- DuckDB / SQLite テーブルスキーマや Monitoring / Execution の内部クラス（SystemMonitor, ExecutionEngine 等）の詳細実装は本差分からは推測できるが、別ファイルに依存しているため、結合時の調整やマイグレーションが必要になる場合がある。

---

上記はソースコードの内容から推測してまとめた変更点です。必要であれば、個々のファイルごとの詳細な API 仕様や使用例、残タスク（TODO）リストを別途作成します。どの粒度で追記・分割するか指示してください。