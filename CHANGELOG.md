CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下の内容は、提供されたコードベースの実装コメント・実装内容から推測して作成した変更履歴です（正確なコミット履歴ではありません）。

Unreleased
----------
（コードベースの現状から推測した最新の変更・実装内容）

Added
- 実行／監視用エントリポイントを追加 / 整備
  - run_execution.py: ExecutionEngine を起動するスクリプトを実装。KABUSYS_ENV が paper_trading の場合は paper 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視処理は環境に関わらず本番 sqlite_path を使用する旨を明示。
  - 停止用フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) による外部制御に対応。

- ポートフォリオ構築ロジック（純粋関数群）を追加
  - portfolio.portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio.position_sizing: position sizing 実装（risk_based / equal / score 対応）、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を用いた保守的コスト見積り。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。

- リサーチ機能を追加（DuckDB 前提）
  - research.factor_research: momentum / volatility / value ファクター計算を実装（prices_daily / raw_financials テーブル参照）。
  - research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、rank ユーティリティ。
  - DuckDB を使った SQL + Python 混合での高速処理を意図。

- AI ニュース NLP モジュールを追加
  - ai.news_nlp: raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析し、銘柄ごとにスコアを ai_scores テーブルへ書き込む処理を実装。バッチサイズ、トークン制御、リトライ（指数バックオフ）、レスポンス検証、スコアのクリップ（±1.0）など堅牢化の方針を含む。

- 運用ツールを追加
  - tools.paper_verification_report: Paper Trading の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。CLI オプションで期間・DB を指定可能。

- 設定/環境変数管理の強化
  - config.Settings: 多数の設定プロパティを実装（DB パス、paper_trading 用パス、PID ファイルパス、監視閾値、環境判定、PAPER_FILL_MODE の検証等）。
  - .env の自動ロード機構を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。.env/.env.local の読み込み順序と上書きポリシー、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサーを強化（export プレフィックス、シングル/ダブルクォート・エスケープ、コメント処理の改良）。

- プロセス優先度 / CPU affinity ユーティリティを追加
  - utils.process_priority: Windows/Linux（POSIX）差分を吸収して優先度設定（high/normal/low）と CPU affinity 設定を提供。許可エラーなどを安全にログ警告してスキップ。

Changed
- DB 初期化の冪等化
  - run_execution.py / run_monitoring.py で共通の init_monitoring_db() を呼び、監視用テーブルの存在を保証。何度呼んでも安全に初期化される前提。

- 実行時の堅牢性向上
  - run_monitoring.py の polling ループが check_once() 内の例外を捕捉してログ出力し、次のポーリングで再試行するようにして監視プロセスの継続性を確保。
  - run_execution.py のスレッド監視ループで停止フラグを検知すると ExecutionEngine.stop() を呼ぶ実装により、外部停止制御に対応。

Fixed
- 環境変数パースの不具合回避
  - .env パーサーがクォート付き値のエスケープやコメント処理を適切に扱うように改善（不正な .env 行を無視）。

- 無効なポーリング間隔へのフォールバック
  - MONITOR_POLL_INTERVAL が整数に変換できない、または 1 未満の値だった場合に警告を出してデフォルト（60 秒）にフォールバックする挙動を追加。

Known issues / Notes
- ai.news_nlp の score_news() 関数は、提供されたコード断片の末尾が途中で切れており実装が未完（ファイル終端で中断）。OpenAI API 呼び出し周りの最終処理（記事取得、バッチ送信、DB 書き込み）は未完の可能性があるため実稼働前に完成・テストを要する。
- position_sizing.calc_position_sizes 内の price 欠損時の注記: price が 0.0 の場合エクスポージャーが過少見積りになる可能性がある旨の TODO が残っている（前日終値等のフォールバック価格導入を検討）。
- DuckDB に対する executemany の制約（空パラメータの扱い）に関する注意がコード中コメントとして残っている。部分失敗時に既存データを保護する設計はあるが、運用時は手順の確認を推奨。
- calc_regime_multiplier は未知のレジームを 1.0（Bull 相当）でフォールバックし、警告ログを出す仕様。意図的な挙動だが確認必須。

0.1.0 - Initial release (推定)
--------------------------------
（プロジェクト初期公開に相当すると推測される機能セット）

Added
- 基本的なパッケージ構造の追加（kabusys パッケージ、サブモジュール export の整備）。
- settings モジュールによる環境変数ベースの設定読み取り基盤。
- 基本的なポートフォリオ構築・リサーチ・ユーティリティ関数群（上記参照）。
- Execution / Monitoring / ツール類の初期実装（run_execution / run_monitoring / paper_verification_report）。
- DuckDB / SQLite を利用したデータアクセス設計。

その他
- ロギングは基本 INFO レベルで初期化される想定。多数のデバッグログ（logger.debug）・警告（logger.warning）を配置し運用観察を容易にしている。

脚注
- 本 CHANGELOG はソースコードの実装内容とコメントから推測して作成したもので、正確なコミット単位の差分ではありません。実際のリリースノート作成時は Git のコミット履歴やタグ情報に基づく精査を推奨します。