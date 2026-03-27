Keep a Changelog に準拠した変更履歴

すべての注目すべき変更を記録します。慣例に従い SemVer を使用します。

## [0.1.0] - 2026-03-27

### 追加
- パッケージの初期リリース。モジュール群を以下の機能別に実装・公開。
  - kabusys.config
    - .env ファイル（.env / .env.local）と OS 環境変数を統合して設定値を読み込む自動ロード機能を実装。
    - プロジェクトルート（.git または pyproject.toml を基準）を起点に .env を探索するため、CWD に依存しない読み込みを実現。
    - .env のパースは export 句、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース/タブ直前の # をコメントと見なす）をサポート。
    - .env.local は .env を上書き（override）可能。既存の OS 環境変数は protected として上書きされない。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト容易化）。
    - Settings クラスに各種必須設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）と検証ロジックを提供。KABUSYS_ENV / LOG_LEVEL のバリデーション、デフォルト値の提供、パス文字列を Path に展開などを実施。

  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini + JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
    - バッチ（最大 20 銘柄）処理、1 銘柄あたりの記事数・文字数制限（上限）、レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証）を実装。
    - 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。API 失敗時は該当チャンクをスキップして他チャンクは継続するフェイルセーフ設計。
    - DuckDB に対して部分置換（該当コードのみ DELETE → INSERT）を行い、部分失敗時に既存スコアを保護する実装。
    - テスト容易性のため、内部の OpenAI 呼び出し関数を patch で差し替え可能に設計。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込む機能を実装。
    - ma200 の算出でルックアヘッドバイアスを防ぐため対象日未満のデータのみを使用する等、データ不足時のフォールバック（中立スコア）や API 失敗時のフォールバック（macro_sentiment = 0.0）を備える。
    - OpenAI 呼び出しは独立実装とし、API の失敗種別に応じたリトライ・ログ出力を行う。

  - kabusys.data
    - calendar_management
      - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）を実装。
      - DB 登録値優先、未登録日は曜日（週末）ベースのフォールバックを行う一貫したロジック。また最大探索日数制限で無限ループを防止。
      - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - pipeline / etl
      - ETLResult データクラスを公開し、ETL パイプラインの結果・品質チェック・エラー集約を行う基盤を提供。
      - 差分取得、backfill、jquants_client 経由での idempotent な保存、品質チェックモジュールとの連携を想定した設計。

  - kabusys.research
    - factor_research
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）の計算関数を実装（DuckDB の SQL を活用）。
      - データ不足時には None を返す等の堅牢な設計。
    - feature_exploration
      - 将来リターン計算（任意ホライズン）、IC（Spearman）の計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
      - pandas 等に依存せず標準ライブラリのみで実装。

  - 共通設計上の追加点
    - DuckDB をデータ格納・クエリ基盤として使用するコードを多数実装。
    - すべての分析 / スコアリング処理で datetime.today() / date.today() の直接参照を避け、ルックアヘッドバイアスを防止する方針を徹底。
    - ロギングを適切に追加し、警告・情報・例外時の挙動を明確化。
    - テスト容易性（環境変数の無効化フラグ、OpenAI 呼び出しの差し替えポイント、id_token 注入想定）を考慮した設計。

### 変更
- 初回リリースのため該当なし。

### 修正
- 初回リリースのため該当なし。

### セキュリティ
- 環境変数依存の機密情報（OpenAI API キー等）は Settings 経由で要求し、直接コードに埋め込まない設計。自動 .env ロードはテスト目的で無効化可能。

### 開発者向けメモ（重要な挙動／フック）
- 自動 .env 読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API のキーは各関数の api_key 引数で注入できます（テスト時はこちらを優先して使用すると容易）。引数未指定時は環境変数 OPENAI_API_KEY を参照します。
- OpenAI 呼び出しの内部関数（kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）は unittest.mock.patch で差し替え可能です。
- DuckDB の executemany は空リストを受け取れないバージョンの挙動に対応するため、空の場合は呼び出しをスキップするガードを実装しています。

（以上が v0.1.0 の主要な追加点・設計上の注意点です）