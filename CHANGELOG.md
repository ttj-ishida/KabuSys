CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
このプロジェクトは現在セマンティックバージョニングに従っています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初回リリースを追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、公開モジュール: data, research, ai, execution, strategy, monitoring（__all__ に基づく）。
- 設定/環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しません。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、行末コメント処理等。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_*、DUCKDB_PATH、SQLITE_PATH、PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、監視用 PID/KILL フラグ、閾値、KABUSYS_ENV、LOG_LEVEL など）。
  - PAPER_FILL_MODE の有効値検証（"instant" | "partial" | "never" | "reject"）や KABUSYS_ENV/LOG_LEVEL のバリデーションを実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）に JSON Mode でリクエストして銘柄ごとのセンチメント（ai_scores）を算出・書き込みする処理を実装。
    - タイムウィンドウは target_date に対して「前日 15:00 JST ～ 当日 08:30 JST」を対象（UTC に変換して DB クエリに使用）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数制限・文字数トリム、JSON レスポンスのバリデーションとスコアクリッピング（±1.0）を実装。
    - API エラー（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフリトライや、失敗時のフェイルセーフ（該当チャンクをスキップ）を実装。
    - テストで差し替え可能な _call_openai_api（unittest.mock.patch に対応）を用意。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。API キーは引数または環境変数 OPENAI_API_KEY から解決。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（'bull'/'neutral'/'bear'）を判定し market_regime テーブルへ冪等的に書き込む処理を実装。
    - マクロニュースの抽出はニュース NLP のタイムウィンドウを再利用（calc_news_window を import）。
    - OpenAI 呼び出しは独立実装（news_nlp と内部実装を共有しない設計）。
    - API エラーやパース失敗は macro_sentiment = 0.0 でフォールバックするフェイルセーフを実装。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時は 1 を返す。API キーは引数または環境変数 OPENAI_API_KEY。
- Data モジュール (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを公開（ETL の対象日や取得/保存件数、品質問題、エラー一覧を保持）。
    - ETL の方針説明と基礎実装を用意（差分更新、バックフィル、品質チェック連携、id_token 注入でのテスト性向上など）。
    - ETLResult.to_dict による監査ログ向け変換を実装。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを使った営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック（週末除外）を使用し、一貫した挙動を保証。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル日数、見込み日数等の安全パラメータを設定。
  - jquants_client と quality などのクライアント関数と連携する設計。
- Research モジュール (kabusys.research)
  - ファクター計算群を実装・公開:
    - calc_momentum(conn, target_date) : 1M/3M/6M リターン、ma200_dev（200日 MA 乖離率）
    - calc_volatility(conn, target_date) : 20日 ATR、相対 ATR、平均売買代金、出来高比率
    - calc_value(conn, target_date) : PER、ROE（raw_financials を使用）
  - 特徴量探索/統計ユーティリティ:
    - calc_forward_returns(conn, target_date, horizons=None) : 将来リターン（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col) : スピアマンランク相関（IC）
    - factor_summary(records, columns) : 各ファクターの基本統計量（count/mean/std/min/max/median）
    - rank(values) : 同順位を平均ランクで扱うランク化ユーティリティ
  - zscore_normalize は kabusys.data.stats から再エクスポート（research パッケージの一部として利用可能）。
- ロギングとエラーハンドリング
  - 各処理で詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のパターンで冪等性を意識し、例外時は ROLLBACK を試みる実装。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI API キーの扱い:
  - OpenAI の API キーは score_news / score_regime の引数か環境変数 OPENAI_API_KEY で指定する必要があります。キーが未設定の場合は ValueError を送出して処理を中断します。

注意・移行ガイド
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings のプロパティで参照）
  - OpenAI を利用する機能を使う場合は OPENAI_API_KEY を設定してください（score_news, score_regime）。
  - 自動 .env ロードを無効化したいテスト等の用途では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルトのデータベースパス:
  - DuckDB のデフォルト: data/kabusys.duckdb
  - 監視用 SQLite のデフォルト: data/monitoring.db
  - Paper Trading 用 SQLite のデフォルト: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH による上書き可）
- Paper Trading:
  - PAPER_FILL_MODE（instant | partial | never | reject）で MockBrokerClient の挙動を制御します。値が不正な場合は起動時に ValueError が発生します。
- DuckDB 互換性:
  - 一部実装（executemany に空リストを渡さない等）は DuckDB の既知の制約（0.10 系など）を考慮しているため注意してください。
- 時間・日付取り扱い:
  - ルックアヘッドバイアスを防ぐ設計として、date.today() / datetime.today() を直接参照しない実装方針に基づいた関数設計になっています。常に target_date を明示的に渡して利用してください。

今後の予定（例）
- AI モデル周りの抽象化やリクエスト効率化、追加指標・ファクターの拡充。
- ETL の実行スケジューリング実装、品質チェックルールの追加強化。

--- 

この CHANGELOG はコードベースからの推測に基づいて作成しました。必要に応じて項目の追加・修正を行ってください。