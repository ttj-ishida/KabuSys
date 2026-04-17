# Changelog

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

### Added
- 初回リリース。KabuSys のコアモジュール群を追加。
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 監視処理は常に本番の sqlite_path を使用して監視テーブルを初期化する（init_monitoring_db の呼び出し）。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループ終了。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を使用）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の別スレッド実行、停止フラグ検知と安全停止処理を実装。
    - エンジンの PID ファイル（data/execution.pid）を扱う設定を追加。

- 設定 / 環境変数管理（kabusys.config）
  - Settings クラスを導入し、環境変数経由で各種設定を取得する API を提供。
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - OS 環境変数は保護され、.env.local の override 時も上書きされない。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - 各種プロパティを実装（J-Quants / kabu API / LINE / DB パス / 監視しきい値 / システム設定 など）。
  - 入力検証を追加:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL は標準のログレベルのみ許容。
    - PAPER_FILL_MODE の有効値検査（instant / partial / never / reject）。
    - 必須環境変数未設定時は ValueError を送出する _require() を提供。

- ポートフォリオ構築ユーティリティ（kabusys.portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank）でソートして上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア重み付けを実装（全スコアが 0 の場合は等配分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中の上限チェック。既存ポジションをもとに上限超過セクターの新規候補を除外。
      - "unknown" セクターは上限適用対象外。
      - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能。
      - 既存ポジションの価格欠損に関する注意と TODO を記載。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: 発注株数を計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、投下上限（max_utilization）、手数料・スリッページの見積り（cost_buffer）を考慮。
    - aggregate cap 超過時はスケールダウンして残余キャッシュで端数ロットを順次配分するアルゴリズムを実装。
    - 将来的な拡張（銘柄別 lot_size マップ）について注記。

- 研究 / リサーチモジュール（kabusys.research）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 各関数は windows / 欠損時の振る舞い（必要行数未満は None）を明示。
  - feature_exploration.py
    - calc_forward_returns: 将来リターン（複数ホライズン）を計算。ホライズン検証（1〜252）を実施。
    - calc_ic / rank / factor_summary: IC（Spearman ランク相関）、ランク付け、ファクター統計サマリを実装（外部ライブラリに依存せず純 Python）。
  - research パッケージ __all__ を整備（zscore_normalize の再輸出含む）。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows / POSIX の差を吸収、psutil を利用）。
    - set_cpu_affinity(cpu_count) を実装。権限不足や未対応環境では安全にスキップして警告ログ出力。
    - 互換性のためのフォールバックと例外ハンドリングを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し PASS/FAIL を判定するレポートを標準出力に出力。
    - デフォルト DB path は data/paper_trading.db。--db/環境変数で上書き可。
    - P95 計算、日付フィルタ、欠損テーブルの扱い（OperationalError を捕捉して N/A 扱い）を実装。
    - 判定基準（閾値）をコード内定数で定義（稼働率 99% など）。

- ニュース NLP（AI）
  - ai/news_nlp.py を追加（ニュース記事を OpenAI API でスコアリングし ai_scores に書き込む設計）。
    - gpt-4o-mini を想定、最大バッチサイズ 20、1 銘柄あたり記事/文字数上限を設ける。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - score_news により API キー解決（引数または OPENAI_API_KEY 環境変数）を行い、エラー時は ValueError を送出。
    - バッチ送信、429/ネットワーク/5xx に対する指数バックオフリトライ、レスポンス検証、スコアの ±1.0 クリッピング、部分更新（対象コードのみ DELETE→INSERT）などを設計上の仕様として実装予定。
    - 出力は厳密な JSON（{"results":[...]}）を期待するプロンプト設計。
    - （注）現時点のスナップショットでは score_news の記事取得部分が途中で切れており、完全実装は未完。

- パッケージ情報
  - パッケージのバージョンを __version__ = "0.1.0" として設定。
  - パッケージ __all__ に主要サブパッケージを列挙。

### Changed
- N/A（初回公開のため既存からの変更はなし）

### Fixed
- N/A（初回公開のためバグ修正履歴はなし）

### Removed
- N/A

### Known issues / Notes
- ai/news_nlp.score_news の実装はスナップショット上で途中（記事集約処理呼び出し直後に切れている）。実運用前に完全実装とテストが必要。
- risk_adjustment.apply_sector_cap は price_map における価格欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨を注記しており、将来的に前日終値等のフォールバック価格を導入することが推奨される。
- position_sizing の将来的な拡張点（銘柄別 lot_size マップ）を TODO として残している。
- set_process_priority / set_cpu_affinity は権限不足や未サポート OS の場合に機能しないことがある（その場合は警告ログを出してスキップ）。
- .env 自動ロードはプロジェクトルート検出に依存するため、配布環境によっては自動ロードがスキップされる可能性がある（その場合は環境変数を明示的に設定すること）。

---

作業履歴や追加要望があれば、どの箇所をより詳しく CHANGELOG に反映するか指示してください。