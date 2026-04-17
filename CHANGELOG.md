# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

## [Unreleased]

- ドキュメント・テスト向けに内部ロジックや挙動の微修正が行われる可能性があります（詳細はコミット履歴参照）。

---

## [0.1.0] - 2026-04-17

初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群と CLI ツール群を含みます。

### Added
- 実行スクリプト / CLI
  - run_execution.py: ExecutionEngine を起動するためのエントリポイント。  
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db 等）に完全分離して記録する。
    - 起動時にプロセス優先度を "high" に設定し、停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するためのスクリプト。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI。必須環境変数未設定や本番運用時の注意などを検出。
  - config_setup.py: 対話式 .env ウィザード。既存値の読み込み、シークレットのマスク表示、生成ファイルの安全注意喚起を実装。
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツール。稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出して PASS/FAIL を判定できる。

- 設定・環境管理
  - config.py: 環境変数ラッパー Settings を提供。多くの設定プロパティを明示化（DBパス、PID/kill フラグパス、閾値、paper_trading 関連設定など）。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。  
    - 読み込み順: OS 環境 > .env > .env.local（.env.local は上書き）。  
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パースの強化: export プレフィックス対応、クォート文字内のバックスラッシュエスケープ処理、インラインコメント処理の改善。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（スコア降順 + タイブレーク）、等金額配分・スコア加重配分を実装。
  - portfolio.position_sizing: 複数の配分方式（risk_based / equal / score）に対応した株数計算。  
    - 単元株（lot_size）丸め、最大ポジション上限、投下資金の aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。
  - portfolio.risk_adjustment: セクター別集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。

- リサーチ
  - research.factor_research: DuckDB 上の prices_daily / raw_financials を参照してファクター（モメンタム、MA200乖離、ATR、出来高・出来高比等）を計算する関数群を提供。大規模データを SQL + Python で処理する設計。

- ユーティリティ
  - utils.process_priority: Windows / POSIX の差を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定を実装。権限不足等の例外はログで警告して安全にフォールバックする。

- DB 初期化/監視連携
  - monitoring_db 初期化呼び出しを各起動スクリプト（monitoring / execution）に追加。監視テーブルの存在を冪等に保証。

- Risk / Execution 周辺
  - Execution 側での依存組み立て（OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）の初期構築を実装。RiskManager のデフォルト構成値を定義（最大ポジション比率、利用率上限、レートリミット等）。
  - ExecutionEngine は別スレッドで session を実行し、停止フラグ検知で安全停止する。

- Paper Trading レポートの判定基準
  - 稼働率、注文成功率、送信率、P95 レイテンシなどの閾値を定義（例: 稼働率 >= 99%、P95 <= 200ms など）し、FAIL の場合は原因を出力する。

### Changed
- 監視挙動
  - run_monitoring は KABUSYS_ENV にかかわらず常に本番用 sqlite_path（Settings.sqlite_path）を使って監視データを保存する仕様（意図的な設計）。
- .env 処理
  - .env の読み込みポリシーを明確化（OS 環境を保護する protected set を導入）。.env.local は .env 上書きとして扱う。

### Fixed
- .env パーサーの堅牢化
  - クォートありの値でのバックスラッシュエスケープや閉じクォートの検出、クォートなし値におけるインラインコメント認識を修正し、より現実的な .env の記述に対応。
- Paper 検証レポートの堅牢化
  - DB に該当テーブルがない場合でも sqlite3.OperationalError を捕捉してレポート生成を続行するように変更（部分データでも出力可能に）。

### Security
- config_setup が生成する .env に対して「絶対に Git にコミットしないこと」の注意書きを追加。
- 必須トークン（J-Quants / kabu API パスワード）を Settings で強制チェックし、未設定時は明確にエラーを送出。

### Documentation
- 各モジュールに docstring を追加し、設計意図・引数・戻り値の説明を明示。
- config_setup と validate_config に使い方と注意点を明記。

### Notes / Known limitations
- position_sizing の lot_size は現在全銘柄共通（将来的に銘柄別単元対応を想定した TODO を記載）。
- apply_sector_cap は price_map に価格が欠損（0.0）の場合にエクスポージャーを過小評価する可能性があり、フォールバック価格（前日終値等）を将来的に検討する旨をコメントに記載。
- process_priority / cpu_affinity は権限不足や未対応プラットフォームで安全にスキップされる。

---

今後のリリースで想定する改善案（例）
- 銘柄別 lot_size 対応
- position_sizing の手数料・スリッページのより精密なモデル化
- Monitoring と Execution の熱冗長性（複数プロセス / コンテナ対応）
- 監視アラートの LINE 通知自動化（validate_config のチェック結果を利用）

--- 

（本 CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は、リポジトリの履歴を参照して更新してください。）