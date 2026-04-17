# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの現状から推測して作成した変更履歴です。

全般的な注記
- 本リリースはパッケージバージョン __version__ = 0.1.0 をベースに作成しています。
- 環境変数や設定ファイル、CLI ユーティリティ、監視/実行ランナー、ポートフォリオ構築、リサーチ用関数群など、運用に必要な主要コンポーネントを含みます。

## [0.1.0] - 2026-04-17

### Added
- 起動・実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV に応じて paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用可能。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンを実行。
    - 停止フラグ (data/stop_requested.flag) と実行 PID ファイル (data/execution.pid) の取り扱いを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はログ警告の上でデフォルトにフォールバック）。
    - 停止フラグ検出時にループ終了、例外捕捉して次ポーリングへ継続。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する仕様。

- 設定管理とウィザード
  - config.py
    - .env 自動読み込み機能（プロジェクトルートが見つかった場合に .env, .env.local を読み込む）。
    - .env の行パーサ（引用符・エスケープ、コメント処理などに対応）。
    - Settings クラスで環境変数をラップ（各種パス、しきい値、Paper Trading 用設定、ログレベル、実行環境判定等）。
    - 環境変数未設定時に明示的なエラーを投げる _require() を提供。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを生成・更新。
    - 各設定項目の説明、デフォルト・選択肢の提示、シークレット表示（マスク）に対応。
    - .env の読み取り／書き込みヘルパを実装。

- 設定検証ツール
  - validate_config.py
    - .env と config/*.yaml の事前チェック CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、YAML のパースチェック（PyYAML が存在する場合）。
    - 本番環境（KABUSYS_ENV=live）向けの追加注意チェック（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等）。
    - --strict フラグで警告もエラー扱いにできる。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重の重み計算。全スコアが 0 の場合は等分配にフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: 同一セクターの既存保有比率に基づく新規候補の除外ロジックを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金の乗数を返す（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - portfolio.position_sizing
    - calc_position_sizes: 重み・候補・ポートフォリオ情報から発注株数を算出。risk_based / equal / score の割当方式に対応。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap、コストバッファ（手数料・スリッページ想定）を考慮したスケーリングと残差配分ロジックを実装。

- リサーチ／ファクター計算
  - research.factor_research
    - DuckDB を用いたファクター計算関数群を追加（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算するための骨格実装（スキャン窓や NULL ハンドリングに配慮）。

- ユーティリティ
  - utils.process_priority
    - プロセス優先度（nice / Windows priority）と CPU affinity 設定のクロスプラットフォーム対応ユーティリティを追加。
    - 標準的なレベル ("high" / "normal" / "low") をサポート。権限不足等の失敗時は警告ログでスキップする。

- その他ツール
  - tools.paper_verification_report.py
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、リスク却下数、レイテンシ指標（avg/max/P95）を集計して検証レポートを生成する CLI ツールを追加。
    - デフォルト基準値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を出力。
    - --from/--to/--db オプションで期間・DB パスを指定可能。

### Changed
- .env 読み込みの取り扱いを明確化
  - OS 環境変数を保護するための protected キーセット機構を導入し、.env.local は .env よりも優先して読み込み（ただし OS 環境変数は上書きされない）。
- DB 接続の動作
  - run_monitoring は常に（環境に依らず）monitoring 用の sqlite_path（Settings.sqlite_path）を使用するよう明確化。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離。

### Fixed
- 環境変数解析まわりの堅牢性向上
  - _parse_env_line においてクォート内のエスケープ処理、インラインコメントの扱い、export プレフィックス対応などを実装し、さまざまな .env 記述を正しくパース可能にした。
- ポートフォリオ計算の端数処理・スケールロジックの安全弁を追加
  - aggregate スケーリング後の残余資金で lot_size 単位での追加配分を行う際に最大許容数をチェックすることで過剰発注を防止。

### Security
- .env ファイルは生成時に「絶対に Git にコミットしないこと」旨の警告を .env ヘッダに明記。

### Known issues / Notes
- research.calc_volatility の SQL 実装は途中で切れている（true_range 集計以降の窓集計部分が続く想定）。実装完了時には ATR の NULL 伝播・行数チェックを含む集計が必要。
- position_sizing の price が欠損（0.0）の場合、現状はスキップするがエクスポージャーが過少評価されるリスクがある旨の TODO コメントが存在する。将来的なフォールバック価格の導入を検討。
- process_priority の設定は権限や OS に依存するため、実行環境によっては警告ログが出力される。

---

今後の予定（推測）
- research モジュールの各ファクター計算（Value, Liquidity 等）の実装完了。
- ExecutionEngine / SystemMonitor の詳細実装・テストおよび異常時のリカバリ強化。
- 単体テストの追加と CI 設定、ならびにドキュメント（PortfolioConstruction.md, StrategyModel.md 等）の参照サンプル整備。

（この CHANGELOG はソースコードの現状から推測して作成しています。実際の変更履歴管理には各コミット・タグに基づく記録を併用してください。）