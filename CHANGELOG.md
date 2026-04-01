CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ定義（kabusys.__version__ = "0.1.0"）に基づきます。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-01
--------------------

Added
- 初回公開リリース。日本株自動売買・データ基盤・リサーチ用のコアモジュール群を提供。
  - パッケージ構成（主な公開領域）
    - kabusys.config: 環境変数 / 設定管理
    - kabusys.ai: ニュースNLP（score_news）および市場レジーム判定（score_regime）
    - kabusys.data: データ ETL / カレンダー管理 / pipeline ユーティリティ
    - kabusys.research: ファクター計算・特徴量探索ユーティリティ
    - kabusys.__init__ による公開: data, strategy, execution, monitoring（パッケージのエントリポイント）
- 環境設定（kabusys.config.Settings）
  - .env ファイル（.env, .env.local）と OS 環境変数の自動読み込みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - OS 環境変数は保護され、.env.local の override 時も保護対象は上書きされない。
    - 自動ロードを無効にするためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォートとバックスラッシュによるエスケープ
    - クォートなしでのインラインコメント（#）処理（直前がスペース/タブの場合にのみコメント扱い）
  - 必須設定取得用のヘルパー _require（未設定時は ValueError）
  - 主要設定プロパティ（デフォルトを含む）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH, CPU/MEMORY/DISK 閾値、KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
- AI（OpenAI）関連
  - kabusys.ai.news_nlp
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini の JSON モード）へバッチ送信してセンチメントを算出。
      - バッチサイズ、トークン肥大防止（記事数 / 文字数トリム）を実装（_BATCH_SIZE=20, _MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
      - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフを実装。APIエラーはフェイルセーフでスキップし続行。
      - レスポンスを厳格にバリデーションし、スコアを ±1.0 にクリップ。
      - 成功した銘柄のみ ai_scores テーブルへ冪等的（DELETE → INSERT）に保存。DuckDB の executemany 空リスト制約に対応。
    - calc_news_window(target_date): JST ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC naive datetime で返すユーティリティ。
    - テスト容易性: _call_openai_api など内部呼び出しはパッチ可能。
  - kabusys.ai.regime_detector
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
      - マクロキーワードで raw_news タイトルを抽出し、OpenAI により JSON で macro_sentiment（-1.0～1.0）を取得。
      - 合成スコアのクリップと閾値判定（_BULL_THRESHOLD=0.2, _BEAR_THRESHOLD=0.2）。
      - DB への書き込みはトランザクションで冪等（BEGIN / DELETE / INSERT / COMMIT）を保証。
      - API 呼び出しのリトライ・フェイルセーフ: API 失敗時は macro_sentiment=0.0 として継続。
- データ / ETL
  - kabusys.data.pipeline
    - ETLResult dataclass を公開（ETL 実行結果・品質問題・エラーの集約用）。
    - 差分更新・バックフィル・品質チェック方針を実装するためのユーティリティ群（jquants_client と quality モジュールを利用）。
    - DuckDB を用いた最大日付取得やテーブル存在チェックのユーティリティを提供。
- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間バッチ更新ジョブ calendar_update_job(conn, lookahead_days) を実装（J-Quants からの差分取得 → 保存）。
  - 営業日判定・検索ユーティリティを提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - 実装上の方針:
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを使用。
    - DB 登録値を優先、未登録日は曜日フォールバックで補完し、一貫した挙動を維持。
    - 最大探索範囲（_MAX_SEARCH_DAYS=60）で無限ループを防止。
    - 夜間バッチはバックフィル（直近 _BACKFILL_DAYS 日）を行い API 側の訂正を取り込む。
- リサーチ（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から取得）
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率
    - DuckDB 上で SQL / ウィンドウ関数を駆使して実装。外部 API へはアクセスしない。
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。horizons の妥当性検証あり。
    - calc_ic: スピアマンランク相関（ランク変換・同順位は平均ランク）で IC を算出。利用可能データが 3 件未満なら None。
    - factor_summary: count/mean/std/min/max/median を算出。None 値は除外。
    - rank: 値をランクに変換（小数丸めで ties を安定化）。
  - 依存軽量設計: pandas 等に依存せず標準ライブラリ + duckdb のみで実装。
- テスト/運用支援
  - OpenAI 呼び出しポイント（_call_openai_api 等）をパッチ可能にしてユニットテストが容易。
  - DB 書き込みは部分失敗時でも既存データを過度に削らない（対象コードを限定して DELETE → INSERT）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは api_key 引数で注入可能（テスト容易化）かつ環境変数 OPENAI_API_KEY からも取得。
- 機密情報の扱いについては .env と OS 環境変数の優先度と保護ルールを実装。

Notes / Known limitations
- OpenAI 連携:
  - API のレスポンスは JSON mode を期待するが、実際には前後に余計なテキストが混ざるケースを想定して一部復元処理を行う（最外の {} 抽出）。
  - 何らかの理由で API が完全に応答しない場合は「スコア 0.0」や該当銘柄スキップで安全側にフォールバックする設計です（例外を投げて全処理停止しない）。
- DuckDB 依存:
  - executemany に空リストを渡せないバージョンの互換性考慮が入っている（空チェックを行う）。
- 動作前提:
  - 正常利用には DuckDB 上のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が整備されている必要があります。
  - 一部の外部クライアント（jquants_client, quality）が別モジュールとして期待されており、実行時に適切に提供される必要があります。
- 注意事項:
  - 各 AI 呼び出しは API 利用料が発生するため、運用時はコスト管理に注意してください。
  - 設定（特に必須トークン類）が不足していると ValueError が発生します（設定方法は .env.example を参照する想定）。

--------------------------------------------
（本 CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリース履歴や日付はパッケージ運用者の記録に合わせて調整してください。）