CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従っています。
リリース日付は本リポジトリの初期バージョン（0.1.0）作成日を仮定して記載しています。

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-29
-------------------

Added
-----
- パッケージ初期リリース。パッケージ名: kabusys、バージョン 0.1.0。
  - src/kabusys/__init__.py で __version__ を公開し、トップレベルで ["data", "strategy", "execution", "monitoring"] を __all__ に設定。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - export 付き行やクォート／エスケープを考慮した .env パーサ実装。
    - OS 環境変数の保護（既存キーは上書きされない、.env.local の override サポート）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須環境変数取得ヘルパ _require と Settings クラスを提供。
    - Settings で参照する環境変数（例）:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/... の検証）

- AI（LLM）関連機能
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）でセンチメント分析し ai_scores テーブルへ書き込むワークフローを実装。
    - UTC ベースのニュース収集ウィンドウ計算（JST 前日15:00〜当日08:30 相当）を calc_news_window として提供。
    - バッチング（最大 20 銘柄）、トークン肥大化対策（記事/文字数の上限）、JSON Mode レスポンスのバリデーション、スコアの ±1.0 クリップ、エクスポネンシャルバックオフによるリトライを実装。
    - API キー未指定時は例外（ValueError）を投げる明示的挙動。
    - テストのために _call_openai_api を差し替え可能（unittest.mock.patch 想定）。

  - src/kabusys/ai/regime_detector.py
    - 上場ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - ma200_ratio の算出、マクロキーワードでのニュース抽出、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、スコア合成、閾値に基づくラベル化を実装。
    - API失敗やパース失敗時はフェイルセーフとして macro_sentiment=0.0 を使用し継続。
    - OpenAI 呼び出し部分は別モジュールと結合しない設計（テスト容易性・モジュール分離）。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum（1M/3M/6M、ma200乖離）、Volatility（20日ATR、相対ATR、20日平均売買代金、出来高比）、Value（PER、ROE）などの定量ファクターを DuckDB 上の prices_daily / raw_financials を用いて計算する関数群を実装。
    - データ不足時に None を返すなどの安全策を採用。
    - 全関数が DB 読取のみで外部 API や取引実行を行わない旨を明記。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン（forward returns）の計算（指定ホライズン: デフォルト [1,5,21]）、Spearman ランク相関（IC）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリで実装。入力の妥当性チェックと None 排除を行う。

  - src/kabusys/research/__init__.py で主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- Data（ETL / カレンダー / ユーティリティ）
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルをベースに営業日判定（is_trading_day）、次/前営業日の検索（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ判定（is_sq_day）を実装。
    - DB にデータがない場合は曜日ベースでフォールバック（週末は休業日）。
    - calendar_update_job: J-Quants API からカレンダー差分を取得して market_calendar を冪等で更新する夜間バッチ処理を提供。バックフィル・健全性チェックを実装。
    - 最大探索日数やバックフィル等の定数で無限ループ等を防止する設計。

  - src/kabusys/data/pipeline.py
    - ETL パイプラインの枠組みとヘルパ（差分取得、保存、品質チェック）を実装。DuckDB 上のテーブルの最終日付検出、fetch/save の差分ロジック、品質チェック結果収集を行う。
    - ETLResult dataclass を定義し、実行結果（取得件数、保存件数、品質問題、エラー等）を構造化して返却可能。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - DB 操作は DuckDB（duckdb.DuckDBPyConnection）を前提。多くの関数で BEGIN / DELETE / INSERT / COMMIT を組み合わせ、冪等性と部分失敗時の既存データ保護を考慮。

Changed
-------
- （初版のため該当なし）

Fixed
-----
- （初版のため該当なし）

Security
--------
- 環境変数の扱いで OS 環境を保護する仕組みを導入（.env の読み込みで既存 OS 環境変数を上書きしない等）。
- OpenAI / 外部 API キーは引数注入または環境変数（OPENAI_API_KEY）から明示的に解決。未設定時は ValueError を送出して安全に失敗。

Notes / Usage
-------------
- 実行にあたって想定される DuckDB のテーブル（例）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など
- news_nlp.score_news / regime_detector.score_regime 等の AI 関連関数は OpenAI API（gpt-4o-mini）を利用するため、OPENAI_API_KEY のセットが必要（関数引数で直接渡すことも可能）。
- .env 自動ロードはプロジェクトルートを探索して行うため、テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して動作を制御可能。
- 時刻・日付処理ではルックアヘッドバイアスを防ぐため datetime.today()/date.today() を直接参照しない設計が各所で採用されている（target_date を明示的に渡す仕様）。

Acknowledgements
----------------
- 初版リリース。今後の機能追加、バグ修正、ドキュメント強化で継続的に更新予定。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0