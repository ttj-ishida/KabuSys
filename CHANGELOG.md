Keep a Changelog
=================

すべての変更はこのファイルに記録しています。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

### Known / Work in progress
- ai/news_nlp.score_news の処理が途中で切れている箇所が確認されました（ソース末尾が不完全）。OpenAI API 呼び出し以降の集約・DB 書き込み処理は実装完了が必要です。
- position_sizing の将来的な拡張（銘柄ごとの lot_size を stocks マスタから取得するなど）は TODO コメントとして残っています。

0.1.0 - 2026-04-17
------------------

Added
- 基本パッケージ構成を追加
  - kabusys パッケージの初期バージョン（__version__ = "0.1.0"）。
- 実行用エントリスクリプト
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止。
    - 監視処理は環境にかかわらず本番 sqlite_path を使用する設計。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - 停止フラグ検知で実行を開始しない／実行中に停止する制御を実装。
    - エンジンは別スレッドで実行し、PID ファイル管理をサポート。
- 設定管理
  - kabusys.config.Settings：.env / .env.local 自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装：export プレフィクス対応、クォート文字列のエスケープ、インラインコメントの扱いなど堅牢化。
  - 多数の設定プロパティを提供（DB パス、PID ファイル、しきい値、PAPER_FILL_MODE 等）と入力検証（有効値チェック）。
- ユーティリティ
  - utils/process_priority.py：クロスプラットフォームでプロセス優先度（high/normal/low）および CPU affinity を設定するユーティリティを追加。未対応 OS や権限不足は警告ログでスキップする安全設計。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py：候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア合計が 0 の場合は等金額にフォールバック。
  - portfolio/risk_adjustment.py：セクター集中制限適用（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。未知レジーム時は警告ログとフォールバック。
  - portfolio/position_sizing.py：発注株数決定ロジックを実装（risk_based, equal, score）。単元株（lot_size）丸め、aggregate cap によるスケールダウン、端数配分アルゴリズムを実装。
- リサーチ／特徴量
  - research/factor_research.py：モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB SQL ベース）。
  - research/feature_exploration.py：将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリ、ランク関数を実装。外部依存なしで標準ライブラリのみで完結。
  - research パッケージのエクスポート設定を追加。
- AI ニュース NLP（部分実装）
  - ai/news_nlp.py：raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む設計を追加。バッチ処理、チャンクあたり最大銘柄数、スコアクリップ、リトライ（指数バックオフ）、出力 JSON 検証等を実装。
  - ニュース時間ウィンドウ計算関数 calc_news_window を実装（JST 基準の UTC 変換）。
- Paper Trading 向けツール
  - tools/paper_verification_report.py：paper_trading DB を解析して検証レポートを生成する CLI ツールを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などの指標を算出し、閾値に基づく PASS/FAIL 判定を出力。DB が存在しない／テーブルが無い場合のフォールトトレランスを実装。
- DB/監視サポート
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出し、監視用テーブルの存在を冪等に保証。

Changed
- 環境変数のデフォルトとバリデーションを明確化
  - MONITOR_POLL_INTERVAL の不正値は警告ログを出しデフォルト（60 秒）にフォールバックする実装。
  - PAPER_FILL_MODE の有効値検査（instant/partial/never/reject）を実装し、無効値で ValueError を送出。
  - KABUSYS_ENV, LOG_LEVEL 等の値チェックで無効な値は例外を発生させる（早期検出）。
- 実行時優先度設定は起動直後に行う（run_monitoring/run_execution）。

Fixed / Robustness improvements
- .env 読み込みでファイルアクセス失敗時に警告を出し処理を継続するように変更（テスト・運用での堅牢性向上）。
- calc_score_weights：全銘柄のスコアが 0 の場合に等金額配分へフォールバックして warning を出力（NaN/ゼロ除外）。
- apply_sector_cap：unknown セクターはセクター上限の適用対象外とし、既知セクターのみで判断するように仕様明示。
- set_process_priority / set_cpu_affinity：権限不足や未対応機能での失敗をキャッチして警告ログを出す安全設計。
- calculational functions（research / portfolio / position sizing）でデータ欠損（価格不在・0 など）時にスキップする挙動を統一してログでデバッグ出力を行うように改善。
- paper_verification_report：DuckDB/SQLite のテーブルが存在しない場合に OperationalError をハンドリングしてレポートを継続生成するように改善。

Removed
- 該当なし

Security
- OpenAI API キー取得は引数優先→環境変数 OPENAI_API_KEY の順。未設定時は ValueError（安全な失敗）を返す実装。

Notes / Migration
- Paper Trading を行う際は KABUSYS_ENV=paper_trading を設定すると、run_execution は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用します。これにより本番 DB と記録が完全に分離されます。
- 自動 .env ロードが不要／望ましくない環境（CI 等）では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ai/news_nlp.score_news は現状で途中実装のため、本番運用前に未実装部分の完成が必要です。

Acknowledgements / TODO
- ai/news_nlp.score_news の残り実装（記事集約 → OpenAI 呼び出し → レスポンス検証 → DuckDB 書き込み）の完了が必要。
- position_sizing の lot_size を銘柄別に指定する設計への拡張（TODO コメントあり）。
- さらに詳細なログレベル運用とモニタリングの可観測性向上を今後検討。

--- 

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のコミット履歴がある場合は、コミットログに基づくより正確な変更履歴の記載を推奨します。