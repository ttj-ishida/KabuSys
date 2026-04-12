# CHANGELOG

この CHANGELOG は Keep a Changelog の様式に準拠しています。  
（リリース日時はコードの内容から推測して記載しています。正確な日付は実際のリリース履歴に合わせて修正してください。）

全般
- SQLite / DuckDB を組み合わせたローカル分析・監視基盤を中心に構築された日本株自動売買システムの初期リリース相当の変更履歴を記載しています。
- .env 自動ロード、paper trading 用の DB 分離、OpenAI を用いたニュース NLP バッチ処理、ポートフォリオ構築/ポジションサイズ計算、リサーチ系ファクター計算などの主要機能が含まれます。

Unreleased
- 予定・考慮中の改善点（コード上の TODO やフェイルセーフに基づく推測）
  - news_nlp.score_news の部分的な実装完了やエラーハンドリング改善（レスポンスバリデーション失敗時のログ強化、部分更新の更なる堅牢化）
  - OpenAI 周りのリトライ・バックオフのテスト強化（429 / ネットワーク / 5xx に対する動作確認）
  - run_* スクリプトの CLI オプション追加（ポーリング間隔やデバッグモードの明示的指定）
  - duckdb 接続のコンテキスト管理改善や接続プール化（長時間バッチの安定化）
  - 単体テスト・統合テストの追加（factor_research、position_sizing、risk_adjustment 等）

[0.1.0] - 2026-04-12
- Added
  - 実行系・監視系起動スクリプト
    - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。実行前にプロセス優先度を上げ、SQLite / DuckDB に接続して実行セッションを開始する。KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に接続して本番 DB と分離する。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
  - 設定管理
    - config.Settings: .env と環境変数を統合する設定管理クラスを導入。自動 .env ロード（.env, .env.local）を行い、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 複数の設定プロパティを追加（DB パス、paper_trading 用 DB パス、PID / KILL フラグパス、閾値、ログレベル判定、env 検証など）。
    - .env パーサ: export 形式、クォートおよびエスケープ、インラインコメントの処理、保護済み OS 環境変数の上書き制御を実装。
  - ポートフォリオ構築ライブラリ（pure functions）
    - portfolio.portfolio_builder: シグナル候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
    - portfolio.position_sizing: position sizing ロジック（risk_based / equal / score）、lot_size 丸め、aggregate cap によるスケールダウン、cost_buffer 考慮を実装。
    - portfolio.risk_adjustment: セクター上限フィルタ (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を実装。
  - リサーチ / ファクター計算
    - research.factor_research: Momentum / Volatility / Value 等のファクター計算を DuckDB SQL で実装（calc_momentum, calc_volatility, calc_value）。200 日移動平均、ATR、各種リターンを計算。
    - research.feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリ (factor_summary)、ランク関数 (rank) を提供。
    - research パッケージは DuckDB を使ったオフライン分析を前提とし、本番 API にはアクセスしない設計。
  - AI / ニュース NLP
    - ai.news_nlp: OpenAI (gpt-4o-mini) を用いたニュースセンチメントスコアリングを実装。銘柄ごとの記事集約、チャンク化（最大 20 銘柄/リクエスト）、最大記事数・文字数制限、JSON Mode での厳格なレスポンス期待、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフリトライを設計。
    - calc_news_window ユーティリティで JST/UTC のニュースウィンドウ計算を提供。
    - OpenAI API キー未設定時は ValueError を送出する安全設計。
  - ツール
    - tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。システム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出して標準出力へ出力。期間フィルタ (--from / --to) と DB パス指定 (--db) をサポート。
  - ユーティリティ
    - utils.process_priority: クロスプラットフォームに対応したプロセス優先度設定 (set_process_priority) と CPU affinity 設定 (set_cpu_affinity) を追加。Windows / POSIX(nice) の差分吸収、権限不足時は警告でスキップ。
  - DB 初期化
    - monitoring.monitoring_db.init_monitoring_db の呼び出しを多数箇所で行い、監視テーブルの存在を保証（冪等）。
  - パッケージ管理
    - kabusys.__init__ に __version__ = "0.1.0" を設定。

- Changed
  - 本番と paper_trading の DB 分離ポリシーを採用（run_execution: settings.is_paper により PAPER_TRADING_SQLITE_PATH を使用）。
  - 監視 (run_monitoring) は環境に関係なく本番 sqlite_path を使用するよう仕様化（監視情報は本番 DB に集約）。
  - DuckDB を分析用途に明確に導入し、research / ai モジュールで活用（prices_daily / raw_financials / raw_news などのテーブル参照）。
  - ログ初期化を各起動スクリプトで行い、デフォルト INFO レベルを設定。

- Fixed / Hardened
  - .env パーサの堅牢化（クォート内のバックスラッシュエスケープ、コメント判定の細分化、空行/コメント行スキップ）。
  - process_priority の実行環境差異による例外（AccessDenied / NotImplementedError）を捕捉して警告にフォールバック。
  - position_sizing / risk_adjustment における価格欠損時の安全化（価格なし / 0 の場合はスキップし、過小評価の TODO を残す）。
  - paper_verification_report: DB が存在しない場合の明確なエラーメッセージと、テーブル欠如時の OperationalError に対するフォールバックを実装（各集計で try/except してデフォルト値を返す）。

- Security
  - ai.news_nlp.score_news は OpenAI API キーが未設定の場合に明示的に例外を投げる（誤動作を防止）。

- Notes / Known limitations
  - position_sizing の lot_size は現状グローバルで固定（将来的に銘柄別 lot_map を想定している）。
  - apply_sector_cap は "unknown" セクターを上限適用対象外としており、price が欠損 (0.0) の場合にエクスポージャーが過小評価される可能性がある（コード中に TODO を残し改良予定）。
  - ai.news_nlp のレスポンス部分は厳格に JSON を期待するため、API のフォーマット変更に弱い。レスポンスバリデーションは実装済みだが、部分失敗時のロールバック戦略は限定的。
  - .env 自動ロードはプロジェクトルート検出に .git または pyproject.toml を使うため、配布パッケージ化後は自動ロードがスキップされる可能性がある（設定設計の意図）。

デベロッパ向けメモ（推測）
- 環境変数で細かい挙動を制御する設計（PAPER_FILL_MODE, KABUSYS_ENV, MONITOR_POLL_INTERVAL, KILL_FLAG_CLEAR_ON_START 等）により、テストと本番の切り替えを容易にしている。
- DuckDB を利用したオフライン解析と SQLite を利用したイベント・監視ログの混在設計。分析は DuckDB（高速かつ SQL ベース）、監視 / トレードログは SQLite（軽量）という役割分担。
- OpenAI の利用は外部 API との相互作用を含むため、API キーとレート制限への考慮が必要。リトライ・バッチ化はそのための実装。

今後の推奨対応（提案）
- news_nlp の API エラー時の部分更新ロールバック / トランザクション戦略を明確化する。
- duckdb 接続管理を context manager 化・テストケース追加。
- position_sizing の lot_map 拡張、銘柄別手数料/スリッページモデルの導入。
- run_* スクリプトに対する CLI ドキュメント・systemd / supervisor 用のユニットファイル例を提供。

--- 

（この CHANGELOG はコードの内容から推測して作成しています。正式なリリース履歴や日付はプロジェクトの実際の運用記録に基づいて更新してください。）