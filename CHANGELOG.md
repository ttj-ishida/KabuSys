CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と、セマンティックバージョニングに従います。
（参考: https://keepachangelog.com/ja/1.0.0/）

[0.1.0] - 2026-04-12
--------------------

Added
- 初回リリースを公開。
- 実行エントリ／長期プロセス
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。MockBrokerClient の使用を想定。
    - 起動時にプロセス優先度を High に設定するユーティリティを呼び出す。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する（監視データは本番 DB に蓄積）。
    - 起動時にプロセス優先度を High に設定。

- 設定管理
  - kabusys.config.Settings: 環境変数 / .env 読み込みによる設定管理を実装。
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードする（無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - .env パーサは export プレフィックス、引用符（シングル/ダブル）のエスケープ、インラインコメント等に対応。
    - J-Quants / kabu API / LINE / DB / 監視・しきい値・実行用パスなど多数のプロパティを提供。
    - PAPER_FILL_MODE の値検証、KABUSYS_ENV / LOG_LEVEL の検証ロジックを含む。

- ポートフォリオ構築（純粋関数群）
  - kabusys.portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソートし上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算（スコア全ゼロ時は等金額にフォールバック）。
  - kabusys.portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限の適用（既存ポジションの時価から判断、unknown セクターは適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - kabusys.portfolio.position_sizing
    - calc_position_sizes: 等配分／スコア配分／リスクベース（risk_based）に対応した発注株数決定ロジックを実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮。
    - 利用可能現金を超えた場合のスケールダウンと残差処理（lot 単位で残余を再配分）を実装。

- 研究（Research）用モジュール
  - kabusys.research.factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率 (MA200) 等の計算を DuckDB SQL ベースで実装。
    - calc_volatility: ATR(20) / 相対 ATR / 20 日平均売買代金 / 出来高比などを計算。
    - calc_value: P/E（per）と ROE を raw_financials と prices_daily から計算。
  - kabusys.research.feature_exploration
    - calc_forward_returns: 将来リターン（デフォルト: 1,5,21 営業日）を計算。
    - calc_ic / rank / factor_summary: IC（Spearman ρ）やランク化・統計サマリーの純粋関数を提供。
  - すべて DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照する設計（本番 API にアクセスしないことを保証）。

- ニュース NLP（AI）機能
  - kabusys.ai.news_nlp
    - raw_news を銘柄ごとに集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルに格納する処理を実装。
    - バッチサイズ、文字数上限、記事数上限、JSON Mode の期待される出力フォーマットなどを定義。
    - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - API キー未設定時は ValueError を送出（api_key 引数または環境変数 OPENAI_API_KEY を参照）。

- ユーティリティ
  - kabusys.utils.process_priority
    - set_process_priority(level): Windows / POSIX の差を吸収して現在プロセスの優先度を設定（アクセス権限がない場合は警告でスキップ）。
    - set_cpu_affinity(cpu_count): プロセスを最初の N コアにピン留め（未対応環境では警告でスキップ）。
  - ロギングや例外処理を踏まえた堅牢な実装。

- ツール
  - kabusys.tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加。
    - 指標: 稼働率 (uptime)、注文成功率、送信率、P95 レイテンシ 等。
    - デフォルト閾値・判定基準（例: 稼働率 >= 99%、P95 <= 200 ms 等）とコマンドライン引数 (--from, --to, --db) を提供。
    - DB 存在チェックと sqlite3.OperationalError に対するフェイルセーフなハンドリングを実装。

Changed
- 初版において設計上の挙動を明記（監視は常に本番 sqlite_path を使用する、paper_trading は DB を分離等）。
- .env 自動ロードの挙動を明確化（プロジェクトルート基準／OS 環境変数優先／.env.local は上書き可能）。

Fixed
- N/A 初版リリースのため現時点で修正履歴はなし。

Deprecated
- N/A

Security
- OpenAI API キーを直接ログに出力しない設計。API キーは引数または環境変数で受け取り、必要以上に露出しないよう実装。

Notes / 注意点
- run_monitoring.py は監視データを本番 sqlite_path に書き込むため、監視用途で Paper Trading と分離したい場合は注意が必要（設計上監視は本番 DB を参照する仕様）。
- .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml が存在しない場合、自動ロードはスキップされる）。
- process_priority / cpu_affinity の設定は権限不足や未対応プラットフォームで失敗することがあり、その場合は警告を出して処理を継続する。
- AI ニューススコアリングは OpenAI API に依存するため、API 使用量・料金・レート制限に注意すること。

今後の予定（例）
- ファクター計算のパフォーマンスチューニング（DuckDB クエリ最適化）。
- portfolio の lot_size を銘柄別に扱えるよう拡張。
- AI モジュールのローカルフォールバックオプションやスケジューリングの実装。

----