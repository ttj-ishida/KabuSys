Keep a Changelog
=================

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。パッケージ名: `kabusys`（バージョン 0.1.0）。
- パッケージ公開 API:
  - pakage root: `kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]`
  - 設定オブジェクト: `kabusys.config.settings`
  - ETL インターフェース: `kabusys.data.ETLResult`（`kabusys.data.etl` で再エクスポート）
  - 研究用ユーティリティ群: `kabusys.research`（`calc_momentum`, `calc_value`, `calc_volatility`, `zscore_normalize`, `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`）
  - AI 関連:
    - `kabusys.ai.news_nlp.score_news`：ニュース記事を集約して OpenAI（gpt-4o-mini / JSON mode）でセンチメント評価し、`ai_scores` テーブルへ書き込む
    - `kabusys.ai.regime_detector.score_regime`：ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して `market_regime` テーブルへ書き込む
    - `kabusys.ai.news_nlp.calc_news_window`：ニュース収集ウィンドウ計算
- データプラットフォーム / ETL:
  - `kabusys.data.pipeline`：差分取得・保存・品質チェックのための ETLResult 等
  - `kabusys.data.calendar_management`：JPX カレンダー管理、営業日判定・前後営業日検索、夜間カレンダー更新ジョブ（`calendar_update_job`）
- 環境変数管理:
  - `kabusys.config`：.env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml）、`.env` / `.env.local` の優先順位、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能
  - .env パーサ: `export KEY=val`、クォート文字列（エスケープ処理）やインラインコメントの扱いに対応
  - 必須キー取得ヘルパー `_require` により不足時は `ValueError` を送出
  - Settings プロパティで主要設定を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL など）
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装（有効値セットをチェック）
- DuckDB ベースの DB 操作・テーブル想定:
  - 主に使用するテーブル: `prices_daily`, `raw_news`, `news_symbols`, `ai_scores`, `market_regime`, `raw_financials`, `market_calendar`
  - 各処理での書き込みは冪等・トランザクション（BEGIN / DELETE / INSERT / COMMIT）/ROLLBACK 処理を実装
- ロギング・堅牢性:
  - OpenAI 呼び出しはリトライ（指数バックオフ）を実装（RateLimit、接続エラー、タイムアウト、5xx を考慮）
  - API 失敗時のフェイルセーフ挙動:
    - ニュース NLP / レジーム判定の API 失敗時はスコアをデフォルト（0.0）にフォールバックして継続
    - ma200 比率のデータ不足時は中立（1.0）を使用
  - レスポンスの JSON パースは堅牢化（前後に余計なテキストが混ざる場合の {} 抽出処理）
  - LLM レスポンスのバリデーション（キー存在、型チェック、スコアの数値変換、既知コードフィルタ）を実装
- AI モデル／プロンプト:
  - 使用モデル: `gpt-4o-mini`
  - JSON mode を利用して厳密な JSON を期待（ただし余計な前後テキストに対応）
  - 各モジュールにシステムプロンプトを埋め込み（出力フォーマットの強制）
  - バッチ処理: `news_nlp` は最大 20 銘柄/チャンク、1銘柄あたり記事数・文字数上限を導入
- テストしやすさ:
  - OpenAI 呼び出し部分は内部関数 `_call_openai_api` を通しており、テストで patch しやすい設計

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時、既存の OS 環境変数はデフォルトで保護（`.env.local` は上書き可能だが OS 環境は保護）
- API キー（OpenAI）未設定時には呼び出し側へ `ValueError` を返し誤用を明確化

Notes / 実装上の重要ポイント
- ルックアヘッドバイアス対策:
  - すべての分析処理は内部で `datetime.today()` / `date.today()` を直接参照しない（外部から `target_date` を注入する形）
  - DBクエリでは target_date 未満 / 排他条件などを用いて未来データの混入を防ぐ
- DuckDB の互換性考慮:
  - `executemany` に空リストを渡せないバージョンへの対応（処理前に空チェック）
  - `ANY(?)` などのバインドが不安定な環境を避け、個別 DELETE を行う設計
- カレンダー周りのフォールバック:
  - `market_calendar` が存在しない場合は曜日ベースで判定（主に土日判定）
  - DB 登録とフォールバックの優先順序を明確化（DB 値優先、未登録は曜日ベース）
- ロギングレベルの検証: `LOG_LEVEL` の値は大文字化して検査（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）

要求される環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- SLACK_BOT_TOKEN（必須）
- SLACK_CHANNEL_ID（必須）
- OPENAI_API_KEY（AI 機能利用時に必須）
- KABUSYS_ENV（デフォルト: development、有効値: development / paper_trading / live）
- LOG_LEVEL（デフォルト: INFO）
- DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 設定で .env 自動読み込みを無効化）

既知の制約・今後の検討事項
- ai_score と sentiment_score は現フェーズでは同値として扱われる（将来的に差分化の余地あり）
- レジーム判定やニューススコアは LLM の品質に依存するため、モデルやプロンプトのチューニングが必要
- `kabusys.strategy` / `kabusys.execution` / `kabusys.monitoring` の実装詳細は本リリースでは外部公開 API のホルダとして存在（将来的な機能拡張予定）

---

開発者向け補足:
- OpenAI 呼び出し部分はユニットテストでモックしやすいように内部呼び出しを分離しています（unittest.mock.patch で `_call_openai_api` を差し替えてください）。
- DB スキーマ（テーブル名・カラム）はモジュール内 docstring に明記された前提で実装しています。テスト用の DuckDB に必要なスキーマを準備してから実行してください。