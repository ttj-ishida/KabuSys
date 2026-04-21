CHANGELOG
=========

この CHANGELOG は Keep a Changelog のフォーマットに準拠しています。  
以下の記載は提示頂いたコードベースから推測して作成した変更履歴です（実装上のコメントや挙動から機能追加・修正点を抽出しています）。

Unreleased
----------

（なし）

0.1.0 - 2026-04-21
------------------

Added
- 環境設定・管理周りを導入
  - .env ファイルの自動ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - 高機能な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの取り扱い等）。
  - Settings クラスを追加し、J-Quants / kabuステーション / LINE / DBパス / 監視閾値 / 実行環境（development/paper_trading/live）などの設定値をプロパティで取得可能に。
  - config_setup CLI（対話式ウィザード）を追加し、.env の作成・更新を支援。
  - validate_config CLI を追加し、.env と config/*.yaml（PyYAML利用時）の静的検証を実施（--strict オプションで警告もFAIL扱いに）。

- 実行スクリプト群を追加
  - run_execution: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離して動作。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知でループを終了。

- 発注・実行基盤の骨格を追加
  - BrokerClientFactory によるブローカークライアント生成に対応（テスト用 Mock クライアント等を工場パターンで切り替え）。
  - ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の依存関係を組み立てる起動処理を実装。

- 監視・分析基盤を導入
  - monitoring 用の SQLite DB 初期化（init_monitoring_db）を実行。monitoring 用テーブルが存在することを保証（冪等）。
  - DuckDB 接続サポートを追加し、分析用途に使用（duckdb による prices/financials 等の集計想定）。

- ロギング・プロセス管理ユーティリティを追加
  - setup_logging ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定し、ログディレクトリを自動作成。ログレベルは引数 > 環境変数 > デフォルトの優先順で解決。
  - process_priority ユーティリティを追加し、Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）と CPU affinity 設定を提供。権限がない場合は警告を出してスキップする安全設計。

- Portfolio 構築ライブラリを追加（純粋関数群）
  - portfolio_builder: シグナルから候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）。
  - risk_adjustment: セクター集中制限の apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。
  - position_sizing: 株数決定ロジック calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応し、lot_size による丸め、aggregate cap によるスケーリング（cost_buffer を考慮）を含む。

- Paper Trading 向け検証ツールを追加
  - tools/paper_verification_report.py により paper_trading DB を集計してレポート出力、稼働率・注文成功率・送信率・レイテンシ(P95) 等の指標を算出し PASS/FAIL を出力する CLI を実装。閾値はファイル内定数で管理。

- research/factor_research の初期実装（モメンタム等のファクター計算の骨格）
  - DuckDB 接続を受け取り prices_daily / raw_financials を用いてモメンタム・MA200乖離等を計算するための関数を追加（ファイル途中までの実装）。

Changed
- DB 周りの分離とデフォルトパス
  - 本番用の monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する旨の挙動を導入（run_monitoring の設計上の判断）。
  - run_execution では paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離。

- ログ出力の取り扱いを改善
  - StreamHandler は stdout に出力（stderr ではなく）するよう変更。これにより cron / Task Scheduler 等で stdout/stderr を一本化してリダイレクトしやすくした。
  - ログファイル出力用ディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続する堅牢化を実装。

- 環境変数読み込みの優先順位
  - OS 環境変数 > .env.local > .env の優先順位で読み込む設計。既存 OS 環境変数は protected として .env により上書きされない。

Fixed
- .env パーサの堅牢性向上
  - export プレフィックス対応、クォート内のエスケープやクォート閉じ処理、コメントの扱いなどに対応し、従来の単純なパースで発生しがちな誤判定を回避。

- 監視 DB 初期化の冪等化
  - init_monitoring_db を呼び出すことで監視テーブルの存在を保証する処理を追加（既に存在する場合でも安全に呼べる）。

Notes / Known limitations / TODO
- apply_sector_cap 内で価格が 0.0 の場合にエクスポージャーが過少見積りされる旨の注意コメントが残っており、将来的に前日終値や取得原価をフォールバックする改善案が提示されている。
- position_sizing の lot_size は現状全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を導入する設計拡張の TODO がある。
- research/factor_research はファイル末尾が途中で切れている（モメンタム処理の実装が一部で終端しているため、未完の関数 / 追加実装が必要）。
- run_monitoring は環境に関係なく「本番 sqlite_path を使用する」という挙動は設計上の選択であり、誤って本番データベースを参照／改変しないよう運用上の注意が必要。
- process_priority/set_cpu_affinity は権限や OS に依存するため、権限不足時に警告を出してフォールバックする設計になっている（期待どおりに反映されないケースあり）。

セキュリティ
- 特に本リリースで新たに報告されているセキュリティ脆弱性はありませんが、.env に秘密情報（トークン・パスワード）を保持する設計のため .env を決してリポジトリにコミットしない運用を README 等で周知する必要があります（config_setup の出力コメントにも注意書きあり）。

メタ
- パッケージの初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py の __version__ に基づく）。

---

注: 上記は提示いただいたコードから推測して作成した CHANGELOG です。実際のリリースノートとして使用する場合は、実装者／リポジトリのコミット履歴と照合して差分や日付を確定してください。