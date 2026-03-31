# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

- リリース方針: 主要な機能追加や重要な振る舞い、バグ修正、互換性に影響する変更を明記します。
- 日付はリリース日を示します。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加（Added）
- 基本パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring（__all__ 経由で公開）

- 環境設定/読み込み機能（kabusys.config）
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定: __file__ を起点に .git または pyproject.toml を探索してルートを検出。
  - .env パーサ: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でスキップ可能。
  - OS 環境変数の保護: .env ロード時に既存の環境変数を保護する仕組みを導入（.env.local は上書き可能だが OS のキーは保護）。
  - Settings クラスを提供し、必要な設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development, paper_trading, live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価を行い ai_scores テーブルへ書き込み。
  - 時間ウィンドウ: JST 前日15:00〜当日08:30（UTC では前日06:00〜23:30）をサポート。calc_news_window 関数を提供。
  - バッチ処理: 最大 20 銘柄/コール、各銘柄は最新10記事・最大3000文字でトリム。
  - 再試行/フォールバック: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。API 失敗時は該当チャンクをスキップして継続。
  - レスポンス検証: JSON パース、results フィールド、コード整合性、数値検証。スコアは ±1.0 にクリップ。
  - DB 書き込みは冪等性確保（対象コードのみ DELETE → INSERT）および DuckDB の executemany 空リスト制約に配慮。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）200日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を算出。
  - マクロニュース抽出はキーワードリストに基づき raw_news からタイトルを取得。
  - OpenAI（gpt-4o-mini）呼び出しで macro_sentiment を取得。API失敗時は 0.0 にフォールバック。
  - MA 計算・ニュースウィンドウ取得・スコア合成の各ステップを提供（score_regime 関数）。
  - DB 書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に処理。失敗時は ROLLBACK を試行。

- データ処理・ETL（kabusys.data.pipeline / etl / jquants クライアント連携）
  - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
  - 差分取得、backfill、品質チェック（quality モジュールとの連携）を想定した設計。ETLResult には品質問題とエラーの集約を保持。
  - DuckDB のテーブル存在チェックや最大日付取得などユーティリティを実装。

- マーケットカレンダー（kabusys.data.calendar_management）
  - market_calendar テーブルを元に営業日判定・前後営業日の検索・期間内営業日取得・SQ判定などのAPIを提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - DB データがない/欠損時は曜日ベースのフォールバック（土日を非営業日と扱う）。
  - calendar_update_job は J-Quants API から差分取得して保存（バックフィル、健全性チェック、保存数を返す）。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials に基づく）。
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank（外部依存を用いず純粋に DuckDB と標準ライブラリで実装）。
  - zscore_normalize を data.stats から再公開。

### 変更（Changed）
（初回リリースのため該当なし）

### 修正（Fixed）
（初回リリースのため該当なし）

### 既知の振る舞い / 注意点（Notes）
- OpenAI API の利用:
  - モデルは gpt-4o-mini を使用（JSON mode を想定）。
  - API キーは関数引数で注入可能。省略時は環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を送出。
  - レスポンスの堅牢化（JSON 前後余計テキストの復元など）を行っているが、LLM の出力形式変化には注意。

- ルックアヘッドバイアス防止:
  - datetime.today() / date.today() をデフォルト内部処理で参照しない方針を採用。target_date を明示的に与えるAPI仕様。

- DuckDB 互換性:
  - executemany に対する空リストバグ対応（呼び出し前に空チェック）。
  - 日付型取り扱いで date オブジェクトに正規化するユーティリティを利用。

- エラーハンドリング:
  - LLM/API 関連の致命的失敗は基本的にローカルフォールバック（例: macro_sentiment=0.0）やチャンクスキップして継続する設計。必要に応じて呼び出し元で厳密なエラーハンドリングを行ってください。

### 互換性（Compatibility）
- 初回リリースのため後方互換破壊の履歴はありません。公開 API（関数名/引数/戻り値）を将来変更する可能性があるため、利用時はバージョン管理に注意してください。

---

今後のリリースでは、テストカバレッジ、より詳細な品質チェックモジュール、追加のエクスポート/インポートツール、実運用向けの監視・アラート機能（monitoring モジュールの拡充）などを予定しています。