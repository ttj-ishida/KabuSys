CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

履歴の解釈はソースコードから推測して作成しています。実装上の詳細（関数名、挙動、制約など）に基づき主要な追加点・設計方針・既知の制限を明記しています。

Unreleased
----------

-（なし）

0.1.0 - 2026-03-29
-----------------

初期リリース。以下の主要機能・モジュールを実装・公開。

Added
- パッケージ基盤
  - kabusys パッケージ公開（__version__ = 0.1.0）。
  - __all__ に data, strategy, execution, monitoring を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルと環境変数からの自動ロード機能を実装。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理）。
  - Settings クラスを提供し、必須環境変数取得（_require）、既定値、検証（KABUSYS_ENV, LOG_LEVEL 等）を実装。
  - データベースパス（DUCKDB_PATH/SQLITE_PATH）、Slack/各種 API トークンなど主要設定をプロパティで公開。

- AI 系（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたり記事数・文字数制限（上限: 記事数=10, 文字=3000）。
    - JSON Mode（厳密 JSON）でのレスポンス検証と堅牢なパース（余計な前後テキストからの復元処理含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
    - ai_scores テーブルへの冪等書き込み（DELETE→INSERT、部分失敗時の保護）。
    - タイムウィンドウ（JST 前日15:00～当日08:30）を UTC に変換して DB を参照するユーティリティを実装（calc_news_window）。
    - テスト容易性を考慮し、OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ保存。
    - マクロNEWS はキーワードフィルタで抽出（複数キーワードリストを実装）。
    - OpenAI 呼び出しは model=gpt-4o-mini、JSON レスポンスのパースとエラーハンドリング（リトライ/フォールバック macro_sentiment=0.0）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等フロー。失敗時は ROLLBACK を試行。
    - ルックアヘッドバイアス防止の設計（target_date 未満のデータのみ使用、date.today() を利用しない）。

- Data / ETL / カレンダー（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダー情報がある場合はそれを優先、未登録日は曜日ベースでフォールバック（週末は非営業日扱い）。
    - next/prev で最大探索日数の上限を設定し無限ループを防止。
    - 夜間バッチ calendar_update_job を実装: J-Quants API から差分取得→保存（バックフィル・健全性チェックあり）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを公開（取得数・保存数・品質チェック結果・エラー一覧などを保持）。
    - 差分取得、バックフィル、品質チェック、冪等保存の設計方針を反映した実装。
    - DuckDB の存在確認や最大日付取得などのユーティリティを提供。
    - jquants_client と quality モジュール経由で API 取得・保存・検査を行う想定。
  - jquants_client を利用する想定での連携ポイントを用意（fetch/save の呼び出し箇所を保持、例外ハンドリングあり）。

- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の prices_daily / raw_financials を参照する SQL ベースの実装。
    - 足りないデータは None を返す等の堅牢な設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリで実装。ランクの同順位は平均ランクで処理。

Changed
- （初回リリースのため「変更」はなし）

Fixed
- （初回リリースのため「修正」はなし）

Security
- OpenAI API キー等の機密情報は環境変数経由で取得する設計。
- .env 自動読み込み時、現行の OS 環境変数は既定で保護（上書き不可）される仕組みを導入。

Notes / Known limitations（既知の制約）
- 外部依存:
  - DuckDB を前提とする（DuckDB のバインド振る舞いに依存する実装箇所あり。例: executemany の空リスト禁止への対処）。
  - OpenAI（gpt-4o-mini）へ実際にリクエストを送る設計。API 呼び出しに関連する課金やレート制限に注意。
  - J-Quants クライアント（jquants_client）の実体実装は外部依存で、fetch/save の挙動に依存。
- タイムゾーン:
  - データベース内の日時は UTC 前提（news ウィンドウ計算などで UTC naive datetime を使用）。タイムゾーン混入に注意。
- レジリエンス:
  - LLM 関連の API 失敗はフォールバック（ゼロスコアやスキップ）で継続する設計。結果整合性のため部分失敗ケースが存在し得る。
- テスト:
  - OpenAI 呼び出し箇所は内部関数をパッチして差し替え可能にしてあり、ユニットテストは可能。ただし E2E テストでは外部サービスのモックが必要。
- まだ未実装/将来対応想定:
  - 一部ファクタ（PBR、配当利回りなど）は未実装。Strategy/Execution 周りの詳細はこのリリースでは省略（パッケージの公開プレースホルダあり）。

導入メモ（想定）
- 初期セットアップ:
  - 環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env/.env.local または OS 環境に設定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動 .env ロードを無効化可能（テスト時など）。
- データ準備:
  - DuckDB データベース（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のスキーマ）を用意する必要あり。

謝辞
- 本 CHANGELOG はソースコードの記述・コメント・docstring から機能・設計意図を推測して作成しています。実際のリリースノート作成時はリポジトリ管理者による確認・追記を推奨します。