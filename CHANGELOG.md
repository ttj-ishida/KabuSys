# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring をエクスポート。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を提供。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）。CWD に依存しない自動読み込み。
  - .env, .env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - export KEY=val 形式やクォート付き値、インラインコメントの取り扱いに対応したパーサを実装。
  - Settings クラスを提供し、各種必須設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を必須として扱う。
    - DB パスのデフォルト値（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。
    - 環境 (development / paper_trading / live) とログレベル（DEBUG/INFO/...）の検証。
    - is_live / is_paper / is_dev の簡易フラグ。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores に保存する処理を実装。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの最大記事数・文字数トリミング、レスポンス検証を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。致命的でない失敗はログ出力してスキップ（フェイルセーフ）。
    - 時間ウィンドウ計算ユーティリティ calc_news_window を提供（JST 前日 15:00 〜 当日 08:30 を UTC naive datetime に変換）。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で regime（bull/neutral/bear）を算出。
    - OpenAI を用いたマクロセンチメント評価（gpt-4o-mini）を実装。記事がない場合は LLM 呼び出しを行わない。
    - API エラー時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ動作。
    - DuckDB 上の market_regime テーブルへ冪等に書き込む（BEGIN/DELETE/INSERT/COMMIT）、例外時は ROLLBACK を試行。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定（is_trading_day / is_sq_day）、前後営業日検索（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）を実装。
    - DB にカレンダーがない場合の曜日ベースフォールバック（週末を休日扱い）をサポート。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアントから差分取得して保存、バックフィルや健全性チェックを実施。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを提供（フェッチ数・保存数・品質問題・エラーメッセージ等を格納）。
    - 差分取得、backfill、品質チェック（quality モジュール連携）など ETL の骨組みを実装。
    - jquants_client との連携ポイントを確保して idempotent に保存できる設計。
  - その他ユーティリティ（jquants_client 等への依存を前提）。

- リサーチ / ファクター群（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M）、ma200乖離、ATR などの計算関数（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials のみ参照、DB のみで計算。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）を実装。
    - IC（Spearman）計算 calc_ic、ランク化ユーティリティ rank、統計サマリー factor_summary を実装。
  - zscore_normalize を含むデータ統計ユーティリティを re-export。

### 修正
- （初版のため該当なし）

### 既知の動作・設計上の注意
- ルックアヘッドバイアス防止:
  - 各 AI/研究モジュールは datetime.today() / date.today() を直接参照しない（target_date を明示的に受け取る設計）。
  - DB クエリにおいても target_date 未満や排他条件を用いるなど、将来データの参照を避ける設計を採用。
- OpenAI 統合:
  - gpt-4o-mini を使った JSON mode を利用。API レスポンスのパース・検証を厳密に行い、不正レスポンスはスキップしてフェイルセーフ。
  - テスト用に API 呼び出し関数をモック可能。
- トランザクション管理:
  - DuckDB への書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理を採用。例外発生時は ROLLBACK を試行し、失敗ログを出力。
- 環境変数の取り扱い:
  - .env の読み込みは OS 環境変数を保護（protected set）し、override 挙動を選択可。
  - 必須環境変数未設定時は ValueError が発生する（Settings の必須プロパティ）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- DuckDB 互換性:
  - executemany に空リストを与えると問題がある点（DuckDB 0.10 系）を回避するため、空チェックを行ってから executemany を実行。

### 要求される外部サービス / 環境
- OpenAI API（OPENAI_API_KEY が必要。関数呼び出しで api_key を渡すことも可能）
- J-Quants API（JQUANTS_REFRESH_TOKEN、jquants_client を使用）
- kabuステーション API（KABU_API_PASSWORD 等）
- Slack 通知に SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を使用するための設定

---

今後のリリースでは、以下を予定しています（非包括的）:
- strategy / execution / monitoring モジュールの実装詳細（自動発注・監視ループ）。
- PBR・配当利回りなど value ファクターの追加。
- より細かな品質チェック、メトリクス収集・可視化機能の強化。