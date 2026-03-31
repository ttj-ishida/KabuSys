CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

[0.1.0] - 2026-03-31
-------------------

Added
- 基本パッケージ初期リリース。パッケージ名: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py
    - パッケージ公開とバージョン情報を追加。

- 環境設定・自動 .env ロード
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを導入。
    - export KEY=val 形式、クォートやエスケープ、インラインコメントの処理に対応した .env パーサーを実装。
    - OS 環境変数を保護する protected パラメータを導入し、.env.local での上書きを制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途を想定）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / Slack / DB パス / 実行環境 / ログレベル等の取得ロジックと検証を実装。
    - 環境値が未設定／不正な場合は明示的な ValueError を投げる。

- AI（ニュースNLP・レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算。
    - 一銘柄あたりの記事数・文字数上限、バッチサイズ上限、チャンク分割、最大リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション（JSON 抽出、results 配列、code と score の検証）、スコアの ±1.0 クリップ。
    - DuckDB への冪等的書き込み（対象コードのみ DELETE → INSERT）および部分失敗時の保護（他銘柄の既存データを消さない）を実装。
    - calc_news_window を提供（JST の前日 15:00 ～ 当日 08:30 に対応する UTC 時刻ウィンドウの計算）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - MA200 乖離計算（target_date 未満のデータのみを使用してルックアヘッドバイアスを回避）。
    - マクロニュース抽出用キーワード群と、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価を実装。API 失敗時は macro_sentiment=0.0 のフォールバック。
    - レジームスコア合成・ラベリング・market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI 呼び出しのエラー判定／リトライ（RateLimit/接続/タイムアウト/5xx）とログ出力を実装。
    - テスト容易性のため news_nlp 側と内部 API 呼び出し実装を分離。

- データ（ETL・カレンダー・クライアント公開）
  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプラインの基本実装（差分取得、idempotent 保存、品質チェックフックの呼び出し）。
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラー一覧などを保持）。to_dict により監査ログ用の辞書化が可能。
    - 最小データ日やバックフィル日数等のデフォルト設定を定義。

  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルの管理と JPX カレンダー夜間更新ジョブ（calendar_update_job）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを提供。
    - 市場カレンダー未取得時には曜日ベースのフォールバック（平日を営業日）を使用し、一貫性を保つ設計。
    - カレンダー取得のバックフィルや健全性チェック（過度な将来日付のスキップ）を実装。
    - jquants_client との連携ポイント（fetch_market_calendar / save_market_calendar）を想定。

  - src/kabusys/data/__init__.py, src/kabusys/data/etl.py
    - ETLResult の再エクスポートを提供。

- リサーチ・因子計算・特徴量探索
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER/ROE）等のファクター計算を実装。
    - DuckDB を用いた SQL + Python 実装。prices_daily / raw_financials テーブルのみ参照し、外部 API にはアクセスしない。
    - データ不足時の扱い（None の返却）やログ出力を実装。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns: 任意ホライズンに対応）、IC（Information Coefficient）計算（Spearman ランク相関）、rank ユーティリティ、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。数値の有限性チェック・入力検証を実施。

- 共通実装・注意点
  - DuckDB を前提とした実装で、日付処理はすべて date/datetime オブジェクトで統一。
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を解析内で直接参照しない実装方針を徹底（target_date を明示的に受け取る）。
  - OpenAI の呼び出しは JSON mode（response_format={"type":"json_object"}）を使用し、厳密な JSON 出力を期待する設計。
  - API 呼び出しに関してはリトライ・バックオフ・フェイルセーフ（失敗時はゼロやスキップするなど）を多くの箇所で取り入れ、ETL/スコアリング処理の堅牢性を高めている。
  - 各種操作（AI スコアの書込み、レジームスコアの書込み、カレンダーデータ保存等）は冪等性を意識している。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- 初版リリースのため該当なし。

Notes / 補足
- OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照する。キー未設定時は ValueError を送出する設計。
- デフォルトの DuckDB/SQLite ファイルパスは Settings クラスで設定可能（環境変数 DUCKDB_PATH / SQLITE_PATH）。
- 将来的な改良点（例: PBR・配当利回りの追加、より詳細な品質チェック出力、モデルの切替機能など）は別途計画する想定。

--------------------------------------------------------------------
今後のリリースでは「Changed」「Fixed」「Security」等のセクションに差分を追記してください。