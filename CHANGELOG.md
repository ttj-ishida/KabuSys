# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトは現在セマンティックバージョニングを使用しています。

## [Unreleased]

（現在差分はありません。新機能や修正は次のリリースに含まれます）

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能一式を実装しました。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py
    - パッケージバージョン __version__ = "0.1.0"
    - 公開モジュール: data, strategy, execution, monitoring

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロードする仕組み
      - 読み込み順序: OS 環境変数 > .env.local > .env
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
    - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱い等に対応
    - _require() による必須環境変数チェック
    - Settings クラスにより型付きプロパティを提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH, SQLITE_PATH
      - KABUSYS_ENV（development / paper_trading / live の検証）
      - LOG_LEVEL の検証
      - is_live / is_paper / is_dev のユーティリティ

- AI ニュース解析モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用いた銘柄毎ニュース集約
    - ニュース収集ウィンドウ calc_news_window(target_date) 実装（JST 基準、UTC で比較）
    - OpenAI（gpt-4o-mini）を JSON Mode で呼び出してセンチメントを取得
    - バッチ処理（最大 _BATCH_SIZE = 20 銘柄/回）、1銘柄あたり記事数・文字数の上限を導入
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score の検証）、スコア ±1 にクリップ
    - DuckDB への冪等書込み（DELETE → INSERT、部分失敗時に既存スコアを保護）
    - テスト容易性のため _call_openai_api をパッチ可能に設計
    - 公開関数: score_news(conn, target_date, api_key=None)

  - src/kabusys/ai/__init__.py
    - score_news を公開

- 市場レジーム判定モジュール
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で市場レジームを判定
    - レジーム分類: "bull" / "neutral" / "bear"（閾値設定あり）
    - DuckDB から prices_daily / raw_news を参照し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - LLM 呼び出しは独立実装（tests で差し替え可能）
    - API エラー時はフェイルセーフ（macro_sentiment = 0.0）で継続
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ管理 / ETL
  - src/kabusys/data/pipeline.py
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラーの集計）
    - 差分更新、バックフィル、品質チェック等の方針を実装（関数群の基盤）
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティ等を提供

  - src/kabusys/data/etl.py
    - ETLResult を公開インターフェースとして再エクスポート

- マーケットカレンダー管理
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーを扱うユーティリティ群を実装
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar の有無に応じた DB 優先 / 曜日フォールバックの一貫した実装
    - calendar_update_job(conn, lookahead_days)：J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェック含む）
    - 最大探索日数やバックフィル日数等の安全策を導入

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム、ボラティリティ、バリュー（PER/ROE）の計算関数を実装
      - calc_momentum, calc_volatility, calc_value
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグや移動平均を算出
    - データ不足時の None 処理、結果は (date, code) をキーとする辞書リストで返却

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装
    - pandas 等に依存せず標準ライブラリで完結
    - rank() は同順位を平均ランクで処理（丸めによる ties 対策あり）

  - src/kabusys/research/__init__.py
    - 主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

- データユーティリティ
  - src/kabusys/data/calendar_management.py, pipeline.py 等が jquants_client と連携（fetch/save の呼び出しを想定）

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY から取得する設計。未設定時は明示的に ValueError を発生させることで誤った無条件呼び出しを防止。

---

注意:
- 多くのモジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を想定しています。テストや実行時には適切に接続を渡してください。
- LLM 呼び出し部分は外部 API（OpenAI）に依存します。テスト環境向けに _call_openai_api の差し替えを行えるよう設計されています。
- datetime.today()/date.today() の乱用を避け、ルックアヘッドバイアス防止の設計がなされています（target_date を明示的に渡す方式）。
- 詳細な使用方法・データスキーマ・運用手順は別途ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。