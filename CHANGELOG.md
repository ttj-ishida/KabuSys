CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日を示します。内容はソースコードから推測してまとめたものであり、実際のコミット履歴に基づくものではありません。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-16
--------------------

Added
- 基本パッケージ初期リリース。
- 実行／監視用エントリポイントを追加。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。Paper Trading 環境時は MockBrokerClient を利用し、paper_trading 用の専用 SQLite DB（data/paper_trading.db, 環境変数で上書き可）に記録する。停止フラグ／PID 管理、スレッドでのエンジン実行をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番 sqlite_path を使用する設計。
- 設定管理モジュールを追加（kabusys.config）。
  - .env 自動読み込み（プロジェクトルートの検出: .git または pyproject.toml を基準）。.env / .env.local 読み込みの優先・上書きルール、OS 環境変数の保護機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - 各種設定アクセス（DB パス、PID/kill フラグ、しきい値、環境種別、Paper Trading 設定等）をプロパティとして提供。入力検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装。
- ポートフォリオ構築ユーティリティを追加（kabusys.portfolio）。
  - portfolio_builder: 候補選定（score 降順、同スコアは signal_rank 昇順）、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分にフォールバック）を提供。
  - risk_adjustment: セクター集中制限（セクターごとの既存エクスポージャー計算と候補除外）、レジーム乗数計算（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは 1.0 にフォールバック）を提供。
  - position_sizing: risk_based / equal / score ベースの株数計算、単元株（lot_size）丸め、1銘柄上限・全体投下合計のスケールダウン（aggregate cap）ロジック、コストバッファの考慮、現有ポジション差分発注算出を実装。
- 研究（research）モジュールを追加。
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 経由で計算する関数を実装。DuckDB による SQL ベース計算で pandas 等外部依存を避ける設計。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）、ファクターの統計サマリ、ランク関数を実装。小数丸めや ties の処理を考慮した安定的実装。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加。
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ保存する処理を実装。1回あたり最大 20 銘柄バッチ、記事・文字数上限を設けトークン肥大化に対処。
  - API 呼び出しのリトライ（429 / ネットワーク / 5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時のデータ保護（対象コードに限定した DELETE→INSERT）などフェイルセーフ設計を採用。
  - ニュース収集ウィンドウ（JST基準の前日15:00〜当日08:30）を厳密に計算し、ルックアヘッドバイアスを防止するために内部で datetime.today() 等を参照しない実装方針を採用。
- ユーティリティを追加。
  - process_priority: Windows / POSIX（Linux / macOS / FreeBSD）を吸収するプロセス優先度設定と CPU affinity 設定関数を提供。権限不足や未実装環境では警告を出してスキップ。
- ツールを追加。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツール。稼働率、注文成功率、送信率、P95 レイテンシ等の指標を計算して標準出力にレポートを出す。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を組み込み。日付フィルタと DB パスオプション（--db、PAPER_TRADING_SQLITE_PATH）をサポート。

Changed
- DuckDB を分析用途の主要な内部データベースとして採用（prices_daily / raw_financials 等の高速集計に利用）。
- Execution / Monitoring 起動時にプロセス優先度を最初に「high」に設定する処理を導入（プラットフォーム差分は utils.process_priority が吸収）。
- run_monitoring のポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で制御。無効値や 0 / 負数は警告してデフォルト 60 秒にフォールバックするバリデーションを追加。
- 設定読み込みルールを明確化：OS 環境変数が最優先、.env.local が .env を上書き。保護対象キー（既存の OS 環境変数）は上書きされない。

Fixed
- スコア重み合計が 0 の場合の配分ロジックにフォールバックを追加（calc_score_weights がゼロ総和時に等分配へフォールバックして警告を出す）。
- position_sizing における aggregate cap 適用時のスケーリングと端数処理を実装（lot_size 単位での安定した再配分ロジックを導入）。
- ニューススコアリングでの部分失敗時に他銘柄の既存データを消してしまうリスクを回避（書き込み前に対象コードに限定して削除→挿入する戦略）。
- .env パーサーの改善：export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、無効行の安全スキップ等を実装。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定の場合は明示的な例外を返すことで誤動作を防止。

Notes / Known limitations
- 一部の関数は外部データ（prices_daily, raw_financials, raw_news, trade_logs, system_status 等）のスキーマに依存するため、データ投入・テーブル定義が必要です。
- position_sizing の価格欠損（price==0.0）に対するフォールバックは TODO コメントが残っており、将来的に前日終値等の価格フォールバックを検討予定。
- news_nlp の全文処理は API レスポンスのフォーマットに強く依存する（厳密な JSON 出力を前提）。API 側の振る舞いにより堅牢化が必要な箇所があります。
- run_monitoring は監視データの記録に本番 sqlite_path を使用するため、テスト実行時は設定に注意してください。

Authors
- 初期実装: kabusys 開発チーム（ソースコード内のモジュール群に基づく推測）

LICENSE
- （リポジトリに付随する LICENSE を参照してください）