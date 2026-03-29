# Changelog

すべての重要な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」準拠のフォーマットで記載しています。

フォーマットの変更履歴が必要な場合はこのファイルを更新してください。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。パッケージバージョン: 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定
  - kabusys.config モジュールを追加。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を探索）。
    - 行パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
    - OS 環境変数を保護する protected オプションを実装し、.env.local は既存環境変数を上書き可能（ただし保護キーは除外）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを公開。
    - env / log_level の入力検証（不正な値は ValueError を送出）。
    - duckdb/sqlite のデフォルトパス値を提供（data/kabusys.duckdb, data/monitoring.db）。

- AI 関連（OpenAI 統合）
  - kabusys.ai パッケージを追加。
  - news_nlp モジュール
    - raw_news と news_symbols を用い、指定ウィンドウ（前日15:00JST〜当日08:30JST）内のニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON mode で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄）、トークン肥大化対策（記事数最大・文字数トリム）を実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数的バックオフを持つリトライ機構と、レスポンスのバリデーション（JSON抽出、results 配列、code/score 検証、数値チェック、スコアクリップ）を実装。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。
    - calc_news_window(target_date) でニュース収集ウィンドウを算出（UTC naive datetime を返す）。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、news_nlp ベースのマクロセンチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出のキーワードリストを実装、OpenAI 呼び出しは独立実装でモジュール結合を低く保持。
    - API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ、リトライ・バックオフ・エラー分類（5xx とそれ以外）を実装。
    - score_regime(conn, target_date, api_key=None) を公開。戻り値は成功時 1。
  - 全 AI モジュールは OpenAI API キーの注入をサポート（api_key 引数または環境変数 OPENAI_API_KEY）。

- Data / ETL / カレンダー
  - kabusys.data パッケージを追加。
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）を扱うユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫したロジック。
    - 夜間バッチ calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント呼び出し（jquants_client.fetch_market_calendar / save_market_calendar）を行い、バックフィル・健全性チェックを含む。
    - 最大探索日数やバックフィル幅など安全措置を実装（_MAX_SEARCH_DAYS/_BACKFILL_DAYS/_SANITY_MAX_FUTURE_DAYS など）。
  - pipeline / ETL
    - kabusys.data.pipeline モジュールに ETLResult dataclass を実装（取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得ロジック、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - ETLResult.to_dict() は品質問題を (check_name, severity, message) 形式で出力。
    - kabusys.data.etl で ETLResult を再エクスポート。

- Research / ファクター
  - kabusys.research パッケージを追加。
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200日移動平均乖離、20日 ATR、平均売買代金、出来高比率、PER/ROE（raw_financials から）を計算する関数を実装。
    - calc_momentum, calc_volatility, calc_value を公開。DuckDB のみ参照する想定（本番取引 API へのアクセスなし）。
    - データ不足時の扱い（None 返却）やロギングを実装。
  - feature_exploration モジュール
    - 将来リターン計算 calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（Spearman ρ）計算 calc_ic（レコード結合、None/データ不足時の扱い）。
    - ランク変換関数 rank（同順位は平均ランク、丸めで ties を扱う）。
    - factor_summary で count/mean/std/min/max/median を算出（None 除外）。
    - 研究用途に必要な統計解析機能群を提供。

- DB/トランザクション設計
  - DuckDB を主体としたデータ操作（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等のスキーマを想定）。
  - 重要な書き込み処理は BEGIN / DELETE / INSERT / COMMIT を用いた冪等・置換方式を採用。例外時は ROLLBACK を試行してエラーを上位へ伝搬。
  - ai_scores の更新は対象コードのみ DELETE → INSERT することで部分失敗時に既存データを保護。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Notes / 重要な設計判断（運用上の注意）
- ルックアヘッドバイアス防止
  - AI/研究/ETL の各モジュールは datetime.today()/date.today() を直接参照しない設計。外部から target_date を与えることで将来情報の混入を防止。
  - DB クエリは target_date 未満／排他条件を守る箇所がある（例: _calc_ma200_ratio の date < target_date）。
- フェイルセーフ
  - OpenAI API 呼び出しの失敗は必ずしも例外で停止させず、0.0（中立）やスキップで継続する設計を採用。監査用にログを残す。
- テスト容易性
  - OpenAI 呼び出しを行う内部関数（_call_openai_api 等）をモジュール単位で差し替え可能にしているためユニットテストでのモックが容易。
  - 環境自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- 環境変数必須項目
  - AI機能・Slack通知等を使用する場合は関連環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）の設定が必要。Settings の必須プロパティは未設定時に ValueError を投げる。

### Known limitations / TODO
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value では PER / ROE のみ）。
- News/NLP の出力整形は LLM の安定性に依存するため、将来的に追加のガードやロールバックを強化予定。
- DuckDB の executemany の空リスト制約（バージョン依存）を考慮した実装を行っているが、実運用での互換性テストが必要。

---

※ ここに記載の内容は、現行コードベースの実装・コメント・ドキュメントから推測してまとめた変更履歴です。実際のリリースノートとして公開する場合は、実運用でのテスト結果や追加の設計意図を反映して調整してください。