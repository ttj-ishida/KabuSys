# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

注: コードベースから推測して作成しています。実装意図や内部設計に基づく記述を含みます。

## [0.1.0] - 2026-04-17

### Added
- 初期リリース: KabuSys の基盤機能を追加。
- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込み。プロジェクトルートは .git / pyproject.toml を探索して特定するため、CWD に依存しない。
  - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境など）。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を行い、不正な値は例外を送出。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- .env パーサ改善
  - `export KEY=val` 形式対応、クォート値（シングル/ダブル、バックスラッシュエスケープ）対応、インラインコメントの取り扱い改善。
  - .env の読み込みで OS 環境変数を保護する機構（protected）を提供。
- 環境設定ウィザード CLI (kabusys.config_setup)
  - 対話式で .env を作成 / 更新するウィザードを追加。
  - デフォルト値、選択肢の提示、シークレット入力のマスク表示、保存確認、`--env-file` 指定をサポート。
  - 生成される .env にはヘッダコメント（Git にコミットしない旨）を含めるテンプレート出力。
- 設定検証 CLI (kabusys.validate_config)
  - 起動前に必須環境変数や設定ファイル（config/*.yaml）、DB パスなどを検査する CLI を追加。
  - `--strict` モード（警告も失敗扱い）をサポート。
  - 本番 guard（KABUSYS_ENV=live）時の追加チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定など）。
- 実行 / 監視用起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - プロセス優先度を起動直後に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用（モニタリング専用設計）。
    - DuckDB 接続・監視 DB 初期化・例外ハンドリング・停止フラグ監視を実装。
- モニタリング DB 初期化ユーティリティを呼び出す箇所を追加（冪等に監視テーブルを保証）。
- ツール類
  - tools/paper_verification_report.py: ペーパートレード結果検証用レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均 / 最大 / P95）を集計。
    - 閾値に基づく PASS/FAIL 判定、日付フィルタ、DB パス指定（env または --db）をサポート。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: シグナルをスコア降順で選定（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づく候補フィルタリング（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元株（lot）丸め、最大ポジション比率上限、aggregate cap によるスケーリング（端数処理で残差を考慮）。
    - cost_buffer による手数料等の保守的見積りを考慮。
- 研究用ファクター計算 (kabusys.research.factor_research)
  - DuckDB を用いたモメンタム / ボラティリティ / 流動性等のファクター計算機能を追加。
  - SQL ウィンドウ関数を使った期間ベースの計算（MA200, ATR20, 各種リターン等）。
- ユーティリティ
  - utils.process_priority: psutil を使ってクロスプラットフォームにプロセス優先度設定（Windows / POSIX）と CPU affinity 設定を提供。権限不足時は警告を出して安全にスキップ。

### Changed
- 設定読み込み順序を明確化: OS 環境変数 > .env.local > .env（.env.local は上書き可能）。
- .env 読み込み時に OS 環境変数を保護（既存値は上書きしない、override フラグで制御）。

### Fixed / Improved
- .env パーサの堅牢性向上（export プレフィックス、引用符内のエスケープ、インラインコメント処理）。
- config_setup ウィザードでシークレットはマスクして表示するように改善（画面表示上の露出を低減）。
- run_monitoring の MONITOR_POLL_INTERVAL に不正値が設定された場合に警告を出し、デフォルト値にフォールバックする挙動を追加（time.sleep に負の値を渡して例外になるのを防止）。
- ExecutionEngine 起動時の paper_trading 分離により、本番データとペーパートレードデータを分離（DB の偶発的書き換えを防止）。
- process_priority の例外ハンドリングを追加して、権限がない環境でも起動を継続できるように改善。

### Security
- ウィザードのプレビューでシークレット値を "****" でマスク表示。
- .env 自動ロード時に OS の既存環境変数を保護する仕組みを導入（意図しない上書きを防止）。

### Notes
- 監視プロセスはプロダクション用の sqlite_path を参照する設計（KABUSYS_ENV に依存しない）。意図的な設計のため注意して運用すること。
- 停止操作はプロジェクトルートの data/stop_requested.flag（および PID ファイル）を用いて行う想定。
- paper_verification_report の閾値（稼働率、成功率、レイテンシ等）はソース内定数で定義されており、運用環境に応じて調整が可能。

------------------------------------------------------------
今後のリリースでは、以下の改善が考えられます（実装予定/検討項目の例）:
- 個別銘柄ごとの lot_size を銘柄マスタから参照可能にする拡張。
- position_sizing の価格フォールバック（前日終値や平均取得原価）導入。
- ファクター計算のユニットテスト追加および計算結果の安定化。
- 運用向けに監視アラート（LINE 通知など）の自動化・閾値外通知の充実。

