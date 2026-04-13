CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-13
--------------------

Added
- 初期リリース: KabuSys — 日本株自動売買システムの基本モジュール群を実装。
- 実行および監視エントリポイント:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite DB を使用し、MockBroker を利用して本番 DB と完全分離して実行可能。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を設定し、監視用 DB を初期化してポーリングを継続する。
- 設定管理:
  - config.Settings を実装。.env/.env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）、プロジェクトルート自動検出（.git または pyproject.toml 基準）、環境変数必須チェック、各種パス・閾値・フラグのプロパティラッパーを提供。
  - .env パースは export 形式・クォート・エスケープ・インラインコメントを考慮する実装。
- ポートフォリオ構築ライブラリ (kabusys.portfolio):
  - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装。スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - risk_adjustment: apply_sector_cap（セクター集中の除外ロジック）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。unknown セクターはセクター上限の対象外。
  - position_sizing: calc_position_sizes を実装。allocation_method("risk_based" / "equal" / "score") に対応し、単元株（lot_size）、コストバッファ、aggregate cap（利用可能現金）を考慮したスケールダウンロジックを実装。
- 研究／ファクター計算 (kabusys.research):
  - factor_research: calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials テーブルを参照し、MA200、ATR20、各種モメンタムを計算。
  - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関による IC）、factor_summary（統計サマリ）、rank（平均ランク扱い）を実装。外部依存を避け、標準ライブラリで実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）、上記ファンクション群をエクスポート。
- ニュース NLP スコアリング (kabusys.ai.news_nlp):
  - raw_news を集約し OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコア（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
  - バッチ処理（1 リクエストあたり最大 20 銘柄）、トークン肥大化対策（記事数・文字数のトリム）、JSON Mode 指定、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアクリップを実装。
  - ニュース収集ウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して DB と照合するロジックを実装（calc_news_window）。
- ユーティリティ:
  - utils.process_priority: プラットフォーム差分を吸収した set_process_priority と set_cpu_affinity を実装。Windows / POSIX（Linux, Darwin, FreeBSD）に対応し、権限不足時には警告を出してスキップする。
- 運用支援ツール:
  - tools.paper_verification_report: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを算出し、PASS/FAIL 判定ルール（しきい値）を定義。
- DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を用いて監視テーブルが存在することを保証する処理を実行（冪等）。
- パッケージメタ:
  - kabusys.__version__ = "0.1.0"

Fixed / Improved
- .env ローダーの堅牢性向上: export 前置、クォート内エスケープ、インラインコメントの取り扱いを細かく実装し、OS 環境変数の保護（protected set）を実現。
- DuckDB / SQLite を併用する設計: 解析・研究処理は DuckDB、監視・実行ログは SQLite に分離。

Notes / Known TODOs
- position_sizing.calc_position_sizes:
  - 銘柄ごとの lot_size を将来的にサポートする予定（現状は共通 lot_size パラメータ）。
- risk_adjustment.apply_sector_cap:
  - price が 0.0 の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO が残されている（将来的に前日終値や取得原価でのフォールバックを検討）。
- ai.news_nlp:
  - OpenAI API キーが未設定の場合は明示的に ValueError を送出する設計（運用時の注意点）。
  - 処理はフェイルセーフ設計（API エラー時は該当チャンクをスキップして継続）になっている。
- run_monitoring の MONITOR_POLL_INTERVAL:
  - 0 以下の値は無効と扱い、デフォルトにフォールバックする挙動（time.sleep に対する安全策）。
- tests / ドキュメント:
  - サンプルやユニットテストは含まれていないため、導入時に環境変数設定 (.env.example 参照) と DB 初期化を確認してください。

Breaking Changes
- なし（初期リリース）

Security
- OpenAI API キーや各種シークレットは環境変数で管理する設計。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。環境変数の保護を考慮して .env ロード時に OS 環境変数を上書きしない実装。

Acknowledgements / Credits
- 初期実装（v0.1.0）。今後の改善点・バグ修正は未だ多く想定されます。導入前に README / .env.example を参照し、運用ポリシー（API キー・DB パス・PID ファイル等）を適切に設定してください。