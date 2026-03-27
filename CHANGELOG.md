# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

全般:
- このリポジトリは日本株自動売買システム「KabuSys」の初期公開です。
- 主に DuckDB をデータストアとして使用し、J-Quants / OpenAI（gpt-4o-mini）等との連携機能を含みます。
- 日付: 2026-03-27

## [0.1.0] - 2026-03-27

### Added
- パッケージと公開 API
  - パッケージ名 `kabusys` の初期リリース。
  - バージョン番号は `kabusys.__version__ = "0.1.0"`。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと OS 環境変数の統合読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途）。
    - プロジェクトルートの検出は __file__ から上位ディレクトリを走査し、.git または pyproject.toml を基準とする（CWD 非依存）。
  - .env のパーサ実装（クォート・エスケープ・コメント処理対応、`export KEY=val` 形式サポート）。
  - 環境変数の必須チェック `_require` と設定ラッパ `Settings` を導入。
    - J-Quants / kabuステーション / Slack / データベース / システム設定（env, log_level）向けプロパティを提供。
    - `duckdb_path` / `sqlite_path` のデフォルトパスを定義。
    - `KABUSYS_ENV` の有効値検証（development / paper_trading / live）。
    - `LOG_LEVEL` 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - `settings = Settings()` によりモジュールレベルで簡単に利用可能。

- AI（自然言語処理）モジュール（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へバッチ送信する機能を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC で扱う（calc_news_window を提供）。
    - バッチサイズ・トリム: 1銘柄あたり最大記事数・文字数制限（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を使用した応答パースと厳格な検証ロジック（results 配列、code/score のバリデーション）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数的バックオフによるリトライ実装。
    - スコアは ±1.0 にクリップし、取得成功銘柄のみ ai_scores テーブルを冪等的に置換（DELETE → INSERT）。
    - API キーは引数 `api_key` または環境変数 `OPENAI_API_KEY` で指定。未設定時は ValueError を送出。
    - ロギングによる経過報告とフェイルセーフ設計（API失敗時はそのチャンクをスキップして継続）。
  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull / neutral / bear）。
    - ma200_ratio の計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュースは news_nlp.calc_news_window を用いて抽出、LLM 呼び出しは独立実装でモジュール結合を避ける。
    - LLM 呼び出し失敗時は macro_sentiment = 0.0 にフォールバック（警告ログ）。
    - 計算結果を市場レジームテーブル（market_regime）へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK 後に例外を伝播。

- データ処理（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して market_calendar を冪等保存。
    - 営業日判定ユーティリティを提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（土日を非営業日とする）。
    - 安全性: 最大探索日数やバックフィル、健全性チェックを導入（日付整合性ガード）。
  - ETL パイプライン（pipeline + etl）
    - ETLResult データクラス（pipeline.ETLResult）を公開（etl モジュールから再エクスポート）。
    - 差分取得・保存・品質チェックの設計方針に基づく基盤を実装（jquants_client と quality モジュールとの連携を前提）。
    - パイプライン内部ユーティリティ（テーブル存在チェック・最大日付取得・トレーディング日調整等）を提供。
    - 初期データロード用に J-Quants が提供する最小データ開始日（_MIN_DATA_DATE）やバックフィル・カレンダー先読みの定数を定義。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Value（PER、ROE）、Volatility（20 日 ATR）および流動性指標を DuckDB の SQL と Python で計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 各関数は prices_daily / raw_financials のみ参照し、取引・発注 API へはアクセスしない設計。
    - 不足データや条件未満の場合は None を返す（安全設計）。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)
      - デフォルト horizons は [1,5,21]。入力検証（1..252）あり。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンの順位相関をランク変換 (rank) を用いて計算。有効レコードが 3 件未満の場合は None を返却。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を算出）
    - rank(values) ユーティリティ（同順位は平均ランク、丸めで ties を扱う）を提供。
    - これらは DuckDB と標準ライブラリのみで実装され、外部依存を避ける。

- その他の細かいユーティリティ
  - DuckDB の date 値変換ユーティリティやテーブル存在チェックなど、複数モジュールでの共通処理を整備。
  - 各種ログ出力（info/warning/debug）を配置して運用時の追跡を容易化。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易化）かつ環境変数でも参照。キーの扱いに注意してください（ログにキーを出力しない等の運用上の留意点）。

---

注記:
- 本リリースはコードベースから推測して作成した CHANGELOG です。実際の外部 API クライアント（jquants_client など）の実装や DB スキーマ、マイグレーション等はリポジトリの他ファイルに依存します。運用前にテストと設定確認を行ってください。