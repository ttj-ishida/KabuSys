CHANGELOG
=========

すべての変更は「Keep a Changelog」の形式に従って記載しています。  
このリポジトリの初版リリースはバージョン 0.1.0 です。

Unreleased
----------

（なし）


[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - exported サブモジュール: data, strategy, execution, monitoring（__all__ に設定）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 高度な .env パーサ:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなしの行でのインラインコメント処理（直前が空白/タブの場合のみ # をコメントと見なす）。
  - 必須変数取得ヘルパー (_require) と Settings クラス提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須項目をプロパティ経由で取得。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（data/kabusys.duckdb, data/monitoring.db）。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許可）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI（ニュース NLP / レジーム判定）（src/kabusys/ai/）
  - news_nlp モジュール:
    - raw_news と news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄別センチメントを付与して ai_scores テーブルへ書き込む。
    - 時間ウィンドウは JST 基準: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime）。
    - バッチサイズ・トリム制限（_BATCH_SIZE=20、1銘柄あたり最大記事数/文字数制限）によるトークン肥大化対策。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ実装。
    - レスポンス検証（JSON 抽出, results 配列, code/score の型検証、スコアを ±1.0 にクリップ）。
    - 部分的失敗に備え、ai_scores の更新は対象コードのみ DELETE → INSERT（冪等性・既存データ保護）。
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（70% 重み）と、マクロニュースの LLM センチメント（30% 重み）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
    - ma200 比率は target_date 未満のデータのみを用いる（ルックアヘッド防止）。
    - マクロニュースは raw_news からキーワード（例: 日銀, Fed, CPI 等）で抽出し、最大記事数制限の上で LLM に評価依頼。
    - OpenAI 呼び出しに対して再試行/バックオフを実装。API 失敗時は macro_sentiment=0.0 にフォールバックし継続（フェイルセーフ）。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT。失敗時は ROLLBACK を試行し例外を上位へ伝播。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management:
    - JPX 市場カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar 未取得時は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラス（target_date, fetched/saved カウント、quality_issues, errors 等）を提供して ETL 実行結果を構造化。
    - 差分更新、backfill、品質チェック（quality モジュール連携）等の設計に基づくユーティリティを実装。
    - DuckDB テーブル存在確認や最大日付取得などのヘルパーも実装。
    - ETL の保存処理は冪等（ON CONFLICT 相当の扱い）を想定。

- リサーチ（src/kabusys/research/）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER, ROE）、Volatility（20 日 ATR）等のファクター算出を実装。
    - DuckDB を用いた SQL 中心の実装で、prices_daily / raw_financials のみ参照。結果は (date, code) を含む dict のリストで返す。
    - データ不足時の None ハンドリング（例: ma200 に 200 行未満）。
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン取得、デフォルト [1,5,21]）を実装。ホライズン検証（1〜252 日）あり。
    - calc_ic（Spearman ランク相関による IC 計算）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず純 Python / DuckDB で実装。少数レコードや ties の扱いに注意。

Changed
- 初期リリース。設計方針・防御的実装の注記（例: ルックアヘッドバイアス防止、冪等書き込み、部分失敗時のデータ保護）を明示。

Fixed
- 初回リリースのため該当なし。

Notes / Migration
- OpenAI の利用:
  - OpenAI API キーは api_key 引数を優先し、省略時は環境変数 OPENAI_API_KEY を参照します（news_nlp, regime_detector）。未設定の場合は ValueError が発生します。
  - 使用モデルは gpt-4o-mini、JSON Mode（response_format={"type":"json_object"}）での呼び出しを行います。レスポンス検証に失敗した場合は該当銘柄/処理をスキップまたは 0.0 にフォールバックします。
  - テスト時はモジュール内の _call_openai_api をモックして API 呼び出しを制御できます。
- 環境変数の必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを Settings 経由で取得する関数があるため、運用時は .env を用意してください（.env.example を参照すること）。
  - 自動 .env ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB:
  - デフォルトの DuckDB/SQLite パスは Settings のプロパティで確認・上書きできます。
  - DuckDB のバージョン差異に配慮した実装（ex: executemany に空リストを渡さないガード等）を行っています。

開発者向け / テスト向けメモ
- ルックアヘッドバイアス回避:
  - 多くの処理（news_nlp.score_news, regime_detector.score_regime 等）は内部で datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計です。ユニットテストでの再現性が高い実装です。
- トランザクションとエラーハンドリング:
  - DB 書き込みは明示的な BEGIN/COMMIT/ROLLBACK を利用。ROLLBACK 失敗時は警告ログを出力して上位例外を伝播します。

Acknowledgements
- 初期実装のため、今後の利用・運用で発見された不具合や改善要望は Issue/PR を通じて反映してください。