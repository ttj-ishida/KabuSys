CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。

v0.1.0 — 2026-04-20
-------------------

初回リリース。以下の主要機能・ユーティリティを実装しました。

Added
- 基本パッケージ情報
  - パッケージのバージョンを src/kabusys/__init__.py にて v0.1.0 として設定。

- 環境設定管理
  - .env の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - Settings クラスを実装し、環境変数を型変換して提供（DBパス、LINE 通知設定、しきい値、実行環境など）。
  - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、KILL_FLAG_CLEAR_ON_START 等の設定項目をサポート。

- 環境設定ウィザード CLI
  - python -m kabusys.config_setup による対話式ウィザードを実装。
  - 秘匿項目はマスク表示、既存 .env の読み込み・上書き、.env 生成/保存機能を提供。

- 設定検証ツール CLI
  - python -m kabusys.validate_config による起動前チェックを実装。必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在・パース検証（PyYAML がない場合はスキップ）を行う。
  - --strict オプションで警告を失敗扱いにできる。

- 実行系起動スクリプト
  - run_execution.py を実装。
  - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB を使用（本番 DB と完全分離）。
  - BrokerClientFactory 経由でブローカークライアントを生成（実運用・モックを切替）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をデーモンスレッドで実行。停止フラグ（data/stop_requested.flag）および PID ファイルを扱う。
  - RiskManager のデフォルト構成（max_position_pct や circuit breaker 等）を設定。

- 監視系起動スクリプト
  - run_monitoring.py を実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下や不正値は警告してデフォルトにフォールバック）。
  - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
  - 停止フラグ検知で監視ループを終了する仕組みを実装。

- ロギングユーティリティ
  - setup_logging を実装。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
  - ログディレクトリ作成に失敗した場合はファイル出力を自動的に無効化し、コンソールのみで継続。
  - ログレベル解決順（引数 > 環境変数 LOG_LEVEL > デフォルト）。

- プロセス優先度 / CPU affinity ユーティリティ
  - set_process_priority と set_cpu_affinity を実装。
  - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。権限不足や未対応 OS では警告してスキップする安全設計。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（スコア降順・タイブレーク）、等金額・スコア加重の重み計算を実装。全スコアが 0 の場合は等金額にフォールバック。
  - risk_adjustment: セクター集中上限適用（既存保有を考慮して候補除外）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。
  - position_sizing: risk_based / equal / score の配分方式に対応した発注株数算出を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金）でのスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮した調整を実装。

- リサーチ（ファクター計算）基盤
  - research/factor_research.py にてモメンタム・ATR 等の計算方針と定数を実装（DuckDB 経由で prices_daily / raw_financials を参照する設計）。関数 calc_momentum の雛形を含む（以降の実装継続を想定）。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py を実装。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を出力。
  - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

- その他ユーティリティ
  - monitoring_db.init_monitoring_db を呼び出して監視用テーブルの存在を保証する箇所を複数スクリプトで使用。
  - run_* スクリプトでプロセス優先度を高（high）に設定してから起動する運用ポリシーを採用。

Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron / タスクスケジューラからのリダイレクト対応のため）。
- .env 自動ロードの挙動
  - OS 環境変数を保護するため、既存の OS 環境変数はデフォルトで上書きしない挙動（.env.local は明示的に override）。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

Fixed
- .env パースの堅牢化（引用符内エスケープ、inline コメント扱い等）により誤った値読込のリスクを低減。
- ログディレクトリ作成失敗時にアプリが異常終了する問題を回避し、代替の stdout ログ出力で継続するように修正。
- process_priority の権限制御エラー（AccessDenied 等）を捕捉して警告ログでスキップするように改良。

Security
- .env を生成する際に注意書きを追加（.env を Git にコミットしない旨を明記）。

Notes / Known limitations
- research/factor_research.calc_momentum の実装はファイル中で途中までの形で含まれており、完全なクエリ実装は今後追加予定。
- position_sizing の価格フォールバック（open_price が欠損した場合の取り扱い）については TODO コメントあり。将来的に前日終値などを使う拡張を検討。
- 一部の機能（例: BrokerClientFactory の具体的実装、ExecutionEngine の内部）は本変更ログの範囲では抽象的に扱われ、詳細は個別モジュールの実装を参照してください。

--- 

今後の予定（例）
- research モジュールの完全実装（各ファクター計算の SQL 実装完了）
- 単体テスト・統合テストの追加（特に position_sizing、risk_adjustment）
- CLI ドキュメント・運用ガイドの整備

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合はそれに合わせて更新してください。）