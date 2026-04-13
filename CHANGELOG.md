CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
このファイルはコードベース（src/kabusys/*）の現在の実装内容から推測して作成しています。実際のコミット履歴ではなく、実装された主な機能・改善点・既知の注意点をまとめたリリースノートです。

[Unreleased]
-------------

（現時点では未リリースの変更はありません。以下は初回公開想定の内容です。）

[0.1.0] - 2026-04-13
--------------------

Added
- 実行系・監視系の実行スクリプトを追加
  - run_execution.py: ExecutionEngine の起動エントリポイント。環境に応じて paper_trading 用の専用 SQLite DB を使用し（本番 DB と分離）、BrokerClient のファクトリで本物のブローカーまたはモックを選択してセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番の sqlite_path を使用して監視テーブルを初期化する。
- 設定管理モジュールを追加（config.py）
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local が .env を上書き）
  - export 形式・クォート・インラインコメントに対応した .env パーサを実装
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 / PID/KILL ファイルパス / 環境種別判定 等）
  - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）
- Execution 系コアコンポーネントのスケルトンを追加
  - OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine（呼び出し側の組み立てを run_execution で実施）
  - RiskConfig のデフォルト値設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 等）と初期ポートフォリオ値の broker からの取得
- 監視 DB 初期化ユーティリティを導入（init_monitoring_db を呼び出して監視テーブルの存在を保証）
- ユーティリティ: プロセス優先度 / CPU affinity 設定モジュールを追加（utils/process_priority.py）
  - Windows / POSIX を吸収し、簡易な API（set_process_priority, set_cpu_affinity）を提供
  - 権限不足や非対応環境時に警告を出して処理をスキップするフェイルセーフ
- ポートフォリオ構築ライブラリを追加（kabusys.portfolio）
  - portfolio_builder.py: シグナル選定（select_candidates）と重み計算（等金額/スコア加重）
  - risk_adjustment.py: セクター上限適用（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）
  - position_sizing.py: 銘柄別発注株数計算（risk_based / equal / score の allocation_method をサポート）、単元株丸め、aggregate cap によるスケーリング、cost_buffer の考慮
- リサーチ機能（kabusys.research）を追加
  - factor_research.py: モメンタム / ボラティリティ / バリュー等のファクター計算を DuckDB 上で実行する関数群（calc_momentum, calc_volatility, calc_value）
  - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、統計サマリ（factor_summary）、ランク関数（rank）
  - DuckDB を使った SQL+Python のハイブリッド実装で大量データの集計に適した設計
- AI ニュース NLP スコアリング（kabusys.ai.news_nlp）を追加
  - raw_news / news_symbols から記事を集約し、OpenAI API（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込むロジック
  - バッチ処理（最大 20 銘柄/呼び出し）、記事数/文字数のトリム、スコアの ±1.0 クリップ、レスポンス検証、エクスポネンシャルバックオフによるリトライを実装
  - 日時ウィンドウ計算（JST ベース→UTC 変換）や look-ahead バイアス防止の設計を採用（date.today() を参照しない）
- Paper Trading 検証ツールを追加（kabusys.tools.paper_verification_report）
  - SQLite（Paper Trading 用 DB）から稼働率・注文成功率・送信率・レイテンシ等を集計し、閾値判定（PASS/FAIL）を行う CLI ツール（コマンドライン引数で期間指定可能）
  - P95 計算、各種安全ハンドリング（テーブル未存在時のエラー回避）を実装

Changed
- パッケージ初期化と公開 API を整理
  - kabusys.__init__.py に __version__ を設定（"0.1.0"）し、主要サブパッケージを __all__ に列挙
  - kabusys.research のトップレベルエクスポートを整備（zscore_normalize 等を含む）

Fixed / Hardened
- 環境変数読み込みの堅牢化
  - _parse_env_line により export プレフィックス、クォート中のエスケープ、インラインコメントの正しい扱いを実現。見かけ上の無効行は無視する挙動を明確化。
  - .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行うため、CWD に依存しない実行が可能
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用）
- 各種入力値の検証を追加
  - Settings.env / LOG_LEVEL / PAPER_FILL_MODE / calc_forward_returns の horizons 等で不正値を早期に例外化
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）時にデフォルトへフォールバックしてログ出力
- ポジションサイズ算出とスケーリング周りを堅牢化
  - lot_size 単位で丸め、aggregate cap 超過時にスケール＆残差再配分ロジックを導入
  - price 欠損（0 または None）時はスキップする安全策を採用
- Research / Factor 計算での欠損データ対処
  - 移動平均窓や ATR 計算で必要行数が不足する場合は None を返すようにして downstream が壊れない設計
- AI スコアリングでの安全策
  - OpenAI API キー未指定時は明示的な ValueError を送出
  - API 呼び出し失敗（429/タイムアウト/5xx）でリトライ、最終的に失敗しても他データを壊さず継続するフェイルセーフ

Removed
- （該当なし）

Security
- 環境変数の自動上書きを行う際、OS 環境変数を protected として .env.local / .env の上書きを防ぐ仕組みを導入（テストやデプロイ時の意図しない上書きを回避）

Notes / Known limitations
- run_monitoring は監視用 DB に常に本番の sqlite_path を使用する仕様（意図的）。開発環境から監視データを書き込まないよう注意が必要。
- position_sizing の price 欠損時の TODO: price が欠損するとエクスポージャーや発注判定が過少見積りされるため、将来的に前日終値や取得原価等のフォールバック価格を導入する予定。
- ai/news_nlp の実装はレスポンス JSON の形式に依存するため、OpenAI モデルや API レスポンス仕様の変更があると追加の検証・修正が必要。
- DuckDB 側の executemany に関する注意（コメントにある通り、空 params を渡さない前提）や、Paper Trading 用 DB と本番 DB の完全分離に関する運用ルールを遵守すること。
- set_cpu_affinity / set_process_priority は権限やプラットフォームに依存するため、失敗時は警告ログを出して処理をスキップする。

参考（簡易使用例）
- 監視ループを起動:
  - MONITOR_POLL_INTERVAL を設定（秒）可能。例: export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Execution を起動（paper_trading 環境時は Mock を使用）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

以上。今後のリリースでは、テストカバレッジ・エラーメトリクス・価格フォールバックや銘柄別 lot_size 対応などを改善予定です。必要であればこの CHANGELOG を英語版や細かいセクション分割で整形します。