CHANGELOG
=========

すべての重要な変更は Keep a Changelog のフォーマットに従って記録します。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 進行中: ai/news_nlp モジュールの処理完結（API 呼び出し後の DB 書き込み処理等）に関する追加の堅牢化・部分的リトライ戦略の見直しを予定。
- 小さなリファクタリングおよびドキュメント整備（TODO コメントに基づく改善）。

[0.1.0] - 2026-04-12
--------------------

Added
- 初期リリース（バージョン 0.1.0）。
- 実行系 / 監視:
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を利用し MockBrokerClient を使用する挙動をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値はデフォルト 60 秒にフォールバック）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。
  - PID ファイルや kill-flag 等のパス設定を Settings で管理。
- 設定管理:
  - robust な .env ローダを実装（.env / .env.local の読み込み、export プレフィックス・クォート・インラインコメント対応、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ローディング無効化）。
  - Settings クラスを導入。J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / 環境種別（development / paper_trading / live）等をプロパティ経由で取得。環境変数のバリデーション（例: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL）。
- ポートフォリオ構築:
  - portfolio_builder: 候補選定（select_candidates）、等金額重み（calc_equal_weights）、スコア重み（calc_score_weights）を追加。スコアが全て 0 の場合は等金額配分へフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）および市場レジームに応じた乗数（calc_regime_multiplier）を追加。unknown セクターはセクター上限の対象外とする仕様。
  - position_sizing: position サイズ計算（calc_position_sizes）を追加。allocation_method に risk_based / equal / score をサポートし、lot_size（単元）丸め、aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer（保守的な手数料・スリッページ見積）を考慮。
  - portfolio パッケージのエクスポートを整理。
- リサーチ / ファクター:
  - research.factor_research: DuckDB を使ったファクター計算関数を提供（calc_momentum, calc_volatility, calc_value）。各ファクターは prices_daily / raw_financials テーブルを参照し、データ不足時は None を返す等の堅牢化を実施。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク付けユーティリティ（rank）を追加。pandas 等外部ライブラリに依存しない純粋 Python 実装。
  - research パッケージのエクスポート（zscore_normalize を含む）。
- AI / ニュース:
  - ai.news_nlp: raw_news を集約して OpenAI (gpt-4o-mini) に JSON Mode で問い合わせ、銘柄別センチメント ai_score を ai_scores テーブルへ書き込む処理設計を追加。処理はバッチ（最大 20 銘柄）で行い、トークン肥大化対策（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、スコアの ±1.0 クリップ、429/ネットワーク/5xx のリトライ（指数バックオフ）などを想定。
  - ニュースウィンドウ計算 (calc_news_window) を実装（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換）。
- ユーティリティ:
  - utils.process_priority: プロセス優先度（Windows と POSIX の差分吸収）と CPU affinity 設定関数を追加。権限不足や未対応 OS の場合は警告を出しスキップするフェイルセーフ。
- ツール:
  - tools.paper_verification_report: Paper Trading 用検証レポート生成 CLI を追加。期間指定（--from / --to）や DB パス指定（--db）に対応し、稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を表示・PASS/FAIL 判定する。デフォルト DB は data/paper_trading.db。いくつかの合格基準（閾値）を定義（稼働率 99%、Fill 90% 等）。
- パッケージメタ:
  - パッケージルートに __version__ = "0.1.0" を設定。

Changed
- 基本設計として、DuckDB/SQLite を切り分け（DuckDB は分析系、SQLite は監視 / 発注ログなど）して接続を分離。
- run_execution/run_monitoring で起動時にプロセス優先度を最初に設定するフローを採用（実行開始直後に優先度を上げる）。

Fixed
- .env パースの厳密化（引用符内のバックスラッシュエスケープやインラインコメントの取り扱い改善）。
- DB 初期化の呼び出し（init_monitoring_db）を run_execution/run_monitoring 起動フロー内で冪等に行うことでテーブル不在時の安定起動を確保。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは明示的に引数で渡すことを可能にし、未設定時は環境変数 OPENAI_API_KEY を参照。未設定の場合は ValueError を送出して安全に失敗する設計。
- .env ロード時に OS 環境変数を保護する機能を実装（.env.local による上書きは可能だが OS 環境変数は protected）。

Notes / Known issues / TODO
- position_sizing.calc_position_sizes:
  - price_map が欠損（0.0）だとエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。前日終値や取得原価などのフォールバック価格を利用する拡張が想定されている。
  - 将来的に銘柄ごとの lot_size をサポートする設計への拡張を検討している（現状は共通 lot_size）。
- apply_sector_cap の unknown セクターは上限を適用しない方針だが、必要なら設定で制御可能。
- ai.news_nlp の score_news 実装は全体の設計は記述済みだが、（スナップショット末尾で切れているため）実行時の部分エラー処理・DuckDB 書き込みの細部実装や部分失敗時のロールバック/保護ロジックは引き続き確認が必要。
- DuckDB executemany に関する注意（DuckDB 0.10 の制約）をツール側で考慮している。
- set_cpu_affinity はプラットフォーム依存のため、権限不足や未対応環境ではスキップしログに警告する。

作者注
- 各モジュールは「DB を直接操作するが本番売買 API へはアクセスしない」設計思想（分析系と実行系の分離）に基づいて作成されています。
- ドキュメント内の参照（PortfolioConstruction.md, StrategyModel.md 等）は実装の設計根拠を示すもので、追加ドキュメント整備により使用方法を明確化予定です。