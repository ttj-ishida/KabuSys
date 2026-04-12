CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はコードベースから推測したリリース日（2026-04-12）を使用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-12
--------------------

Added
- 実行/監視の起動スクリプトを追加
  - run_execution.py：ExecutionEngine を起動するエントリポイントを追加。paper_trading 環境時は専用の MockBrokerClient と data/paper_trading.db を使用する挙動をサポート。
  - run_monitoring.py：SystemMonitor のポーリングループを起動するスクリプトを追加。環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書きをサポート（デフォルト 60 秒）。
  - 両スクリプトとも起動直後にプロセス優先度を "high" に設定する処理を呼び出す（set_process_priority）。

- 設定／環境変数読み込み機能を追加・強化（kabusys.config）
  - プロジェクトルートの自動検出機能を追加（.git または pyproject.toml を探索）。これによりパッケージ配布後でも .env 自動ロードが機能するように改良。
  - .env / .env.local の自動読み込みを実装。OS 環境変数を保護する仕組み（protected set）を導入。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルの行パーサを改良し、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（条件付き）に対応。
  - Settings クラスを導入し、各種設定をプロパティ経由で取得可能に（J-Quants / Kabu API / LINE / DB パス / 監視閾値 / 環境種別等）。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH などのキーを明示的に扱うように追加。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）
  - portfolio_builder：候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）。
  - risk_adjustment：セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier。
  - position_sizing：複数の配分方式（risk_based / equal / score）に対応した株数計算 calc_position_sizes。単元株（lot_size）、コストバッファ、aggregate cap（available_cash 超過時のスケールダウン）等を実装。

- 研究 / ファクター計算機能を追加（kabusys.research）
  - factor_research：モメンタム（1M/3M/6M, MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高系指標）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials から算出する関数群。
  - feature_exploration：将来リターン計算（複数ホライズン対応）、IC（Spearman rank によるランク相関）、ファクター統計サマリ（count/mean/std/min/max/median）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージの __all__ を整備して再利用を容易に。

- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) を用いたセンチメントスコアを ai_scores に書き込む処理を実装。
  - 処理の特徴：
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を正確に計算して記事を選定。
    - 銘柄ごとに記事をトリム（最大記事数・最大文字数）してトークン膨張を抑制。
    - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE）し、429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
    - レスポンスの厳格なバリデーション（JSON モードの results 配列、コードの既知性、スコアを数値で受け取る）を実施。
    - スコアは ±1.0 にクリップし、部分失敗があっても既存スコアを保護するため更新は対象コードのみを削除→挿入の方法で行う（部分的置換）。

- 監視・検証ツールを追加（kabusys.tools）
  - paper_verification_report.py：Paper Trading DB（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、P95 レイテンシ等を集計してレポート出力する CLI ツールを追加。期間指定（--from / --to）に対応。データ欠損やテーブル未存在時は適切に N/A を出力して継続可能。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を追加し、Windows と POSIX（Linux/Mac/FreeBSD）で優先度を共通インタフェースで扱えるようにした。権限不足等は警告ログでスキップ。
  - set_cpu_affinity(cpu_count) を追加。利用可能コア数より大きい値が指定された場合の挙動や権限エラーを考慮。

Changed
- 環境依存の DB 運用ポリシー
  - 監視処理（run_monitoring）は KABUSYS_ENV にかかわらず常に本番の sqlite_path（Settings.sqlite_path）を使用するように仕様を明確化。これにより監視データは本番 DB に集約される設計。

- Settings のバリデーション強化
  - KABUSYS_ENV の値を厳密に検証（development, paper_trading, live のみ許可）し、不正値は ValueError を送出するようにした。
  - LOG_LEVEL、PAPER_FILL_MODE 等も許容値チェックを導入し、不正値での稼働を防止する。

- duckdb / sqlite の利用方法
  - 各起動スクリプトで DuckDB と SQLite の接続確立とクローズを明示的に行うようにした。monitoring テーブル初期化（init_monitoring_db）は冪等に呼べるように調整。

Fixed
- MONITOR_POLL_INTERVAL の取り扱い改善
  - 環境変数 MONITOR_POLL_INTERVAL のパースで整数変換に失敗したり 0 以下の値が指定された場合にデフォルト（60 秒）にフォールバックするようにし、time.sleep に渡して ValueError が発生するのを防止。
  - 不正な値があった場合は警告ログを出力。

- レスポンスやデータ欠損時の堅牢性向上
  - research / feature_exploration、paper_verification_report、ai.news_nlp 等で、欠損データやテーブル未存在時に例外で停止しないよう適切に None を返す・例外を捕捉する処理を追加。
  - calc_score_weights で全スコアが 0 の場合は等金額配分にフォールバックして警告ログを出す。

- スケーリング時の端数処理（position_sizing）
  - aggregate cap 適用時に lot_size（単元）単位での丸め・残差配分ロジックを導入し、再現性を確保するため残差ソートの安定化（二次キーに code を使用）を行った。

Security
- OpenAI API キー取り扱い
  - news_nlp.score_news() は引数の api_key を優先し、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を発生させて誤った無認証呼び出しを防止。

Potential breaking changes / 注意事項
- Settings 自動ロード
  - パッケージ導入後も .env の自動読み込みが働くため、既存の実行環境では予期せぬ環境変数上書きが起きる可能性があります。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の許容値制限
  - 以前は任意の文字列を許容していた場合、"development" / "paper_trading" / "live" 以外の指定が ValueError となるため、環境変数の値確認が必要です。
- 監視 DB の扱い
  - run_monitoring は常に Settings.sqlite_path（本番設定）を使用します。監視データを分離したい場合は sqlite_path を変更するか実行ポリシーを見直してください。
- PAPER_FILL_MODE の厳格化
  - PAPER_FILL_MODE に不正な値を与えると起動時に例外が発生します。許容値は "instant" / "partial" / "never" / "reject" です。

Notes / Implementation details（参考）
- DuckDB を用いたファクター集計は SQL ウィンドウ関数を多用し、性能と簡潔さを両立しています（LAG/LEAD, AVG OVER, ROW_NUMBER 等）。
- news_nlp は API 呼び出しをチャンク化し、レスポンス検証とクリッピングを行うことでフェイルセーフかつ安定的なスコア投入を目指しています。
- position_sizing と risk_adjustment は PortfolioConstruction.md / StrategyModel.md の設計指針に沿った純粋関数群として実装され、外部状態に依存しません。

---

著者注:
本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のコミット履歴やバージョン管理ログがある場合は、そちらに基づいて正確な日付・バージョン・項目を追記・修正してください。