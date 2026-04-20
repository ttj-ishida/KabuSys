# CHANGELOG

すべての変更は Keep a Changelog の形式に従っています。項目は重要度別に分類しています。

## [0.1.0] - 2026-04-20

### 追加
- 初回リリース: KabuSys 自動売買フレームワークの初版を公開。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV によりペーパートレード用の MockBrokerClient と本番ブローカーを切替え。ペーパートレード時は専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は実行環境にかかわらず本番の sqlite_path を使用する仕様。
- 設定管理・CLI
  - config.py: .env 自動読み込み機能（.env, .env.local、OS 環境変数を保護）と設定取得用 Settings クラスを実装。必須値チェック（_require）・各種プロパティ（DB パス、KABUSYS_ENV、PAPER_FILL_MODE 等）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（各種項目、シークレット扱い、保存前確認、.env 書き出し）。.env を絶対に Git にコミットしない旨の注記あり。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在・パースチェック（PyYAML がない場合は警告）などを検査。--strict フラグで警告を FAIL 扱いにできる。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・同点タイブレーク）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、1銘柄上限・総投資上限（aggregate cap）に基づくスケーリング、cost_buffer を考慮した保守的見積り、残差処理による追加配分ロジックを実装。
- 研究・指標
  - research/factor_research.py: DuckDB 接続を使ったファクター計算モジュールの骨組み（モメンタム、MA、ATR 等）を追加（設計・定数・API仕様を含む。実装は続きを想定）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。期間フィルタ、稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL 判定を行う。閾値はソース内定義で調整可能。DB パスは引数または環境変数で指定可。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。ルートロガーをクリアして StreamHandler（stdout）と TimedRotatingFileHandler（デフォルト logs/<app>.log、日次ローテーション・30日保持）を設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続する。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定を実装（Windows / POSIX の差分を吸収）。権限不足などで失敗しても警告を出してスキップする安全設計。
- モニタリング DB 初期化
  - monitoring/monitoring_db.py（参照されていることが明示）を使用して、起動時に監視用テーブルの存在を保証（冪等初期化）。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として定義。

### 変更
- ロギングの標準出力は stderr ではなく stdout を使用するように明示（cron/Task Scheduler からのリダイレクトを想定）。
- .env の自動ロード順序を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き禁止）。
- .env パーサーの強化:
  - export KEY=val 形式を受け入れ。
  - シングル/ダブルクォートの内部でのバックスラッシュエスケープに対応。
  - クォートなし値でのインラインコメント判定を改良（'#' の直前が空白またはタブの場合のみコメントと認識）。
- run_execution の DB 接続は環境に応じて paper_sqlite_path（ペーパートレード）または sqlite_path（本番/開発）を選択し、監視テーブルの初期化を行う（ペーパートレード DB と本番 DB の完全分離を担保）。
- run_monitoring は KABUSYS_ENV にかかわらず monitoring は本番 sqlite_path を使用する仕様を明示。

### 修正（不具合対策・堅牢化）
- 各所で I/O / OS 操作に対して例外ハンドリングを追加:
  - ログディレクトリ作成やファイルハンドラ作成失敗時にフォールバックすることで起動失敗を防止。
  - process_priority の設定で権限不足や非対応 OS を捕捉して警告化。
  - run_monitoring の check_once() 呼び出しで例外を捕捉し、次ポーリングへ継続するように保護。
- config_setup の .env 読み書きで既存値の扱いとシークレットのマスク表示を導入。
- validate_config で PyYAML 未インストール時は YAML 検証をスキップして警告を出すようにして、ツールが不要に失敗しないようにした。

### ドキュメンテーション（ソース内コメント）
- 各モジュールに動作・設計方針・使用例を詳細に追記。
- PortfolioConstruction.md / StrategyModel.md 等の設計参照箇所を明記（実コードの挙動説明を補足）。

### セキュリティ・運用上の注意
- .env は決して Git にコミットしないよう出力テンプレートに注記。
- 本番（KABUSYS_ENV=live）向けに validate_config で追加警告を出す（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性等）。

---

（注）
- 本 CHANGELOG は提供されたコードベースの内容・コメントから推測して作成した初期リリース向けのまとめです。実際のリリースノートを作成する際は、コミット履歴やリリース差分を基に追記・修正してください。