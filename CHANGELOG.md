CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).

Unreleased
----------

### Added
- run_monitoring 起動スクリプトを追加
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
  - 停止フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する旨を明示。
- run_execution 起動スクリプトを追加
  - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用（本番 DB と分離）。
  - MockBrokerClient を利用可能にするフラグ/ファクトリ連携を想定。
  - 停止フラグ（data/stop_requested.flag）およびエンジン PID ファイル（data/execution.pid）対応。
- ai/news_nlp モジュールを追加（ニュースの NLP スコアリング）
  - OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む。
  - バッチサイズ、文字数・記事数上限、スコアの ±1.0 クリップ、429/5xx/ネットワーク断に対する指数バックオフ等の堅牢な設計。
  - ニュース収集ウィンドウ計算（JST 基準の前日 15:00 〜 当日 08:30）を提供。
- portfolio 関連の純粋関数群を実装
  - portfolio_builder: select_candidates / calc_equal_weights / calc_score_weights（スコア合計が 0 の場合のフォールバック警告付き）。
  - risk_adjustment: apply_sector_cap（セクター集中上限フィルタ）、calc_regime_multiplier（レジームに応じた投下資金乗数、未知レジームはフォールバックかつ警告）。
  - position_sizing: calc_position_sizes（risk_based / equal / score の各配分方式、lot_size 単位で丸め、aggregate cap によるスケールダウンと残差配分ロジック、cost_buffer を考慮）。
- research モジュール（ファクター計算・特徴量解析）を追加
  - factor_research: calc_momentum / calc_volatility / calc_value（DuckDB 接続を受け SQL で計算）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（外部ライブラリ不要で統計量・IC 計算）。
- tools/paper_verification_report を追加
  - Paper Trading の検証レポートを生成する CLI（期間指定オプション、デフォルト DB パスは data/paper_trading.db）。
  - 稼働率・注文成功率・送信率・P95 レイテンシなどの判定基準と出力フォーマットを実装（閾値は定数で定義）。
- config/settings 実装を強化
  - .env 自動読み込み（.env, .env.local の優先度、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env の行パース（export プレフィックス、クォート文字・エスケープ、インラインコメント処理）を実装。
  - 各種設定プロパティ（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE の検証、PID や閾値など）を提供。
- utils/process_priority を追加
  - Windows と POSIX の差を吸収した set_process_priority と set_cpu_affinity を実装（権限不足や未対応 OS は警告してスキップ）。

### Changed
- 起動処理で最初にプロセス優先度を "high" に設定するように統一（run_monitoring/run_execution）。
- run_execution では paper_trading 環境のとき専用 DB を選択するよう明確化。
- monitoring の DB 初期化（init_monitoring_db）を起動時に必ず呼ぶようにして、監視テーブルが存在することを冪等的に保証。

### Fixed
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分にフォールバックし、WARNING を出力するように改善。
- calc_regime_multiplier: 未知のレジームに対して 1.0 でフォールバックし、警告を出すように修正。
- position_sizing:
  - lot_size 単位での丸め・スケールダウン処理を改善し、残余キャッシュでの端数配分（fractional_remainder）を安定的に行う実装に。
  - cost_buffer を導入して手数料・スリッページを保守的に見積もる仕様に。
- .env パーサー:
  - クォート付き値のバックスラッシュエスケープ処理と閉じクォートまでの切り出し、インラインコメント処理を正しく扱うように改善。
  - export KEY=val 形式に対応。
- tools/paper_verification_report:
  - P95 計算関数を実装し（_p95）、latency 集計で P95 を出力可能に。
  - DB 存在チェックと sqlite3.OperationalError のハンドリングで想定されるテーブル欠如時に優雅に失敗するように。
- utils/process_priority:
  - 権限不足や実装未対応の例外（AccessDenied, NotImplementedError, AttributeError）を捕捉して警告ログを出すように。

0.1.0 - 2026-04-16
------------------

リリース初版（ベース機能群）。主要機能を初回公開。

### Added
- 基本パッケージ構成の追加
  - kabusys パッケージ（__version__ = 0.1.0）
  - サブパッケージ: data, strategy, execution, monitoring（__all__ にエクスポート）
- 実運用向けコンポーネント実装（起動スクリプト・コアライブラリ）
  - run_monitoring, run_execution の起動スクリプト（監視・実行エンジンの起点）
  - ExecutionEngine 周辺の骨格（BrokerClientFactory, OrderManager, OrderRepository, Reconciler, RiskManager を組み合わせてエンジンを起動するフロー）
  - monitoring_db の初期化フック（init_monitoring_db 呼び出し）
- ポートフォリオ構築ロジック（select_candidates, weight 計算, position sizing, risk adjustment）
- リサーチ用ファクター計算（モメンタム/ボラティリティ/バリュー）および特徴量解析ユーティリティ（forward returns, IC, summary）
- AI ニューススコアリング（OpenAI 連携のベース実装）
- 運用ツール: paper_verification_report（Paper Trading の検証レポート生成）

### Changed
- 設定の自動読み込みロジックを導入（.env / .env.local、OS 環境変数を保護）。
- 起動時にプロセス優先度を設定することで運用時の処理安定化を図る。
- paper_trading と live の DB 分離を明確にして安全性を向上。

### Fixed
- 初期リリース相当の既知の安定化と例外ハンドリングの追加（DB が未整備な場合の耐性、API キー未設定時の明確なエラーなど）。

Deprecated
----------
- （現時点なし）

Removed
-------
- （現時点なし）

Security
--------
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を参照する設計。未設定時は ValueError を送出して明確に失敗するようにしているため、キー漏洩防止の観点から自動的に外部に送信されることはない。利用時は環境管理に注意。

注記
----
- 上記 CHANGELOG はソースコードから推測して作成したものであり、実際の変更履歴（コミット単位の履歴）とは完全に一致しない可能性があります。具体的な差分や過去の変更履歴は Git のログを参照して下さい。