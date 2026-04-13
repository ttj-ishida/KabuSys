CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。主なカテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security。

[Unreleased]
-------------
- ドキュメント整理・軽微なログ改善。
- テストやローカル実行での .env 自動読み込みを無効化できる環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD の取り扱いに関する注意書きを追記（挙動そのものは既存実装に依存）。
- その他、内部実装のログレベル調整や例外メッセージの微調整。

[0.2.0]
-------
Added
- AI ベースのニュースセンチメントスコアリング機能を追加（kabusys.ai.news_nlp）。
  - OpenAI (gpt-4o-mini) を用いたバッチ処理（最大 20 銘柄/API コール）。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）で raw_news を集約し、news_symbols と組み合わせて銘柄毎に要約して送信。
  - レスポンス検証、スコアクリッピング（±1.0）、部分失敗時に他銘柄の既存スコアを保護する更新ロジックを備える。
  - 429 / ネットワークエラー / タイムアウト / 5xx に対する指数バックオフリトライを実装。
  - API キーが未設定の場合は明示的に ValueError を送出。

- 研究用モジュール群を充実（kabusys.research）。
  - モメンタム、ボラティリティ、バリューのファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB を使用して prices_daily / raw_financials を参照）。
  - 将来リターン計算：calc_forward_returns（任意ホライゾン対応）。
  - IC（Information Coefficient）計算、ファクター統計集計ユーティリティ（calc_ic, factor_summary, rank）。
  - research パッケージから zscore_normalize を含む必要な関数をエクスポート。

- ポートフォリオ構築・サイズ決定機能を追加（kabusys.portfolio）。
  - 候補選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
  - ポジションサイズ計算（calc_position_sizes）：risk_based / equal / score の配分方式、lot_size、cost_buffer を考慮した aggregate cap スケーリングを実装。
  - リスク調整（apply_sector_cap, calc_regime_multiplier）：セクター集中チェック、レジームに応じた投下資金乗数。

- 実行エンジン・監視ランナーを追加。
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時の paper_db 分離と BrokerClientFactory によるブローカークライアント生成対応。起動時にプロセス優先度を高く設定。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。

- ユーティリティを追加・改善（kabusys.utils.process_priority）。
  - Windows / POSIX(Linux/Mac/FreeBSD) を吸収してプロセス優先度設定（set_process_priority）と CPU affinity 固定（set_cpu_affinity）を実装。
  - 設定に失敗した場合は警告ログでスキップするフェイルセーフな実装。

- 紙上検証レポートツールを追加（kabusys.tools.paper_verification_report）。
  - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率・送信率、P95 レイテンシなど）を集計してレポート出力。
  - 判定基準（PASS/FAIL）と閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）。
  - p95 計算、日付フィルタ、DB 存在チェックに対応。

Changed
- duckdb を研究・AI・実行系で利用する設計に統一（duckdb コネクションを受け渡すパターンを採用）。
- 実行開始時にプロセス優先度を最初に設定するように変更（run_execution/run_monitoring）。
- run_monitoring のデフォルトポーリング間隔は 60 秒。無効な環境変数値に対してデフォルトへフォールバックして警告ログを出す処理を追加。

Fixed
- position_sizing の aggregate cap スケーリングで残余キャッシュを考慮して lot_size 単位での追加配分を行う安全弁を実装（投資合計が available_cash を超えた場合の扱いを改善）。

[0.1.1]
-------
Added
- .env ローダーの強化（kabusys.config）。
  - export プレフィックス対応（"export KEY=val" 形式を許容）。
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理を実装し、クォート内のインラインコメントを無視するように改善。
  - クォートなしの値に対しては "#" の直前がスペースまたはタブの場合のみコメントとみなす挙動を導入。
  - .env と .env.local の読み込み優先順位を明確化（OS 環境変数 > .env.local > .env の順）。既存 OS 環境変数は protected として上書きを防止。

Changed
- Settings に各種プロパティを追加 / バリデーション強化。
  - PAPER_FILL_MODE の許容値検証（instant/partial/never/reject）。不正値は ValueError。
  - KABUSYS_ENV の許容値検証（development, paper_trading, live）。不正値は ValueError（起動時に早期に検出）。
  - LOG_LEVEL の許容値検証。
  - paper_sqlite_path, duckdb_path, sqlite_path, pid_file_path 等の Path 解決を Path.expanduser を使って統一。

Fixed
- .env ファイル読み込みでファイルオープン時の OSError を警告として扱い処理継続するよう修正（例外の伝播を防止し、読み込み失敗時はスキップ）。

[0.1.0] - Initial release
-------------------------
Added
- プロジェクト初期構成と主要機能を実装。
  - 基本設定管理モジュール（kabusys.config）: プロジェクトルート検出、.env 自動読み込み、Settings クラス。
  - パッケージメタ情報（__version__ = "0.1.0"）。
  - Portfolio モジュール（選定/重み/サイズ決定/リスク調整）を実装（kabusys.portfolio.*）。
  - Research 基本機能（factor_research と初期ユーティリティ）。
  - 実行・監視・ユーティリティの基礎（ExecutionEngine 関連のスクリプト、SystemMonitor 呼び出しパターン、process_priority ユーティリティの原型）。
  - tools として paper_verification_report の最初の実装。

Fixed
- 初期の各種バグ修正、基本的なログと例外メッセージの整備。

Breaking Changes
- Settings の環境変数検証を厳格化（無効な値で ValueError を送出するようにしたため、従来は黙って動いていた値が原因で起動時に停止する可能性があります）。KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE の設定を確認してください。

Notes
- 実行時の DB パス・API キー・PID ファイルなどは環境変数で設定可能です。各スクリプトの docstring と Settings のプロパティを参照してください。
- Paper Trading 用の DB は本番 DB と分離する設計になっているため、KABUSYS_ENV=paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- OpenAI を利用する ai.news_nlp は API キー（OPENAI_API_KEY）を必要とします。未設定時は明示エラーになります。

--- 
上記はリポジトリ内ソースコードの実装内容から推測して作成した変更履歴です。実際のリリース日・バージョン運用ルールに合わせて適宜調整してください。