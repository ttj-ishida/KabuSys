# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードベースから推測して作成した変更履歴です。

全般的な方針:
- 日付は本生成時の日付（2026-04-17）を使用しています。
- 各項目はソースコードの導入機能・設計判断・環境変数・既知のフォールバック動作から推定して記載しています。

Unreleased
---------
- なし

[0.1.0] - 2026-04-17
-------------------
Added
- 初期リリース: KabuSys 自動売買フレームワークの基盤機能を実装。
- 実行・監視スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイント。環境に応じて本番/ペーパートレード用 DB を分離して使用（KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用）。停止フラグ（data/stop_requested.flag）検知で安全に停止。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
- 設定/環境読み込み
  - config.Settings: 環境変数ラッパーを提供。.env / .env.local の自動ロード機能（OS 環境変数を保護して上書き制御）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 各種必須環境変数取得用ユーティリティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）。
  - 値検証: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の妥当性チェックを追加。
- データベース関連
  - DuckDB / SQLite の接続を使用（duckdb_path, sqlite_path, paper_sqlite_path を設定で指定可能）。
  - init_monitoring_db を呼び出して監視テーブルの存在を保証する処理を実装（冪等）。
- ポートフォリオ構築（純粋関数群、DB参照無し）
  - portfolio_builder.select_candidates: BUY シグナルのソート（スコア降順、同点は signal_rank でブレーク）と候補選定。
  - portfolio_builder.calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み算出。スコア合計が 0 の場合は等配分にフォールバックし Warning を出力。
  - risk_adjustment.apply_sector_cap: セクター集中上限を評価し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
  - risk_adjustment.calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告付きで 1.0 フォールバック）。
  - position_sizing.calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算。lot_size 単位で丸め、max_position_pct / max_utilization / cost_buffer を考慮したスケーリング処理を実装。aggregate cap 超過時の比例縮小と残差処理（lot 単位での追加配分）を実装。
- 研究（research）モジュール（DuckDB を使ったファクター計算）
  - factor_research.calc_momentum / calc_volatility / calc_value: Momentum, Volatility, Value 系ファクターを DuckDB SQL で計算。200 日 MA、ATR、各種リターン等を算出。データ不足時は None を返す方針。
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank: 将来リターン計算、Spearman ランク相関（IC）計算、ファクター統計要約などを実装。外部ライブラリ依存せずに標準ライブラリで実装。
  - 設計方針として prices_daily/raw_financials のみ参照し、外部 API にはアクセスしないことを明記。
- AI ニュース NLP（OpenAI 経由のスコアリング）
  - ai/news_nlp.py: raw_news を集約して OpenAI (gpt-4o-mini) に送信し、銘柄ごとの ai_score を ai_scores テーブルへ書き込むフローを実装。バッチ処理（最大 _BATCH_SIZE=20）、JSON 出力厳格性、スコアクリッピング（±1.0）、リトライ（429/5xx/接続障害に対する指数バックオフ）等を実装。
  - ニュースウィンドウ計算（JSTベース -> UTC 変換）を提供（calc_news_window）。
- ツール
  - tools.paper_verification_report: ペーパートレード DB（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ（P95 等）を集計し、PASS/FAIL 判定を行う CLI を追加。閾値はソース内定義（例: 稼働率 >= 99%、P95 <= 200ms 等）。日付フィルタ --from/--to、--db オプションに対応。
- ユーティリティ
  - utils.process_priority.set_process_priority: cross-platform（Windows / POSIX）でプロセス優先度を設定するユーティリティ。対応 OS 判定とエラー時のフォールバック（警告）を実装。
  - utils.process_priority.set_cpu_affinity: CPU affinity を最初の N コアに固定する機能を追加（None の場合は変更しない）。パーミッションエラー・未対応環境では警告を出してスキップ。

Changed
- なし（初期リリースにおける「追加」主体の反映）

Fixed
- なし（初版として既知バグ修正履歴は無し）

Deprecated
- なし

Removed
- なし

Security
- 環境変数による API キー等の取り扱いは環境変数を想定（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN 等）。.env 自動読み込みは OS 環境変数を保護する設計（protected セット）で実装。

注記 / マイグレーションガイド
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は Settings で必須。未設定時は起動時に例外が発生します（.env.example を参照して設定してください）。
  - OpenAI を使う処理は OPENAI_API_KEY が必要（ai/news_nlp.score_news の呼び出し時に検査）。
- 環境変数（主要なもの）:
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。正の整数でない場合はデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）。無効値は例外。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動読み込みを無効化。
- 実行方法の例:
  - 監視ループ: python -m kabusys.run_monitoring
  - 実行エンジン: python -m kabusys.run_execution
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 停止フラグ:
  - data/stop_requested.flag（プロジェクトルートの data 配下）を配置すると実行中のプロセスが検知して安全に停止する仕組みがあるため、外部から停止させたい場合はこのファイルを利用してください。
- 既知の注意点:
  - portfolio.position_sizing の価格欠損時（price が 0.0 または None）はその銘柄をスキップするロジックが入っており、将来的には前日終値や取得原価のフォールバックを検討する旨の TODO が残されています。
  - ai/news_nlp.py は堅牢な設計（バッチ、リトライ、JSON 検証）を持つ一方で、API 使用量やレスポンスフォーマットに依存するため、運用時には OpenAI 側の仕様変更に注意してください。
  - research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存します。テーブルスキーマとデータ品質が結果に強く影響します。

開発者向け補足
- パッケージバージョンは src/kabusys/__init__.py にて __version__ = "0.1.0" として管理されています。
- 単体関数群（portfolio/*, research/*）は純粋関数設計が意識されており単体テストが書きやすくなっています。
- 設定読み込みのパーサーはシェル風の .env 行パース（export, クォート、インラインコメントルール）に対応しています。

（以上）