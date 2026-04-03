# Keep a Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基本機能群を実装・公開します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュールの __all__ 定義）。
- 設定管理
  - kabusys.config: .env / .env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込みする仕組みを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env 行パーサは export 形式、クォートやエスケープ、インラインコメントの扱いに対応。
  - Settings クラスで各種設定をプロパティ形式で公開（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル /実行環境 等）。
    - 必須設定取得用の _require が未設定時に ValueError を送出。
    - デフォルト値を多数設定（例: KABU_API_BASE_URL、DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db など）。
    - 環境変数の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）。
- AI 関連
  - kabusys.ai.news_nlp: ニュース記事を OpenAI（gpt-4o-mini）の JSON Mode でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理 (_BATCH_SIZE=20)、1銘柄あたり記事トリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアのクリップ）。
    - テスト容易性のため _call_openai_api を差し替え可能。
  - kabusys.ai.regime_detector: ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・market_regime テーブルへ冪等書き込み。
    - マクロキーワードフィルタ、最大記事数制限、LLM 呼び出し（gpt-4o-mini）、リトライとフェイルセーフ（API失敗時 macro_sentiment=0.0）。
    - DB クエリはルックアヘッドバイアスを防ぐように target_date 未満の排他条件を採用。
- データ基盤
  - kabusys.data.calendar_management: JPX カレンダーの管理・夜間バッチ更新（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に登録があれば優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - 最大探索日数やバックフィル、健全性チェック等の安全機構を実装。
  - kabusys.data.pipeline / etl: ETLResult データクラスおよび ETL パイプラインのインターフェース（差分取得、保存、品質チェックの設計方針を実装）。
    - ETLResult に品質問題やエラー一覧を保持し、辞書変換 to_dict を提供。
  - kabusys.data.etl は pipeline.ETLResult を再エクスポート。
  - jquants_client（参照）を用いる想定のフックを実装（fetch/save を呼ぶ箇所）。
- リサーチ用ユーティリティ
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などを計算。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比などを計算。
    - calc_value: 最新の raw_financials から PER/ROE を計算。
    - 計算は DuckDB クエリ中心で、結果は日付・コードをキーにした dict のリストで返す。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic: スピアマン（ランク）相関による IC 計算。
    - rank / factor_summary: ランク変換、基本統計量集計。
  - 研究モジュールは外部ライブラリに依存せず、標準ライブラリと DuckDB のみで実装。
- その他
  - DuckDB を利用した各種クエリ実装（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等を前提）。
  - 各種ロギング（logger）とエラーハンドリングを実装。

### 変更 (Changed)
- 初版のため変更履歴はありません（新規実装）。

### 修正 (Fixed)
- 初版のため修正履歴はありません。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- なし（初回リリース）。ただし以下注意点あり:
  - OpenAI API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で提供する必要がある。未設定時は ValueError を送出。
  - .env ファイル読み込みは自動で行われるが、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

### 互換性と移行ノート (Notes / Migration)
- 必要な外部依存:
  - duckdb（DuckDB 接続使用）
  - openai（OpenAI Python SDK の OpenAI クライアントを使用）
- DuckDB 関連:
  - 一部実装は DuckDB 0.10 系の挙動（executemany の空リスト制約など）を想定しているため、使用する DuckDB バージョンに注意してください。
- OpenAI SDK 関連:
  - JSON Mode での応答と status_code の有無に依存する箇所があるため、OpenAI SDK の互換性を確認してください。API エラーの status_code が存在しないケースも考慮した実装になっています（getattr を使用）。
- DB スキーマ期待値:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブルが存在する前提です。実行前にスキーマを準備してください。
- フェイルセーフ:
  - LLM 呼び出し失敗時、多くの場合スコアは 0.0（中立）にフォールバックするため、運用での致命的停止を回避する設計です。
- テストとモック:
  - OpenAI 呼び出し部分（_call_openai_api）はテスト時に差し替え可能な作りになっています（unittest.mock.patch を想定）。

### 既知の制約 / 注意事項 (Known issues / Caveats)
- news_nlp / regime_detector ともに LLM を利用するため、API レートや課金に注意してください。
- 時刻・ウィンドウ計算は UTC naive な datetime を使用しており、DB 側の日時列は UTC 前提で動作します（calc_news_window の仕様に注意）。
- calendar_management は market_calendar 情報がない場合は曜日ベース（平日）でフォールバックするため、完全な祝日情報を反映するには J-Quants からのデータ取得が必要です。
- package の __all__ に "execution" / "monitoring" が含まれますが、今回のコードベースでは該当モジュールの実装ファイルは公開ファイル内に含まれていません（将来実装想定）。

--- 

リリースに関する質問や、各モジュールの動作確認用の手順が必要であればお知らせください。