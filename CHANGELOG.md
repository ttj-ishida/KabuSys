CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- 今後のリリースに向けた既知の改善点・TODO を記載しています（詳細は「既知の問題 / TODO」参照）。

0.1.0 - 2026-04-13
-----------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" のコアモジュールを実装。
  - 基本情報
    - パッケージバージョンを __version__ = "0.1.0" に設定。
  - 環境設定
    - kabusys.config.Settings：.env ファイルと環境変数からの設定読み込みを実装。
      - 自動ロード順序: OS環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読み込み無効化をサポート。
      - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、エスケープを適切に処理。
      - 各種設定プロパティ（DB パス、API トークン、監視閾値、環境判定等）を提供。
  - 実行入口スクリプト
    - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
      - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
    - run_execution.py：ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH、既定: data/paper_trading.db）を使用して本番 DB と分離。
      - ブローカークライアントは BrokerClientFactory により生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine.run_session() を呼び出して実行。
      - 起動時にプロセス優先度を "high" に設定する呼び出しを追加。
  - 監視関連
    - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの初期化を行う（冪等）。
    - run_monitoring は duckdb と sqlite の両方に接続して SystemMonitor を走らせる。
  - ユーティリティ
    - utils.process_priority：Windows / POSIX の差分を吸収したプロセス優先度設定と CPU affinity 設定を実装。
      - set_process_priority(level): "high" / "normal" / "low" をサポート。アクセス権限や未対応 OS の場合は警告を出してスキップ。
      - set_cpu_affinity(cpu_count): 指定コア数に固定。入力検証・エラー時の警告あり。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder
      - select_candidates：BUY シグナルをスコア降順で切り出す。
      - calc_equal_weights：等金額配分。
      - calc_score_weights：スコア正規化による配分（全スコア 0 の場合は等分にフォールバック）。
    - portfolio.risk_adjustment
      - apply_sector_cap：セクター集中上限チェック（既存ポジションの時価ベースで判定）と候補の除外ロジック。
      - calc_regime_multiplier：市場レジーム（bull/neutral/bear）に基づく投下資金乗数。
    - portfolio.position_sizing
      - calc_position_sizes：等配分/スコア加重/リスクベースの株数決定、単元株（lot_size）丸め、aggregate cap によるスケーリング。
      - スリッページ・手数料を考慮する cost_buffer パラメータをサポート。
  - リサーチ / ファクター計算
    - research.factor_research
      - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照して各種ファクターを出力。
      - 長期移動平均や ATR 等の窓関数に基づく実装。データ不足時は None を返す扱い。
    - research.feature_exploration
      - calc_forward_returns：将来リターン（horizons: デフォルト [1,5,21]）を計算する汎用実装。
      - calc_ic：ファクターと将来リターンのスピアマンランク相関（IC）を計算。レコード不足（<3）や分散ゼロは None を返す。
      - factor_summary：count/mean/std/min/max/median を計算する統計サマリー。
      - rank：同順位は平均ランクで処理するランク化ユーティリティ。
    - DuckDB を用いて SQL + Python のハイブリッドで効率的に集計を行う設計。
  - AI / ニュース NLP
    - ai.news_nlp
      - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI API（gpt-4o-mini）に対してバッチスコアリングを行う実装（score_news）。
      - バッチサイズ (_BATCH_SIZE=20)、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）、JSON モード期待、スコアを ±1.0 にクリップ。
      - 429 / ネットワークエラー / 5xx に対する指数バックオフのリトライ方針を採用。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
      - レスポンス検証と部分成功時のデータ保全（対象コードを絞った DELETE → INSERT）を想定した設計（フェイルセーフ）。
  - ツール
    - tools.paper_verification_report：Paper Trading 用の検証レポート生成ツールを追加。
      - コマンドライン実行可能（--from / --to / --db）。
      - システム稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）等を算出し PASS/FAIL 判定（閾値はソース内定義）。
      - DB が存在しない、またはテーブルがない場合に耐性を持つ（OperationalError をハンドリング）。
  - DB
    - sqlite3 と DuckDB を用途に応じて併用（監視・発注ログは SQLite、時系列集計は DuckDB を想定）。
  - ロギング
    - 起動時の環境情報出力、主要処理での INFO/DEBUG/WARNING/EXCEPTION を利用したログ記録を強化。

Changed
- 新規実装のため該当なし（初回リリース）。

Fixed
- 新規実装のため該当なし（初回リリース）。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キー等の機密情報は環境変数経由で扱う設計。.env 自動読み込みは必要に応じて無効化可能。

既知の問題 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーが過少見積りとなり、意図せずブロックが外れる恐れがある旨の TODO コメントあり。前日終値や取得原価を用いるフォールバックを検討する必要あり。
- portfolio.position_sizing:
  - lot_size を将来的に銘柄別に拡張する旨の TODO コメントあり（現在は全銘柄共通単元を想定）。
- utils.process_priority:
  - サポート OS は Windows と主要な POSIX（Linux/Mac/FreeBSD）に限定。未対応 OS では設定をスキップする。
- ai.news_nlp:
  - 大量 API 呼び出しに対するさらなる失敗耐性（部分コミット後のロールバック戦略など）や、OpenAI レスポンススキーマ変更への対応が今後の課題。
- 一部箇所にログ/エラーハンドリングはあるが、運用での観測性（メトリクス計測、アラート化）は追加検討の余地あり。
- ソース内に記載の TODO や注釈は将来的な改善候補（拡張ポイント）を示す。実装の完全性はユースケースに依存するため、運用前にパラメータ検証・統合テストを推奨。

補足
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴（コミットログやリリースノート）が存在する場合はそれに合わせて更新してください。