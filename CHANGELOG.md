# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
安定版のリリース履歴は下記の通りです。

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買・データ基盤・リサーチ向けのユーティリティ群を提供します。
主な追加点・設計方針は以下の通りです。

### Added
- 基本パッケージ
  - パッケージバージョンを 0.1.0 に設定（kabusys.__version__）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ にてエクスポート。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト等のため）。
    - プロジェクトルートの探索は __file__ を起点に `.git` または `pyproject.toml` を探索して行う（CWD 非依存）。
  - .env パーサ:
    - 空行・コメント行（#）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートを考慮したバックスラッシュエスケープ処理。
    - クォートなし値の行内コメント判定（直前が空白/タブの場合のみ # をコメントとみなす）。
    - ファイル読み込み失敗時は警告を出力して継続。
    - override/protected 機能により OS 環境変数を上書きしない安全なロードが可能。
  - Settings クラスで各種設定値をプロパティとして提供:
    - J-Quants / kabu API / LINE / データベースパス（DuckDB, SQLite）/監視設定（PID ファイル等）/システム設定（KABUSYS_ENV, LOG_LEVEL）
    - 必須値未設定時は ValueError を送出する `_require` を利用。
    - KABUSYS_ENV のバリデーション（development / paper_trading / live）や LOG_LEVEL の検証を実装。
    - is_live / is_paper / is_dev ユーティリティを提供。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄毎のニュースを統合し、OpenAI（gpt-4o-mini）によるセンチメントを算出して ai_scores テーブルへ書き込む機能を提供（score_news）。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリに使用）。calc_news_window を提供。
    - バッチ処理: 最大 20 銘柄/リクエスト、銘柄ごとに最大記事数・最大文字数でトリム。
    - レスポンスは JSON Mode を期待し、厳格なバリデーションを実施（results リスト・code/score の存在・数値性・既知コードのみ採用）。
    - API の一時エラー（429/接続断/タイムアウト/5xx）は指数バックオフでリトライ。致命的でない場合はスキップして継続（フェイルセーフ）。
    - DuckDB の executemany の互換性を考慮し、DELETE と INSERT を個別に executemany で実行（空リスト対策あり）。
    - スコアは ±1.0 にクリップして保存。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能に実装（_call_openai_api のモジュール内差し替え）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei225 連動型）の 200 日 MA 乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して、日次で market_regime テーブルに書き込む（score_regime）。
    - MA 計算は target_date 未満のデータのみを参照してルックアヘッドバイアスを回避。
    - マクロ記事抽出にはキーワードベースのフィルタリングを実施（マクロキーワード定義あり）。
    - OpenAI（gpt-4o-mini）に JSON モードで問い合わせ、エラー時は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
    - リトライ・バックオフロジック、HTTP 5xx とそれ以外での挙動差別化を実装。
    - レジームスコア合成、ラベル付け（bull / neutral / bear）および market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行。

- データ基盤モジュール（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理用のユーティリティを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day などの実装。
    - market_calendar が未取得のときは曜日ベースのフォールバック（週末を非営業日とする）。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫して扱う設計。
    - 最大探索日数制限を設け無限ループを防止。
    - 夜間バッチ calendar_update_job を実装。J-Quants クライアントから差分を取得して保存し、バックフィル・健全性チェックを実施。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入。ETL 実行結果の構造化（フェッチ数・保存数・品質問題・エラー等）。
    - to_dict により品質問題を辞書化して監査ログに使える形式でエクスポート。
    - ETL の設計方針として差分更新・バックフィル・品質チェックの収集（Fail-Fast を避ける）を採用。
    - kabusys.data.etl で ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す設計。
    - calc_volatility: 20 日 ATR・相対 ATR・20 日平均売買代金・出来高比率等を計算。部分窓でも avg_turnover を算出。
    - calc_value: raw_financials の直近報告を取得し PER/ROE を計算。EPS 欠落や 0 の場合は PER を None とする。
    - 設計上、DuckDB に対する SQL と Python の組合せで計算し、本番口座や発注 API にはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を実装。有効レコードが 3 件未満のときは None を返す。
    - rank: 同値（ties）は平均ランクにし、丸めで ties 検出漏れを防ぐ実装。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - data.stats の zscore_normalize を再エクスポート（kabusys.research パッケージ経由で利用可能）。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Deprecated
- （初版につき該当なし）

### Security
- OpenAI API キーは関数引数から注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を投げて誤使用を防止。
- .env ファイル読み込みで OS 環境変数を保護する仕組み（protected set）を実装。

### 注意事項 / 設計上の重要点
- ルックアヘッドバイアス防止:
  - AI スコアリング／レジーム判定／ファクター計算等の各モジュールは内部で datetime.today() や date.today() を直接参照せず、すべて caller が指定する target_date を基準に処理します。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants 等）呼び出し失敗時は、可能な限り処理を継続する設計（0.0でフォールバック／部分スキップ）。ただし致命的な DB 書込失敗等は上位へ伝播。
- トランザクション安全:
  - 重要な DB 更新（market_regime / ai_scores / market_calendar 等）は BEGIN / DELETE / INSERT / COMMIT パターンや executemany を用いた冪等保存を採用。エラー時は ROLLBACK を試行。
- DuckDB 互換性:
  - executemany に対する空リストの問題（DuckDB 0.10 系）を考慮した条件分岐を実装。

もし CHANGELOG に追加してほしい注釈（例えば内部実装のさらに詳細な変更履歴や将来のマイグレーション注意点など）があれば指示してください。