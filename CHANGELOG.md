CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

- Added
  - news_nlp モジュールにおけるニュース収集ウィンドウ計算 (calc_news_window) と OpenAI 統合の骨格を追加。
    - バッチ送信、再試行戦略、レスポンス検証、スコアクリッピング（±1.0）などの設計が実装されている。
    - OpenAI API キーを引数または環境変数 OPENAI_API_KEY で指定可能。
  - research モジュールにおけるファクター計算・探索ユーティリティを拡充。
    - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily / raw_financials を使ったモメンタム・ボラティリティ・バリュー計算。
    - calc_forward_returns / calc_ic / factor_summary / rank：将来リターン計算、IC（Spearman）計算、ファクター統計サマリ。
    - DuckDB を用いた大規模データ向け SQL + Python 実装。
  - portfolio モジュール（純粋関数）の整備。
    - portfolio_builder: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）。
    - risk_adjustment: セクター集中上限適用（apply_sector_cap）、市場レジーム乗数（calc_regime_multiplier）。
    - position_sizing: position 数量計算（calc_position_sizes）、risk-based / equal / score 配分、単元株丸め、aggregate cap スケーリング。
  - 実行・監視用スクリプトを追加／改善。
    - run_execution.py: ExecutionEngine を起動する CLI スクリプト。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用の専用 SQLite DB（デフォルト data/paper_trading.db）へ記録する分離設計。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL によるポーリング間隔の上書き対応（デフォルト 60 秒）、停止フラグファイルによる安全停止、起動時にプロセス優先度を High に設定。
    - 両スクリプトは起動時にプロセス優先度を高めるユーティリティを呼び出す（set_process_priority）。
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポート出力ツール（CLI）。期間指定 (--from / --to) と DB 指定 (--db / 環境変数) に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定（閾値はファイル内定義）。
  - 設定読み込み・検証を強化（kabusys.config）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）と .env / .env.local の自動ロード（OS 環境変数優先、上書き保護）。
    - .env パーサにおける引用符・エスケープ・インラインコメント対応を実装。
    - 必須環境変数未設定時に ValueError を投げる _require()、KABUSYS_ENV / LOG_LEVEL のバリデーション、Paper Trading 用設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH）等を追加。
  - DB 関連の初期化処理を整備（monitoring テーブルの冪等初期化 init_monitoring_db を利用）。
  - utils/process_priority: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定、CPU affinity 固定ユーティリティを追加。権限不足などの失敗に対してはログでフォールバック。

- Changed
  - ExecutionEngine 起動フローを明確化（PID ファイル、停止フラグチェック、別スレッドでの実行・安全停止）。
  - 監視ループはモニタリング専用 DB を環境にかかわらず本番 sqlite_path を用いる設計に明示。

- Fixed
  - .env 読み込みの失敗時に警告を出すようにしてプロセスを継続できるように改善。
  - 各種集計クエリで NULL ハンドリングやゼロ除算を回避する保護を追加（research, tools 内の SQL）。

- Notes / Known issues
  - apply_sector_cap 内で価格が欠損 (0.0) の場合にエクスポージャーが過少見積りされる可能性がある旨を TODO コメントで明記（将来的に前日終値や取得原価でのフォールバックを検討）。
  - position_sizing では将来的に銘柄別 lot_size 対応を想定する TODO がある（現在はグローバル lot_size）。
  - news_nlp.score_news の実装は設計に沿った骨格（ウィンドウ計算、記事集約、API 呼び出し／リトライ設計）を含むが、処理の後半（記事フェッチや最終書き込み周り）が未完または部分的実装であることを示唆する箇所が存在する（このため Unreleased に分類）。
  - DuckDB を前提とした SQL を多用しているため、テーブル構成（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, trade_logs, risk_logs, system_status 等）の仕様に依存する。環境構築時にスキーマ整備が必要。

[0.1.0] - 2026-04-17
--------------------

- Added
  - プロジェクト初期リリース相当として以下を実装・公開。
    - コアパッケージ構成: execution, monitoring, portfolio, research, data (一部), tools, utils, ai。
    - 実行基盤:
      - run_execution.py: ExecutionEngine 起動スクリプト（BrokerFactory 経由で paper_trading と live を切り替え）。
      - run_monitoring.py: SystemMonitor 監視ループ起動スクリプト（ポーリング、停止フラグ、監視 DB 初期化）。
    - Portfolio construction:
      - 候補選定、等金額/スコア加重、ポジションサイズ計算（risk_based を含む）。
      - セクター上限適用とレジームに基づく投下資金乗数。
    - Research / Feature exploration:
      - モメンタム / ボラティリティ / バリュー計算、将来リターン、IC・統計サマリ機能。
    - Tools:
      - paper_verification_report: Paper Trading 検証レポート生成ツール（CLI）。
    - AI:
      - news_nlp: OpenAI を用いたニュースセンチメントスコアリングモジュール（設計・主要定数・ウィンドウ計算・API 周りの方針）。
    - 設定管理:
      - .env 自動ロード（.env, .env.local）、環境変数検証、Settings クラスによる一元化。
    - Utilities:
      - process_priority / set_cpu_affinity：プロセス優先度・CPU affinity 設定ユーティリティ。
    - DB:
      - DuckDB / SQLite を併用するデータアクセス基盤を採用（研究処理は DuckDB、監視/実行は SQLite を使用する設計）。

- Changed
  - なし（初回公開）。

- Fixed
  - なし（初回公開）。

Security
--------

- Settings._require により必須の機密環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定の場合は明示的に失敗する仕様。デプロイ時は .env 等で適切に設定してください。

参考
----

- 実行用の停止フラグ / PID ファイルは data/ 配下に配置される想定（run_monitoring.py, run_execution.py 内で参照）。
- 環境変数の主なキー:
  - KABUSYS_ENV (development | paper_trading | live)
  - MONITOR_POLL_INTERVAL
  - PAPER_FILL_MODE (instant | partial | never | reject)
  - PAPER_TRADING_SQLITE_PATH
  - OPENAI_API_KEY
  - DUCKDB_PATH / SQLITE_PATH
  - LOG_LEVEL

（この CHANGELOG は与えられたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートに合わせて適宜修正してください。）