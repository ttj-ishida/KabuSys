Keep a Changelog
=================

すべての有意な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。パッケージ名: `kabusys`（__version__ = 0.1.0）。
- パッケージ構成（主要モジュールを公開）:
  - kabusys.config: 環境変数 / .env 管理と Settings API を提供。
    - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
    - .env ファイルのパース機能（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
    - 必須環境変数チェック (`_require`) と Settings によるプロパティアクセス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
    - 環境変数の妥当性チェック（KABUSYS_ENV 値検証、LOG_LEVEL 検証）。
  - kabusys.ai:
    - news_nlp モジュール:
      - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）でバッチセンチメント解析を実行。
      - チャンク処理（最大 20 銘柄／回）、1銘柄当たり記事数と文字数の上限（10 件、3000 文字）。
      - JSON Mode レスポンスのバリデーション、スコアクリップ（±1.0）、失敗時のフォールバック（処理継続）。
      - テストしやすさのため _call_openai_api を差し替え可能。
    - regime_detector モジュール:
      - ETF 1321（Nikkei）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）をスコアリング。
      - DuckDB からのデータ取得、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - API リトライ（指数バックオフ）、API 失敗時は macro_sentiment = 0.0 にフォールバック。
  - kabusys.data:
    - calendar_management:
      - JPX カレンダー管理（market_calendar）と営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - DB 登録優先、未登録日は曜日ベースでフォールバック。
      - calendar_update_job による J-Quants API 差分取得と保存、バックフィルや健全性チェックを実装。
    - pipeline / etl:
      - ETLResult データクラスによる ETL 実行結果の集約（取得件数、保存件数、品質問題、エラー一覧）。
      - ETL パイプラインのユーティリティ（差分取得、バックフィル、品質チェックの枠組み）。
    - etl.py で ETLResult を再エクスポート。
  - kabusys.research:
    - factor_research:
      - モメンタム（1M/3M/6M のリターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、バリュー（PER, ROE）などのファクター計算関数（DuckDB 上で完結）。
      - 関数: calc_momentum, calc_volatility, calc_value（いずれも prices_daily / raw_financials を参照）。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）。
- DuckDB を主要なストレージ層として利用する実装（各モジュールは DuckDB 接続を受け取る）。
- API 呼び出しに対する堅牢化:
  - リトライ/エクスポネンシャルバックオフ（429/ネットワーク/タイムアウト/5xx を考慮）。
  - レスポンスバリデーション（JSON パース、期待フィールドのチェック、未知コード無視）。
  - フェイルセーフな挙動（API 失敗時も例外を投げずスコアをスキップまたはゼロ埋め）。
- テスト支援:
  - OpenAI 呼び出し部分はモジュール内の private 関数をパッチ可能に実装（unittest.mock.patch を想定）。
- ロギングと安全なトランザクション:
  - DuckDB への書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の制御）。
  - 失敗時は ROLLBACK を試み、失敗ログを出力。

Changed
- 初版のため該当なし。

Fixed
- .env パーサが以下を正しく扱うように実装:
  - export プレフィックス、行頭/行末の空白、コメント処理（クォート内の # を無視）、クォート内のバックスラッシュエスケープ。
  - 不正行の無視と明示的なエラーハンドリング（ファイル読取失敗時は警告出力）。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- 環境変数に API キーやパスワードを設定する設計:
  - 必須: OPENAI_API_KEY（API 呼び出し用）、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID。
  - 自動 .env 読み込みは便利だが、機密情報の取り扱いに注意。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定可能。
- OpenAI の呼び出しにタイムアウトと最大リトライを設定し、5xx などのサーバーエラーにはバックオフで再試行する実装。

Migration Notes / 使用上の注意
- 必要な環境変数をセットしてください（例）:
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB パス:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可能）
  - SQLite（監視用）: data/monitoring.db（環境変数 SQLITE_PATH で上書き可能）
- OpenAI モデルは gpt-4o-mini を使用（将来的に変更される可能性あり）。
- 各 AI スコア処理はルックアヘッドバイアスを避ける設計（datetime.today()/date.today() を直接参照しない）。呼び出し時は明示的に target_date を渡してください。
- DuckDB の executemany の挙動（空パラメータ不可）に対する対応を行っているため、部分成功時でも既存スコアを不必要に消さないように配慮されています。
- 監視/ロギングを有効にすると詳細情報が出力されます（INFO/DEBUG レベルで実行可能）。

既知の制限
- OpenAI 呼び出し回りは外部 API に依存するため、ネットワークや API 仕様の変更により動作が影響を受ける可能性があります。テストでは _call_openai_api を差し替えてモック化してください。
- 一部 SQL で DuckDB のバージョン差異に注意（配列バインド等）。互換性を取るために実装上の工夫（executemany による個別 DELETE 等）を行っています。

Contributors
- 初期実装（初回リリース）：開発チーム

（注）この CHANGELOG はコードベースの内容から推測して作成しています。細かな API 仕様や追加ドキュメントは実際のリポジトリの README やドキュメントを参照してください。