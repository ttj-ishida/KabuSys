CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
リリースは semver に従います。

Unreleased
----------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ公開インターフェースを定義 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルート自動検出機能を導入（.git または pyproject.toml を探索）。
  - .env/.env.local の自動ロード機構を実装（無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（OS の既存キーは保護され上書きされない）。
  - .env パーサを強化：
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォート無し値のインラインコメント処理（'#' の直前が空白/タブの場合はコメントと判定）
    - 無効行（空行・コメント）を無視
  - 必須環境変数取得時に未設定なら ValueError を投げる _require() を提供。
  - Settings クラスでアプリケーション設定をプロパティとして提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - KABUSYS_ENV の有効値制約 (development, paper_trading, live) と LOG_LEVEL の検証実装。
  - 環境判定ユーティリティ: is_live / is_paper / is_dev。

- AI (自然言語処理) モジュール
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST 相当）に基づき raw_news と news_symbols から記事を銘柄ごとに集約。
    - 1 銘柄あたり最大記事数および文字数でトリムする仕組み（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI（gpt-4o-mini）にバッチ送信して銘柄別センチメント（-1.0〜1.0）を取得。バッチサイズは最大 20 銘柄。
    - JSON Mode を利用したレスポンス検証と、ノイズを含む場合の復元ロジック（最外の {} を抽出）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ処理。
    - レスポンスのバリデーション機構（results 配列、code の正規化、スコア数値検証、スコアクリップ）。
    - スコア書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api の patch を推奨）。
    - API キー未設定時は明示的に ValueError を送出。
    - 書き込み件数を返す（成功時は書き込んだ銘柄数、失敗時は 0）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - マクロキーワードのフィルタリング実装（日本・米国・グローバルの主要キーワード群）。
    - OpenAI 呼び出し結果の JSON パース、リトライ（429/ネットワーク/5xx）とフェイルセーフ（API 失敗時 macro_sentiment=0.0）。
    - レジームスコア合成ロジック（スコア clip と閾値判定）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー未設定時は ValueError を送出。
    - テストのために _call_openai_api をモック可能に設計。

  - ai パッケージ公開 (src/kabusys/ai/__init__.py)
    - score_news を再エクスポート。

- データ処理 / 研究系モジュール
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装（取得数、保存数、品質問題、エラー一覧、ユーティリティメソッド）。
    - パイプラインで使用するユーティリティ関数（テーブル存在確認、最大日付取得など）。
    - etl モジュールで ETLResult を再エクスポート。

  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を利用した営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB データ優先の判定ロジック、未登録日は曜日（平日）フォールバック。
    - next/prev で最大探索日数制限（_MAX_SEARCH_DAYS）を導入し無限ループ防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar テーブルへ冪等的に保存。バックフィル日数と健全性チェック（将来日付の過度な飛躍を検出）を実装。
    - DB が未取得の場合は曜日ベースのフォールバックを使用。

  - 研究用ファクタ計算 (src/kabusys/research)
    - factor_research.py:
      - モメンタム (1/3/6M)、ma200 乖離、ATR（20日）、平均売買代金・出来高比率、PER/ROE（raw_financials から取得）などを計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB を用いた SQL ベースの計算、結果は (date, code) をキーとする dict のリストで返却。
      - 設計上、外部 API には依存せず本番口座へのアクセスは行わない。
    - feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - Spearman（ランク相関）による IC 計算、中央値・標準偏差等の統計量算出を実装。
    - research パッケージ __all__ を整備して主要関数をエクスポート。

- データアクセス周り
  - DuckDB を用いることを前提に実装（多くのモジュールで DuckDBPyConnection を受け取る設計）。
  - 各種処理でトランザクション（BEGIN/COMMIT/ROLLBACK）と例外処理を適切に実装。

Fixed
- N/A（初回公開）

Changed
- N/A（初回公開）

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / 内部設計上の重要点
- ルックアヘッドバイアス回避:
  - AI / リサーチ系関数は datetime.today() / date.today() を直接参照せず、必ず target_date 引数で日時を受け取る設計。
  - DB クエリも target_date に対して厳密な排他条件（date < target_date 等）を使いルックアヘッドを防止。
- フェイルセーフ設計:
  - OpenAI API の失敗時に例外を上位へ伝播させずフォールバック動作（例: macro_sentiment=0.0）で継続する箇所がある。
  - 一方で API キー未設定は明示的な ValueError を送出してユーザーに通知。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）を patch できるようにしてあり、単体テストで外部ネットワーク呼び出しをモック可能。
- DB 互換性考慮:
  - DuckDB の executemany の空パラメータ制約を考慮して空リストチェックを行う等、実運用での互換性に配慮。

今後の予定（参考）
- Strategy、execution、monitoring の実装（パッケージは __all__ に定義済み）。
- J-Quants / kabuステーション クライアントの具体的な永続化・取得処理の詳細実装とテストカバレッジ拡充。