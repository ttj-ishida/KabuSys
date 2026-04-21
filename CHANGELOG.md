KEEP A CHANGELOG
すべての重要な変更はこのファイルに記録します。

フォーマットは "Keep a Changelog" に従います。  
慣例的にセクションは Added / Changed / Fixed / Deprecated / Removed / Security を使用します。

[Unreleased]
- なし

[0.1.0] - 2026-04-21
Added
- 基本アプリケーション構成と複数の起動/運用ユーティリティを実装しました。
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
- 起動スクリプトを追加:
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレーディング用 DB（data/paper_trading.db など）と MockBrokerClient を利用し、本番 DB と分離して実行します。実行中の PID 管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照します。停止フラグ検知と KeyboardInterrupt による安全終了をサポート。
- 設定関連ツールを追加:
  - config.py: .env 自動読み込み機構（プロジェクトルート検出）と堅牢なパースロジックを実装。Settings クラスで環境変数アクセスをラップし、必須項目の取得関数や各種既定値・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
  - config_setup.py: .env を対話形式で生成・更新するウィザードを実装。既存 .env 読み込み、シークレットマスク表示、確認後ファイル書き込みを行う。
  - validate_config.py: 起動前チェック用 CLI を実装。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在/パース検証を行う。--strict オプションで警告をエラー扱いにできる。
- ロギング/プロセス制御ユーティリティを追加:
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定する共通セットアップを実装。ログディレクトリの自動作成と失敗時のフォールバックをサポート。
  - utils/process_priority.py: Windows/Linux/macOS に対応したプロセス優先度設定（high/normal/low）と CPU affinity 設定ユーティリティを実装。アクセス権限がない場合は警告ログでスキップ。
- ポートフォリオ構築関連の純粋関数群を追加（DB 非依存、メモリ計算）:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分を実装。スコアが全て 0 の場合は等分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジーム時はフォールバックと警告を出す。
  - portfolio/position_sizing.py: 発注株数計算ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、1 銘柄上限・総投下上限（aggregate cap）のスケールダウン処理、コストバッファ対応、残差処理によるロット追加配分を備える。
  - portfolio/__init__.py で上記 API を公開。
- Paper Trading 検証レポートツールを追加:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計を行い、稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などをまとめて出力する CLI を実装。基準値（稼働率 99%、成功率 90%、送信率 95%、P95 <= 200 ms）により PASS/FAIL を判定する。日付フィルタと --db オプションをサポート。
- 監視用 DB 初期化処理を追加:
  - monitoring.monitoring_db.init_monitoring_db が呼び出されるよう起動スクリプトで使用（冪等にテーブル作成を保証）。

Changed
- ログ出力の統一:
  - すべての起動スクリプトで utils.logging_setup.setup_logging を呼び出す設計により、ログハンドラとフォーマットを統一。
- 環境変数ロード順を明確化:
  - config.py にて OS 環境 > .env.local > .env の優先順位を採用。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止を追加。

Fixed
- 例外処理強化:
  - run_monitoring のポーリングループ内で monitor.check_once() が例外を投げてもログ出力して次のポーリングへ復帰するようにハンドリング。run_execution でもスレッド管理と停止フラグ検知を厳密化。

Security
- 機密情報の取り扱い:
  - config_setup の対話UI と .env 書き込みでトークン/パスワードはシークレットとしてマスク表示。README 等で .env を Git にコミットしないよう注意書きを出力。

Notes / Implementation details（実装上の重要点）
- Settings でのバリデーション:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許可。
  - PAPER_FILL_MODE は "instant" | "partial" | "never" | "reject" のみ許可。
  - LOG_LEVEL は標準のログレベルのみ受け付け、不正値は例外を送出。
- run_execution のリスク管理:
  - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec 等）を Engine 起動時に渡す。initial_portfolio_value は broker.get_available_cash() を用いて初期化。
- ファイル / ディレクトリ操作の堅牢性:
  - logging_setup はログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続するデザイン。
  - config._find_project_root() によるプロジェクトルート検出は __file__ を基準に行うため、CWD に依存しない。

Deprecated
- なし

Removed
- なし

今後の予定（メモ）
- research/factor_research.py はモメンタム等ファクター計算の関数定義を開始しています（ファイル末尾で途中）。DuckDB を使ったファクター群の完成・テストを予定。
- 起動スクリプト・エンジン間の統合テストや CLI ドキュメントの追加、エラーハンドリングの増強を予定。

---

参考:
- エントリポイント:
  - 設定検証: python -m kabusys.validate_config
  - 設定ウィザード: python -m kabusys.config_setup
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report

（この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴やリリース日、詳細は開発履歴に合わせて調整してください。）