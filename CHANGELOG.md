CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- minor: ドキュメント整備や内部リファクタ（テスト/運用用の小修正）。  

0.1.0 - 2026-04-19
------------------

Added
- 起動スクリプトを追加/整備
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV に応じて本番 DB / ペーパートレード DB（data/paper_trading.db）を切り替え、BrokerClientFactory を使ってブローカークライアントを構築。実行はスレッドで行い、data/stop_requested.flag による停止や data/execution.pid の管理に対応。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する。

- 設定・環境管理
  - config.py: .env 自動読み込み機構を導入（プロジェクトルートを .git / pyproject.toml で検出）。.env/.env.local の読み込み順と保護された OS 環境変数を考慮した上書きルールを実装。各種設定値（DB パス、PID ファイルパス、閾値、PAPER_FILL_MODE など）を Settings クラスとして提供し、未設定時に例外を投げる必須チェックを実装。
  - config_setup.py: .env を対話的に初期作成・更新するウィザードを追加。秘密値のマスク表示、既存 .env の読み込み、書き込み機能を備える。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース（PyYAML がある場合）や本番環境向けのガードチェックを行う。--strict オプションで警告も失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py: 全起動スクリプトで共通利用できるロギング設定を実装。コンソール（stdout）への StreamHandler と日次ローテート（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールのみで継続する。ログレベル解決順（引数 > 環境変数 > デフォルト）を明示。
  - utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（Windows の優先度クラス / POSIX の nice 値）と CPU affinity 設定を提供。権限不足や未対応 OS 時は警告を出して安全にフォールバック。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア正規化配分（スコア全て 0 の場合は等金額にフォールバック）を実装。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出と単元丸め、per-position と aggregate のキャップ、コストバッファを考慮したスケーリングおよび残余のロット配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションからセクター別エクスポージャを算出し上限超過セクターの候補除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームは警告を出してフォールバック。

- 運用ツール
  - tools/paper_verification_report.py: ペーパートレードの検証レポートを生成する CLI を追加。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（P95）等を集計し、所定の閾値に対する PASS/FAIL を判定。日付フィルタと DB パス指定（--db / 環境変数）をサポート。

- 研究モジュール（途中実装）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity の計算方針を定義）。関数インターフェースと定数を導入（モメンタムや MA200 の窓、ATR、出来高など）。（注: ファイル末尾で計算関数の実装が続く想定で一部が未完）

Changed
- ログ出力挙動の統一
  - ログは標準エラーではなく標準出力（stdout）へ出すように変更。cron/Task Scheduler でのリダイレクト運用を考慮。

- .env 読み込みルール
  - 自動ロードをデフォルトで有効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。読み込み優先度は OS 環境変数 > .env.local > .env。プロジェクトルートを __file__ から探索する実装に変更し、CWD に依存しないようにした。

Fixed
- .env パーサーの強化
  - 値のクォート処理（バックスラッシュエスケープを含む）とインラインコメントの扱いを正しく処理するよう修正。export プレフィックスに対応。無効行のスキップを厳格化。

- 起動時の DB 初期化の冪等性
  - init_monitoring_db 呼び出しを実行系および監視系の起動時に行い、監視テーブルが存在することを保証（何度実行しても影響しない）。

- プロセス優先度設定の頑健性向上
  - 未対応 OS や権限エラー発生時に警告を出して処理を継続するように改善。

Security
- 環境変数の取り扱い
  - 設定ウィザードと .env 書き出しでシークレット項目（トークン・パスワード）をマスクして表示。.env に関する注意書きを生成時に追記（.env を Git にコミットしないよう明記）。

Potential Breaking Changes / 注意点
- Settings クラスの必須チェック
  - Settings.jquants_refresh_token / kabu_api_password は未設定だと ValueError を送出するため、事前に環境変数を設定しておく必要があります（validate_config でチェック可能）。
- KABUSYS_ENV の妥当性チェック
  - 許容値は "development", "paper_trading", "live" のみ。無効値は ValueError を発生させます。
- 監視 DB の使用
  - run_monitoring は環境に関係なく Settings.sqlite_path（本番監視 DB）を使用します。ペーパートレードと完全に分離したい場合は run_execution が paper_sqlite_path を使用する点に注意してください。
- .env 自動読み込み
  - 自動読み込みがデフォルトで有効になっているため、想定外の環境変数がロードされる可能性があります。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Notes / Implementation details
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で制御。0 以下や不正な値はデフォルト 60 秒にフォールバックし、警告を出す。
- run_execution は paper_trading 環境時に BrokerClientFactory により MockBrokerClient を生成し、paper_trading 用 DB へ記録する設計（本番 DB と分離）。
- position_sizing のスケーリング処理は lot_size 単位で丸め、残余キャッシュで fractional 残差の大きい銘柄から追加配分するロジックを持つ。
- risk_adjustment の apply_sector_cap は "unknown" セクターの銘柄を除外対象外とする（セクター不明は上限適用しない）。
- logging_setup はログディレクトリ作成失敗時にファイルハンドラ作成をスキップし、コンソールのみで継続するため、運用環境の権限問題に弱くない設計。

貢献・フィードバック
- 設計や閾値、挙動（例: PAPER_FILL_MODE の取り扱いやレジーム乗数など）に関する改善提案やバグ報告は歓迎します。README やドキュメント（PortfolioConstruction.md 等）に合わせて調整予定です。