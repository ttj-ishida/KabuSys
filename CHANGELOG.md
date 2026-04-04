CHANGELOG
=========

すべての変更は https://keepachangelog.com/ja/ のガイドラインに準拠しています。
このプロジェクトはセマンティックバージョニングを採用します。

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース。
- コア
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - パッケージの公開APIを __all__ で定義（data, strategy, execution, monitoring）。
- 設定 / 環境変数読み込み (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 自動ロードの無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パーサーを実装（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - .env 読み込み時の上書きルール: OS 環境変数 > .env.local > .env。既存の OS 環境変数は保護される（protected キーセット）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能に。
    - J-Quants / kabu API / LINE / データベース（DuckDB, SQLite） / 監視用 PID/kill flag / リソース閾値 / 環境（development/paper_trading/live）/ログレベル等を取得。
    - 必須変数未設定時は ValueError を送出する _require() を採用。
    - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。
- AI（kabusys.ai）
  - ニュースセンチメント（news_nlp）
    - calc_news_window 関数を実装（JST ウィンドウ → UTC naive datetime を返す）。
    - score_news(conn, target_date, api_key=None) を実装。raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - バッチサイズ、1銘柄あたりの最大記事数・最大文字数制限を実装（トークン肥大化対策）。
    - JSON Mode を使ったレスポンス処理と堅牢なバリデーション（JSON 抽出、results 配列・型検証、未知コード無視、数値検証）。
    - レスポンススコアは ±1.0 にクリップ。
    - API 呼び出しでのリトライ（429, ネットワーク断, タイムアウト, 5xx）と指数バックオフを実装。最大試行回数制御。
    - DuckDB の executemany に対する互換性考慮（空リストは実行しない等）、書き込みは DELETE→INSERT の冪等ロジックで他コードを保護。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能に（_call_openai_api を patch 可能）。
  - 市場レジーム判定（regime_detector）
    - score_regime(conn, target_date, api_key=None) を実装。ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - 1321 の ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、データ不足時のフォールバック（1.0）を実装。
    - マクロニュース抽出、OpenAI によるマクロセンチメント評価（JSON 出力のパース）、API エラーなら macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - API 呼び出しのリトライとエラー種別ごとのハンドリング（RateLimit, connection, timeout, APIError の status_code 判定）。
- データ（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar）を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB 登録値を優先し、未登録日は曜日ベースのフォールバックを使用する一貫した挙動。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分フェッチ→保存（バックフィル・健全性チェックを含む）を行う夜間バッチ処理を提供。
    - テーブル存在チェック、NULL 値・未登録日の取り扱い、最大探索日数による安全策を実装。
  - pipeline / etl
    - ETLResult dataclass を実装し、ETLの取得数・保存数・品質問題・エラー等を集約。
    - ETL パイプライン設計に基づく補助関数（テーブル存在チェック、最大日付取得等）を用意。
    - data/etl.py で ETLResult を再エクスポート。
- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を使用して各種ファクター（モメンタム、MA200乖離、ATR、流動性、PER/ROE 等）を計算し、(date, code) ベースの結果を返す。
    - データ不足時の扱い（None）、ウィンドウバッファ等を明示。
  - feature_exploration
    - calc_forward_returns を実装（複数ホライズン対応、ホライズン検証あり）。
    - calc_ic（Spearman ランク相関）と rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない純粋 Python 実装。
- 一般
  - DuckDB を利用する関数群が多数追加（各モジュールで SQL を直接発行）。
  - 日付/時間は date / naive datetime を用いて timezone 混入を避ける設計（ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない関数が多い）。

Changed
- （初回リリースのため履歴項目なし）

Fixed
- 各モジュールでの堅牢性向上（例）
  - API レスポンスのパース失敗や API 障害時に例外を投げずフェイルセーフで継続する挙動を採用（news/regime モジュール）。
  - DuckDB の executemany に空リストを渡さないようにガードし互換性を確保。
  - raw DB 値（NULL 等）に対する安全な処理（true_range の NULL 伝播制御等）を実装。
  - JSON mode でも前後に余計なテキストが混ざるケースを考慮し JSON 抽出を試みるロジックを実装。

Security
- 環境変数管理
  - OS 環境変数は .env による上書きから保護される設計（protected set）。
  - OpenAI API キーや各種トークンが未設定の場合は明示的なエラー（ValueError）を返すことで誤動作を防止。
- secrets（API キー等）は Settings 経由で取得し、必要な関数は引数で api_key を注入可能にしてテストや秘密情報の管理を容易に。

Notes / Migration
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を設定してください。未設定の場合は score_news / score_regime で ValueError を送出します。
- .env の自動読み込みを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）に依存します。初期データロードは ETL パイプラインを利用してください。
- 外部依存: openai SDK（OpenAI クライアント）および duckdb。テスト時は _call_openai_api をモックして API 呼び出しを差し替え可能。

今後の予定（TODO / Backlog）
- strategy / execution / monitoring の実装拡充（現バージョンではデータ取得・ファクター・NLP 周りが中心）。
- エンドポイント、Web UI、実取引連携の詳細な統合テスト・安全性検証。
- ai モジュールのより詳細なプロンプトチューニング、ロギング改善、コスト最適化（バッチ化・要約等）。

---