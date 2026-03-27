Keep a Changelog 準拠 — 重要な変更のみ記載しています。  
この CHANGELOG はソースコードの内容（docstring / 実装）から推測して作成しています。

すべての変更はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27
初回リリース

### 追加
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / ロード (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ 起点）。
    - 優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env のパースは export プレフィックス、クォート・エスケープ、インラインコメントを考慮。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。
    - 主要設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（使用時）
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（デフォルトを提供）
    - 環境モード検証: KABUSYS_ENV（development / paper_trading / live）
    - ログレベル検証: LOG_LEVEL（DEBUG/INFO/...）

- データプラットフォーム（kabusys.data）
  - ETL パイプライン用データクラス ETLResult（pipeline モジュール公開）。
  - calendar_management:
    - JPX マーケットカレンダーの更新・保存ロジック（夜間バッチ向け calendar_update_job）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーデータがない場合の曜日ベースのフォールバック実装。
    - 安全装置: 最大探索日数 / バックフィル / 健全性チェックを実装。
  - pipeline / etl:
    - 差分取得、DB への idempotent な保存（ON CONFLICT 相当）、品質チェックの流れを実装する基盤（詳細は docstring）。
    - ETL 実行結果を表す ETLResult（品質問題やエラーの集約・辞書化メソッドを含む）。
    - テーブル存在チェックや最大日付取得ユーティリティを実装。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）に JSON モードで投げて銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換で DB クエリ）。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたりの記事上限・文字数制限を実装（トークン肥大化対策）。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密バリデーションとスコアのクリップ、部分成功時の DB 書き換えロジック（DELETE → INSERT）により部分失敗で既存データを保護。
    - テスト用フック: _call_openai_api を patch して差し替え可能。
    - DuckDB executemany の空リスト制約に対応したガード実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を日次判定。
    - ウェイト: MA 70% / マクロ 30%、MA は最新終値 / MA200、最終スコアはクリップして閾値でラベル化。
    - マクロニュースはキーワードリストでフィルタしてタイトルを LLM に渡す（最大件数制限）。
    - API 呼び出しのリトライ / フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DB へは冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - news_nlp と実装を分離し、モジュール結合を避ける設計。
  - 共通設計方針:
    - どちらのモジュールも内部で datetime.today() / date.today() を直接参照せず、外部から target_date を与えることでルックアヘッドバイアスを防止。
    - OpenAI SDK（OpenAI クライアント）を使用し、JSON Mode のレスポンスをパースして利用。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時の None 処理）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER / ROE（raw_financials から target_date 以前の最新財務データを使用）。
    - DuckDB ベースの SQL 実装で、prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（スピアマン）計算、ファクター統計サマリー、ランク関数（同着は平均ランク）を実装。
    - pandas 等の外部依存を持たず標準ライブラリ + DuckDB SQL を用いる。

- その他ユーティリティ
  - データ/ETL/カレンダー操作に関する各種内部ユーティリティ（テーブル存在チェック、日付変換、安全ガード等）を実装。
  - ロギングを多用し、処理状況やフェイルセーフ事象を情報/警告/例外ログで記録。

### 既知の設計上の注意点（実装からの明記）
- OpenAI API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出する箇所がある。
- DuckDB の executemany は空リストバインドが不安定なため、空チェックを挟んでから実行。
- API 呼び出し失敗時は例外を止めずにフェイルセーフ（スコア 0.0 またはスキップ）で継続する設計箇所が多い（運用上の可用性を重視）。
- カレンダー・ETL の更新処理は idempotent に設計されている（部分失敗時の既存データ保護を考慮）。

### 既知の制約 / 将来作業候補
- Value ファクター群では PBR・配当利回りは未実装（docstring に明記）。
- news_nlp / regime_detector は gpt-4o-mini を前提にしているため、モデル変更時はプロンプト・レスポンス処理の調整が必要。
- calendar_update_job は jquants_client の fetch/save 実装に依存するため、API 仕様変更や認証フローの違いで影響を受ける可能性あり。

---

メンテナー注: この CHANGELOG はソースコード中の docstring / 実装から推測して作成しています。実際のリリースノートにする際は、コミット履歴・Issue トラッキング等と照合してください。