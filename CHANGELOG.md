# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
なお、以下の内容は提示されたソースコードから推測してまとめたものであり、実際のコミット履歴ではありません。

未リリース
---------

- なし

[0.1.0] - 2026-04-16
-------------------

Added
- 基本アプリケーション初期リリース相当の機能群を追加
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
- 実行系・監視系エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db）に記録する仕組みを導入。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル監視による安全停止に対応。
- コンフィグ・環境変数管理
  - config.py: .env 自動ロード（.env → .env.local、OS 環境変数を保護）、.env パース機能を実装（コメント・クォート・export 形式対応）。各種設定プロパティ（DB パス、PaperTrading のモード、しきい値、KABUSYS_ENV/LOG_LEVEL バリデーション等）を提供。
- データベース連携
  - DuckDB 接続を受け取る設計を導入（research / ai / run スクリプトで利用）。
  - 監視用 DB 初期化: monitoring_db の初期化を起動時に行い冪等性を担保（init_monitoring_db 呼び出し）。
- 実装済みユーティリティ
  - utils/process_priority.py: プラットフォーム差を吸収したプロセス優先度設定および CPU affinity（set_cpu_affinity）ユーティリティを追加。Windows/Linux/macOS 等に対応し、権限不足や未対応環境を警告で扱う。
- ポートフォリオ構築機能（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額にフォールバックする挙動を持つ。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームは警告を出してフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、投下資金の aggregate cap スケールダウンアルゴリズム（再配分ロジック）を実装。コストバッファ（手数料・スリッページ見積り）に対応。
- リサーチ機能（DuckDB 前提）
  - research/factor_research.py: モメンタム、ボラティリティ、バリュー等のファクター計算（prices_daily / raw_financials を参照）を実装。200 日移動平均や ATR 等を SQL + Python で計算。
  - research/feature_exploration.py: 将来リターン（複数ホライズン）計算、IC（Spearman 的なランク相関）計算、ランク関数、ファクター統計サマリーを実装。外部ライブラリに依存しない実装。
  - research パッケージは zscore_normalize を data.stats から再エクスポート。
- AI ニューススコアリング（初期実装）
  - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチで問い合わせ、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む処理を実装。バッチサイズ、トークン肥大対策、429/5xx 等に対する指数バックオフリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ等の設計を含む。API キー未設定時に ValueError を送出。
  - ニュース収集ウィンドウ（JST → UTC 変換）ユーティリティ calc_news_window を提供。
  - （注）ファイル末尾が提示コードでは途中で切れており、処理の一部が未完（部分実装）であることを示唆。
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を行う。コマンドライン引数（--from/--to/--db）対応。
- ログ・例外処理の改善
  - run_monitoring.py / run_execution.py: 起動時にプロセス優先度を設定し、ループ中の例外を捕捉してログ出力し続行するフェイルセーフな実装。ポーリング間隔の環境変数検証（不正値はデフォルトにフォールバック）など。

Changed
- 設計上の注意点を明記（ソース内コメント／ドキュメント）
  - run_monitoring: 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する旨を明示（監視 DB の分離を行わない設計判断）。
  - .env 読み込み順序と保護（OS 環境変数の上書き防止）を明確化。
  - research / ai モジュールは DuckDB 接続を外部から渡す設計にして、本番の発注 API にアクセスしない安全設計を採用。
- 設定関連のバリデーション強化
  - Settings クラスで KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等に対する有効値チェックを追加。

Fixed
- 安全性・堅牢性の向上
  - run_monitoring のポーリングループで check_once() の例外を捕捉し続行するようにして、監視プロセスが一度のエラーで停止しないように修正（ログに例外トレースを出力）。
  - init_monitoring_db が呼び出されても冪等に動作する（監視テーブルが存在しない場合のみ作成する前提）。
  - calc_score_weights: 全銘柄のスコアが 0 の場合に等金額配分へフォールバックするようにしてゼロ除算等の事故を回避。
  - position_sizing: lot_size 単位での丸めや aggregate cap のスケーリング処理における端数処理を改善（残余キャッシュでの追加配分アルゴリズム導入）。
  - process_priority: 権限不足や未対応 OS でも安全にスキップするよう例外処理を追加。

Deprecated
- なし

Removed
- なし

Security
- ai/news_nlp.py: OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定の場合はエラーにより明示的に失敗するため、キー漏洩の防止を促す（環境変数利用を想定）。

Known issues / Notes
- ai/news_nlp.py は提示されたコードが途中で切れており（記事集約フェーズで途切れ）、実運用のためには残り処理（API 呼び出しループ、結果の書き込み等）の完成が必要。
- portfolio/risk_adjustment.apply_sector_cap: price_map に欠損（0.0）がある場合、エクスポージャーが過小評価される可能性がある旨の TODO コメントあり。将来的に価格フォールバックの導入を検討する必要あり。
- run_monitoring は監視に本番 sqlite_path を使用するため、テスト用途で監視を分離したい場合は実装/設定の見直しが必要。
- position_sizing の将来的拡張として銘柄別 lot_size を導入する TODO が記載されている。

---- 

この CHANGELOG は提示されたソースコードの内容・コメント・実装から推測して作成しています。実際のコミット履歴やリリースノートが別に存在する場合は、そちらを公式情報として優先してください。