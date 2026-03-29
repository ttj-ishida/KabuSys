Keep a Changelog
=================

全ての注目すべき変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

[0.1.0] - 2026-03-29
--------------------

Added
- 初期リリース: kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開API: kabusys.{data, strategy, execution, monitoring} を __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により、CWD に依存しない読み込みを実現。
  - .env パーサ実装: export 構文、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などをサポート。
  - 上書き制御（override）と OS 環境変数保護（protected keys）に対応。
  - 自動ロード無効化環境変数 (KABUSYS_DISABLE_AUTO_ENV_LOAD) に対応。
  - Settings クラスを提供（プロパティ経由で設定取得）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証ロジック。
    - duckdb / sqlite のデフォルトパス取得ユーティリティ。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄当たりの記事と文字数制限（上限トリム）を実装。
    - API の 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンス検証ロジック（JSON 抽出、results 配列検証、コード照合、スコア数値化・クリップ）を実装。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT）を実装。部分失敗でも既存データを保護。
    - フェイルセーフ設計: API 失敗時は該当チャンクをスキップして処理継続。datetime.today()/date.today() を参照しない設計でルックアヘッドバイアスを回避。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull / neutral / bear）。
    - ma200_ratio 算出（target_date 未満のデータのみ使用、データ不足時は中立として処理）。
    - raw_news からマクロキーワードでフィルタしてタイトルを抽出、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API 呼び出しのリトライ・エラー処理、JSON パース失敗時のフォールバック（macro_sentiment = 0.0）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバックの取り扱いを実装。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（内部 _call_openai_api を想定）。

- Research（kabusys.research）
  - factor_research: 定量ファクター群を実装
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を prices_daily から算出。データ不足時は None。
    - calc_volatility: 20 日 ATR（avg true range）、相対ATR（atr_pct）、20 日平均売買代金、出来高比率等を算出。NULL の伝播制御に注意した実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。最新の財務レコードを target_date 以前から取得。
  - feature_exploration: 分析ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する汎用クエリを実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）は None を返す。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ（丸め処理で ties の検出漏れを防止）。
    - factor_summary: カラム毎の count/mean/std/min/max/median を標準ライブラリのみで計算する集約関数。
  - 既存ユーティリティ zscore_normalize を kabusys.data.stats から再エクスポート。

- Data（kabusys.data）
  - calendar_management
    - JPX マーケットカレンダー管理機能を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS を再フェッチ）・保存処理を実装。健全性チェック（将来日付の異常検出）を追加。
    - DB 登録値優先かつ未登録日は曜日フォールバックで一貫した挙動を保証。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー等を収集・シリアライズ可能）。
    - 差分取得、バックフィル、idempotent 保存（jquants_client 経由）、品質チェックのフレームワークを用意。
    - DuckDB 互換性考慮（テーブル存在チェック、MAX(date) 取得、executemany の空配列回避など）。
  - etl モジュールは ETLResult を再エクスポート。

Notes / Design decisions
- ルックアヘッドバイアス対策: いずれのスコア生成処理も内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取る設計。
- OpenAI 呼び出し: gpt-4o-mini を想定した JSON Mode を使用し、レスポンスパース時の堅牢性（前後余計テキストの抽出等）を考慮。
- フェイルセーフ: API エラー・パース失敗時は例外を投げずに該当処理を安全にフォールバック（ゼロスコアやチャンクスキップ）する動作を優先。
- DuckDB 対応: SQL 実装で DuckDB の実装差分（配列バインドや executemany の仕様）を考慮した対策を実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

翻訳・補足
- ここに記載した変更点は、提供されたソースコード（src/kabusys 以下）から推測してまとめたものです。実際のリポジトリ履歴（コミット単位の差分）は含みません。必要であれば実装上の関数一覧や外部依存（DuckDB / OpenAI / J-Quants クライアント等）に基づく追加注記を追記できます。