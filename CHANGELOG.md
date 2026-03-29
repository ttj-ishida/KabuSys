CHANGELOG
=========
すべての変更は「Keep a Changelog」方式に準拠して記載しています。  
このファイルはコードベースから推測して作成した初回リリース相当の変更履歴です。

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
------------------
Added
- パッケージ全体
  - 初期公開バージョン v0.1.0 を追加。
  - パッケージ名: kabusys。公開 API: data, research, ai, などを __all__ でエクスポート。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイル（プロジェクトルートの .env / .env.local）または OS 環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD に依存しない実装）。
  - .env ファイルのパース機能実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、行末コメント処理などに対応）。
  - Settings クラスを提供し、以下の必須/オプション設定をプロパティで取得可能:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH（data/kabusys.duckdb）、SQLITE_PATH（data/monitoring.db）、KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - 未設定の必須環境変数に対しては ValueError を送出する挙動を定義。

- AI モジュール (kabusys.ai)
  - news_nlp モジュールを実装
    - raw_news / news_symbols を元にニュース記事を銘柄ごとに集約し、OpenAI（モデル gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントスコアを取得。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に換算して前日 06:00 ～ 23:30）を対象（calc_news_window を提供）。
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄処理（_BATCH_SIZE = 20）。
    - 1 銘柄あたり最大 10 記事、最大 3000 文字にトリム。
    - API 呼び出しは 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" リスト、code と score の検査、未知コード無視、数値チェック）を行い、スコアを ±1.0 にクリップ。
    - 書き込みは部分的失敗に備え、取得済みコードのみ DELETE → INSERT で置換（DuckDB 互換性のため executemany を利用し空リスト対策あり）。
    - テスト用に内部の _call_openai_api をパッチ可能（unittest.mock.patch を想定）。
    - API キーは引数 api_key または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。

  - regime_detector モジュールを実装
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（'bull' / 'neutral' / 'bear'）を判定。
    - ma200 比率は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウからマクロキーワードでフィルタして最大 20 件取得。
    - LLM 呼び出し（gpt-4o-mini）結果は JSON として期待し、API 失敗やパース失敗は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアの合成とクリップ、ラベル付けのロジックを実装。
    - market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込む。DB 書き込み失敗時はロールバックし例外を上位へ伝播。

- データモジュール (kabusys.data)
  - calendar_management モジュール
    - market_calendar テーブルを用いた営業日判定・探索 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - market_calendar がない場合は土日ベースのフォールバック（DB がまばらな場合は DB 値優先、未登録日は曜日で補完）。
    - calendar_update_job を実装し、J-Quants API（jquants_client.fetch_market_calendar）から差分取得して保存する夜間バッチ処理を提供。バックフィルと健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプラインの補助関数（テーブル存在確認、最大日付取得、market calendar ヘルパーなど）を実装。
    - 設計上、差分更新・backfill・品質チェックの枠組みを想定（quality モジュールとの連携ポイントを確保）。

- 研究モジュール (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン）、200 日移動平均乖離、ATR（20 日）、20 日平均売買代金・出来高変化率、PER/ROE（raw_financials から）などを DuckDB 上で計算する関数を実装:
      - calc_momentum, calc_volatility, calc_value
    - 入力は DuckDB 接続と target_date のみ。結果は (date, code) をキーにした dict のリストで返却。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、factor_summary（統計サマリー）を実装。
    - calc_forward_returns は任意の horizon リストに対応（デフォルト [1,5,21]）、引数検証あり。
    - calc_ic はスピアマン（ランク相関）を自前で実装（外部ライブラリに依存しない）。

- DuckDB/互換性関連
  - DuckDB の executemany に関する制約（空リスト渡し不可）に対する対策を実装し、空時は実行をスキップするようにした箇所あり（ai/news_nlp, pipeline など）。

Changed
- （新規追加リリースのため変更履歴なし）

Fixed
- （新規追加リリースのため修正履歴なし）

Security
- OpenAI API キーや各種トークンは明示的に必須（ValueError を投げる）となるため、運用前に .env もしくは環境変数の設定が必要。
- 自動 .env 読み込みの挙動をオフにする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テストや CI での誤読込み回避に有用）。

Notes / 開発者向け情報
- テストの容易性: OpenAI API 呼び出しは各モジュール内の _call_openai_api 関数を patch することで模擬可能（例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")）。
- ルックアヘッドバイアス防止: AI / レジーム / ファクター計算の各モジュールは内部で datetime.today()/date.today() を直接参照せず、常に引数 target_date を基準に処理する設計になっています。
- OpenAI モデル: デフォルトで gpt-4o-mini を使用するように設定。
- ログ出力: 失敗やフォールバック時に WARNING/INFO/DEBUG ログを出すことで動作把握しやすくしている。
- 外部依存: duckdb, openai を使用。jquants_client, quality モジュールを参照する箇所があり、実運用ではそれら実装/設定が必要。

今後の予定（想定）
- AI モジュールの追加テストケース、モデル冗長化（フェイルオーバー）、より詳細な品質チェックルールの実装。
- ETL パイプラインのエンドツーエンド統合、ジョブスケジューラとの連携サンプル追加。
- 監視・モニタリング（Slack 通知等）の実装拡充。

もし CHANGELOG の各項目について、より詳細な説明（関数単位の変更点や使用例、移行手順など）が必要であればお知らせください。