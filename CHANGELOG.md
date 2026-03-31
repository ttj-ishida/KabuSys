# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。形式は「Keep a Changelog」に準拠します。

なお、本CHANGELOGはリポジトリ内の実装から推測して作成した初回リリース向けの要約です。

## [Unreleased]
- 次回以降の変更点をここに記載します。

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買システムのコアモジュール群を実装・公開。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの基本設定を追加。__version__ = "0.1.0"。公開モジュール: data, strategy, execution, monitoring。

- 環境設定/読み込み (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント、export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等に対応）。
  - Settings クラスを追加し、以下の設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL
    - ヘルパーメソッド: is_live / is_paper / is_dev
  - 未設定の必須環境変数は ValueError を投げる仕組みを実装。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news / news_symbols を集約して銘柄ごとに OpenAI (gpt-4o-mini, JSON Mode) でセンチメントスコアを算出し、ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ計算 (JST 前日15:00 ～ 当日08:30 相当の UTC 範囲) を提供（calc_news_window）。
  - バッチ処理 (_BATCH_SIZE=20)、記事数/文字数制限、レスポンス検証、スコアの ±1 クリップ、部分成功時の安全な DB 書き換えロジックを実装。
  - エラー耐性: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップして継続。API 呼び出し部分はテスト用に差し替え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、market_regime テーブルへ日次で冪等書き込みする機能を実装（score_regime）。
  - マクロニュースの抽出、OpenAI 呼び出し、リトライ/フォールバック（失敗時 macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計（target_date を明示的に渡す）。

- データ管理 (kabusys.data.pipeline, kabusys.data.etl, kabusys.data.calendar_management)
  - ETLResult データクラス（ETL 実行結果と品質情報を集約）を実装。
  - ETL パイプラインの骨組み（差分取得、バックフィル、品質チェック方針）を用意。J-Quants クライアント経由での取得保存を想定。
  - JPX カレンダー管理モジュールを実装（market_calendar の読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新ジョブ calendar_update_job）。
  - カレンダー未取得時の曜日ベースフォールバック、最大探索日数による安全措置を実装。

- リサーチ / ファクター (kabusys.research)
  - ファクター計算 (calc_momentum, calc_value, calc_volatility) を実装。prices_daily / raw_financials を参照して各種指標（1/3/6 ヶ月リターン、MA200乖離、ATR20、出来高/売買代金指標、PER/ROE 等）を計算。
  - 特徴量探索ユーティリティ (calc_forward_returns, calc_ic, factor_summary, rank) を実装。外部ライブラリに依存せず標準ライブラリ + DuckDB SQL による実装。
  - Z スコア正規化ユーティリティを kabusys.data.stats から再利用するインターフェースを提供（__all__ 経由）。

- 実装上の利便性・テスト対応
  - OpenAI への呼び出し部分はモジュール毎に独立して実装し、ユニットテストで差し替え可能（patch 可能な _call_openai_api）。
  - DuckDB に対する executemany の空リスト問題（バージョン依存）を考慮した安全な DB 更新ロジックを実装。

### 変更 (Changed)
- 初回リリースのため該当なし（新規実装）。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意 (Notes / Design decisions)
- ルックアヘッドバイアス対策: すべての日次処理は内部で現在時刻を参照せず、明示的な target_date を受け取る設計になっています。
- DB 書き込みは可能な限り冪等操作（DELETE → INSERT や ON CONFLICT）を行い、部分失敗時に既存データを不必要に消さないようにしています。
- OpenAI 呼び出しは JSON Mode を想定しており、返却 JSON のパースに冗長テキスト混入を考慮した復元ロジックを入れてあります。
- エラー処理は「フェイルセーフ（失敗しても処理継続）」を基本方針としています。重大な DB 書込エラー等は上位に伝搬します。

### 既知の制約 / 互換性
- 必要な DB テーブル（例）:
  - prices_daily, raw_news, news_symbols, ai_scores, raw_financials, market_calendar, market_regime
  - スキーマは実装内 SQL クエリから期待されるカラムを満たす必要があります。
- 外部依存:
  - duckdb, openai（OpenAI Python SDK）等が必要。
  - OpenAI モデルとして gpt-4o-mini を利用する想定。
- 環境変数:
  - リリース時に少なくとも以下の変数が設定されていることを期待:
    - OPENAI_API_KEY（score_news / score_regime のデフォルト解決先）
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

### 移行/利用時のヒント
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にすることで環境依存を避けられます。
- OpenAI 呼び出しをモックするには各モジュールの _call_openai_api を unittest.mock.patch してください（例: "kabusys.ai.news_nlp._call_openai_api"）。
- DuckDB で executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で空チェックを行っています。自前で DB 操作を行う場合は注意してください。

### セキュリティ (Security)
- API キーやパスワードは環境変数で管理する想定です。誤ってコミットしないようご注意ください。

### 貢献者
- 初期実装: 本リポジトリのコードベース（作者情報はリポジトリのコミット履歴を参照してください）

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はテスト結果・コミットメッセージ・マージ履歴に基づき適宜更新してください。）