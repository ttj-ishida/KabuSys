# CHANGELOG

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
フォーマット: 変更はセマンティックに "Added / Changed / Fixed / Removed / Security" に分類しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプト
  - SystemMonitor のポーリングループ起動用スクリプトを追加。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグファイル (data/stop_requested.flag) を検知してループを終了。
  - 起動時にプロセス優先度を設定するフックを呼び出し。

- run_execution 起動スクリプト
  - ExecutionEngine を起動するスクリプトを追加。
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB（data/paper_trading.db がデフォルト）を使用して本番 DB と分離。
  - BrokerClientFactory を利用したブローカークライアントの抽象化。
  - ExecutionEngine をデーモンスレッドで実行し、停止フラグ (data/stop_requested.flag) による安全停止を実装。
  - PID ファイルの取り扱いをサポート（data/execution.pid）。

- 設定管理（kabusys.config）
  - .env/.env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - export 形式やクォート付き値、インラインコメント等に対応する .env パーサを実装。
  - 環境変数取得用 Settings クラスを追加。J-Quants / kabu / LINE / DB / 監視閾値等のプロパティを提供。
  - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH など paper_trading 関連の設定を追加。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
  - 重み計算: calc_equal_weights, calc_score_weights（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - リスク調整: apply_sector_cap（セクター集中の上限チェック、売却予定コードの除外対応）と calc_regime_multiplier（market レジームに基づく資金乗数）。
  - ポジションサイズ計算: calc_position_sizes（risk_based / equal / score の配分方式、lot_size 単位の切り捨て、aggregate cap によるスケールダウン、コストバッファ考慮）。

- 研究・ファクター計算（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け prices_daily / raw_financials を参照）。
  - 将来リターン / IC / 統計: calc_forward_returns, calc_ic, factor_summary, rank。
  - DuckDB を用いた SQL + Python 実装により外部 API に依存しない設計。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄別に記事を集約し OpenAI (gpt-4o-mini) でセンチメントスコアを生成して ai_scores に書き込む処理を実装（バッチ化、トークン肥大対策、スコアクリップ、リトライ戦略など）。
  - ニュース収集ウィンドウ（JST ベース）計算ユーティリティを追加。
  - API キーの明示・環境変数 (OPENAI_API_KEY) の検出をサポート。
  - フェイルセーフ設計: API 失敗時は部分スキップして継続、書き込みは対象コードを限定して既存データ保護。

- ツール
  - paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - DB が存在しない場合やテーブルが欠けている場合にエラーハンドリングして N/A 扱いにする。
    - コマンドライン引数 --from/--to/--db をサポート。

- ユーティリティ（kabusys.utils）
  - process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) で high/normal/low を設定（アクセス権限がない場合は警告してスキップ）。
    - set_cpu_affinity(cpu_count) でプロセスを先頭 N コアにピン留め（未指定はスキップ）。
  - 例外や未対応 OS に対する耐性を実装。

- パッケージ初期化
  - kabusys.__init__ にバージョン情報 (__version__ = "0.1.0") と主要サブパッケージの __all__ を設定。
  - research と portfolio のトップレベルエクスポートを整備。

### Changed
- データベース扱い
  - 監視系（monitoring）は KABUSYS_ENV に依存せず本番 sqlite_path を使用する方針を明確化（run_monitoring）。
  - run_execution は paper_trading 時に専用 DB を使用して本番との完全分離を担保。

### Fixed
- .env パーサの堅牢化
  - 引用符・エスケープ・コメント処理に対応。OS 環境変数を protected として .env.local による上書きを制御。

### Known issues / TODO
- apply_sector_cap: price_map に 0.0 が混入した場合にエクスポージャーが過小評価される可能性があり、前日終値や取得原価のフォールバックを将来追加予定（TODO コメントあり）。
- calc_position_sizes:
  - lot_size を全銘柄共通で扱う設計。将来的には銘柄別 lot_size を導入する予定（TODO コメントあり）。
- news_nlp:
  - API 呼び出し周りはリトライ・検証・部分書き換えの設計があるが、実行上の細かい例外パターンやレスポンス検証ロジックは今後さらに強化が望まれる。
- run_monitoring/run_execution はプロセス優先度設定や PID/STOP フラグに依存するため、コンテナ環境や権限のない環境では警告を出してスキップする挙動になっている点に注意。

---

## [0.1.0] - 2026-04-16

初回リリース。本バージョンで実装された主要機能を記載します。

### Added
- コア実行コンポーネント
  - ExecutionEngine 起動スクリプト (run_execution)
  - SystemMonitor 起動スクリプト (run_monitoring)
- 設定管理（Settings クラス）と .env 自動ロード
- ポートフォリオ構築ライブラリ
  - 候補選定、重み算出、ポジションサイズ計算、セクターキャップ、レジーム乗数
- 研究（Research）機能
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- AI ニューススコアリングモジュール（OpenAI 経由）
  - ニュース集計→API バッチ処理→スコア書き込みフロー
- ツール
  - Paper Trading 検証レポート生成 (paper_verification_report)
- ユーティリティ
  - プロセス優先度・CPU affinity 制御ユーティリティ

### Changed
- パッケージ初期化にバージョン番号を追加（__version__ = "0.1.0"）。
- Monitoring は環境に依存せず本番 sqlite DB を参照する仕様に。

### Fixed
- .env ファイル読み込みの互換性向上（export キーワード、クォート/エスケープ/コメントの扱い）。

---

これまでの履歴は可能な限りコードベースから推測して記載しています。実際のリリースノートに合わせて日付や影響範囲（Breaking Changes など）を追記・調整してください。