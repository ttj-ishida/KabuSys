# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

リンクや比較はこのバージョンでは未設定です。

## [Unreleased]

- （現在のコードベースでは未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初期リリース。プロジェクトのコア機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（kabusys）とバージョン設定（__version__ = "0.1.0"）。
  - パッケージ公開 API：data, strategy, execution, monitoring。

- 環境設定 (kabusys.config)
  - .env ファイル / 環境変数から設定を自動ロードする仕組みを実装。
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの実装（クォート、エスケープ、コメント、export 形式対応）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live 検証）、LOG_LEVEL 検証、is_live / is_paper / is_dev
  - 必須環境変数未設定時は ValueError を送出する _require 実装。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを生成。
    - バッチ処理（最大 20 銘柄/回）・トークン肥大化対策（記事数・文字数制限）・レスポンスバリデーション実装。
    - 再試行ロジック（429、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ）。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時に既存データを保護）。
    - calc_news_window(target_date) を公開（JST ベースのニュース収集ウィンドウを UTC naive datetime で返却）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、OpenAI（gpt-4o-mini）を呼び出して macro_sentiment を取得。
    - API 呼び出しの再試行/フォールバック（失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等に書き込むトランザクション処理（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - LLM 呼び出しは独立実装にしてモジュール結合を避ける設計。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar がない場合は曜日ベースのフォールバック（週末を休日扱い）。
    - calendar_update_job により J-Quants からの差分取得 → market_calendar への冪等保存を実装（バックフィルや健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得・保存件数、品質問題リスト、エラー概要を保持）。
    - 差分更新・バックフィル・品質チェックの設計に基づくユーティリティを実装（jquants_client 経由でデータ取得・保存を想定）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、trading-day 調整ロジック等。
  - データ API 再エクスポート（kabusys.data.etl: ETLResult）。

- リサーチ/ファクター (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
    - calc_value: PER（EPS が 0/欠損時は None）、ROE の計算（raw_financials と prices_daily を組合せ）。
    - DuckDB SQL を活用した効率的な実装（カレンダーバッファ、NULL の扱い、データ不足時は None）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズンに対する将来リターン（デフォルト [1,5,21]）をリード関数で一括取得。
    - calc_ic: スピアマン（ランク相関）による IC 計算（コードで結合、None/不足データは除外、最小 3 レコード要件）。
    - rank: 同順位は平均ランクで処理するランク付け。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
  - リサーチユーティリティを __init__ で再エクスポート。

- 設計上の共通方針
  - ルックアヘッドバイアス対策として datetime.today()/date.today() をアルゴリズム内部で参照しない（target_date を明示的に渡す方式）。
  - 外部ネットワーク/API 呼び出しはフォールバック（失敗時スキップ・安全値）を入れてフェイルセーフ化。
  - DuckDB の互換性考慮（executemany の空リスト回避や日付型処理など）。
  - ロギング（警告・情報・デバッグ）を各処理に実装。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 初期リリースのため該当なし。
- 注: OpenAI API キーや各種トークンは環境変数で管理する想定（Settings で必須チェック）。運用時は Secret 管理を推奨。

### 既知の制約 / 注意事項
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定。API の挙動変更やレスポンスフォーマット変更によりパースロジックの調整が必要になる可能性があります。
- DuckDB バインドやバージョンによっては一部挙動（リスト型バインド等）が異なるため、executemany の挙動等は互換性に注意が必要です。
- ai モジュールは外部 API（OpenAI）に依存するためテスト時は _call_openai_api をモックすることを想定しています（コメントでその旨を明記）。
- 一部の計算（200 日 MA 等）はデータ不足時に None や中立値（1.0）を返す設計です。運用上の扱いに注意してください。

---

今後の更新予定（例）
- strategy / execution / monitoring モジュールの実装（発注ロジック・監視・実運用連携）。
- jquants_client の具体的実装（API クライアント）と統合テスト。
- テストカバレッジ拡充、CI の導入、型チェックの強化。

（以上）