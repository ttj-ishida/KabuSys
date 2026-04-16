CHANGELOG
=========
すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog のガイドラインに準拠しています。

フォーマット:
- 変更はセマンティックに分類（Added / Changed / Fixed / Removed / Security / etc.）
- バージョン見出しは [バージョン] - YYYY-MM-DD 形式

[Unreleased]
------------
（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-16
-------------------

Added
-----
- 初期リリース: KabuSys 基本機能群を追加。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、本番 DB と分離。  
    - BrokerClientFactory 経由でブローカークライアントを生成。エンジンはバックグラウンドスレッドで実行し、data/stop_requested.flag による外部停止をサポート。実行 PID のファイルパス指定をサポート。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視処理は KABUSYS_ENV に依らず本番 sqlite_path を参照。
- 設定管理
  - config.py: 環境変数と .env/.env.local の自動ロード機能を追加。プロジェクトルートを .git または pyproject.toml から探索。  
  - .env パーサー追加: export 形式、引用符付き値、インラインコメント処理に対応。
  - Settings クラスを提供し、各種設定（DB パス、API トークン、しきい値、環境種別など）をプロパティとして取得可能に。
  - 環境値検証: KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の入力検証を追加。
- ポートフォリオ構築
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等分配（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を追加。
  - portfolio.position_sizing: 各種配分方法（risk_based / equal / score）に基づく発注株数計算（calc_position_sizes）を追加。単元（lot_size）、max_position_pct、max_utilization、コストバッファを考慮した集計キャップ処理を実装。
- リサーチ機能
  - research.factor_research: モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクター計算を実装。DuckDB を用いた SQL ベースの実装。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）およびファクター統計サマリ（factor_summary）、ランク変換ユーティリティを実装。
  - research パッケージから zscore_normalize を再エクスポート。
- AI / ニュース
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む処理を追加（バッチ送信、リトライ、レスポンスバリデーション、スコアクリップなどの設計を含む）。ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を実装。
- ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数などを集計して標準出力でレポートを生成。コマンドライン引数 --from / --to / --db をサポート。既定の閾値（稼働率 99%、注文成功率 90% 等）による Pass/Fail 判定を実装。
- ユーティリティ
  - utils.process_priority: Windows / POSIX の差を吸収するプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を追加。失敗時は警告を出して安全にスキップする。

Changed
-------
- DB ハンドリングと分離
  - run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
  - run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用するため監視データは環境に依存せず一元管理される。
  - init_monitoring_db は冪等に監視テーブルを準備するよう利用（存在チェックを確実化）。
- 設定の自動ロード挙動
  - .env の読み込み順序は OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され自動上書きされない。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
- エラーハンドリング改善
  - run_monitoring のポーリングループで check_once() の例外をキャッチしてログ出力後に継続するようにし、監視ループの堅牢性を向上。
  - paper_verification_report はテーブルが存在しない場合に sqlite3.OperationalError を捕捉してデフォルト値を使ってレポート出力を継続する（欠損テーブルに対する耐性）。
- CLI / 起動時のプロセス
  - 実行スクリプト起動時にプロセス優先度を自動で "high" に設定するように変更（set_process_priority の呼び出しを追加）。
  - 停止フラグ（data/stop_requested.flag）および PID ファイルの利用を標準化。

Fixed
-----
- 環境変数パースの堅牢化
  - .env パーサーで export プレフィックス、引用符付値のバックスラッシュエスケープ、およびインラインコメント処理に対応。無効行は無視することで .env の柔軟な記述に対応。
- MONITOR_POLL_INTERVAL の妥当性チェック
  - ポーリング間隔に 0 以下や非数値が設定された場合は警告を出してデフォルト（60 秒）へフォールバックするようにした。
- OpenAI 統合の堅牢化（設計段階での記述）
  - API キー未設定時の明示的なエラー、リトライポリシー（429/ネットワーク/5xx）、バッチサイズ制御、スコアクリップなどを実装して部分障害時のフェイルセーフを確保。
- DuckDB 接続の導入
  - research / ai モジュールは DuckDB を利用する設計に整備。接続文字列に対して Path を渡して使用。

Known issues / TODO
-------------------
- risk_adjustment.apply_sector_cap のコメントにある通り、price が欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある。将来的に前日終値やコストベースでのフォールバックを検討する必要あり。
- position_sizing.calc_position_sizes: 現状 lot_size は全銘柄共通。将来的に銘柄別 lot_size を stocks マスタから受け取る設計へ拡張する予定（TODO 記載あり）。
- ai.news_nlp の処理は実装中の箇所があり得る（例えば記事取得フェーズの未完部分に対応する必要あり）。運用前に OpenAI API のレスポンス形式・費用対策・レート制限の本番検証を推奨。
- DuckDB の executemany に関するバージョン依存の制約に注意。大量挿入時は params が空でないことを事前にチェックする実装が必要。

Removed
-------
- （今回の初期リリースでは該当なし）

Security
--------
- 現在特にセキュリティ脆弱性は報告されていませんが、OpenAI API キー・ブローカ API パスワード等の機密値は環境変数で管理する設計となっています。.env をリポジトリにコミットしない運用を推奨します。

Notes
-----
- 本リリースはソースコードから推測して作成した初期 CHANGELOG です。実際のリリース時には運用上の注記（マイグレーション手順、環境変数必須項目、互換性ブレイクなど）を追記してください。