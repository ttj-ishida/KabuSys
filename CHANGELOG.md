CHANGELOG
=========

すべての重要な変更はここに記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリース日付は YYYY-MM-DD 形式です。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開 API の __all__ を定義（data, strategy, execution, monitoring）。
- 環境設定/ロード機能
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーを実装（_parse_env_line）。
      - export KEY=val 形式に対応。
      - シングル/ダブルクオート内でのバックスラッシュエスケープ対応、インラインコメント無視処理。
      - クォートなしの場合は '#' の直前が空白／タブのときのみコメント扱いにする等、細やかな挙動。
    - _load_env_file: protected 引数により OS 環境変数を上書きから保護する挙動を実装。
    - Settings クラスでアプリケーション設定をプロパティとして公開（例: jquants_refresh_token, kabu_api_password, slack_bot_token, duckdb_path, sqlite_path 等）。
      - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
      - is_live / is_paper / is_dev ヘルパーを提供。
- AI モジュール（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 設計上の特徴:
      - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
      - 1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
      - 最大バッチサイズ _BATCH_SIZE（20）で分割して API に送信。
      - 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ、その他エラーはスキップ（フェイルセーフ）。
      - レスポンスは厳密な JSON を期待するが、前後に余計なテキストが混ざる場合に最外の {} を抽出してリカバーする処理を実装。
      - バリデーションを行い、未知コードや数値化できないスコアは無視。スコアは ±1.0 にクリップ。
      - DuckDB の executemany の制約に対応し、空リストを渡さないガードを実装。
    - 公開関数 score_news(conn, target_date, api_key=None) を提供。成功時は書き込み銘柄数を返す。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルに冪等書き込み。
    - 処理の特徴:
      - prices_daily と raw_news を参照して MA 比率・マクロニュースを取得。
      - マクロニュースは独自の LLM 呼び出し実装で gpt-4o-mini を用い、JSON 形式（{"macro_sentiment": 0.0}）を期待。
      - API 呼び出しはリトライ・バックオフを実施し、失敗時は macro_sentiment=0.0 として処理を継続（フェイルセーフ）。
      - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照せず、target_date 未満のデータのみを使用。
    - 公開関数 score_regime(conn, target_date, api_key=None) を提供。成功で 1 を返す。
  - src/kabusys/ai/__init__.py で score_news を公開。
- Research モジュール（ファクター・特徴量探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）等のファクター計算関数を実装。
    - 関数:
      - calc_momentum(conn, target_date) → 各銘柄の mom_1m/mom_3m/mom_6m/ma200_dev を返す。MA200 データ不足時は None。
      - calc_volatility(conn, target_date) → atr_20, atr_pct, avg_turnover, volume_ratio 等を返す。ATR データ不足時は None。
      - calc_value(conn, target_date) → per, roe を返す（raw_financials の最新レコードを参照）。
    - DuckDB 上の SQL を中心に実装し、外部 API へのアクセスは行わない設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を提供。
    - 特徴:
      - calc_forward_returns は複数ホライズンを一度に取得する効率的なクエリを実装（horizons のバリデーションあり）。
      - calc_ic は Spearman ランク相関を算出し、サンプル数が不足する場合は None を返す。
      - rank は同順位（ties）を平均ランクで扱う実装で、丸め（round(..., 12)）により浮動小数点の ties 検出漏れを軽減。
      - factor_summary は count/mean/std/min/max/median を計算（None を除外）。
  - src/kabusys/research/__init__.py で主要関数を公開（calc_momentum, calc_value, calc_volatility, zscore_normalize 等）。
- Data モジュール（カレンダー管理・ETL）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が存在しない場合は曜日ベースのフォールバック（週末を非営業日）を行う一貫した設計。
      - next/prev/get 関数は DB 登録値を優先し、未登録日は曜日ベースで補完。最大探索は _MAX_SEARCH_DAYS（60）で無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント経由で差分取得し、バックフィル（直近 _BACKFILL_DAYS）と健全性チェック（将来日付の異常検出）を行い冪等保存する。
    - DuckDB 値の date 型取り扱いや NULL の警告ログなど堅牢化。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの基盤実装と ETLResult データクラスを提供。
      - 差分取得、jquants_client 経由での idempotent 保存、品質チェックの統合を想定した設計。
      - ETLResult は品質問題やエラーの一覧を保持し、to_dict() によりシリアライズ可能。
      - _get_max_date 等のユーティリティを実装（テーブル存在チェックや最大日付の取得）。
    - 実装方針として「バックフィル」「部分失敗時の既存データ保護」「品質チェックは収集して呼び出し元が判断」を採用。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
  - カレンダー/ETL は DuckDB を前提に書かれている（DuckDB の制約を考慮した実装上の配慮あり）。
- データクライアント（参照）
  - data モジュール内で jquants_client を参照（fetch/save 関数を利用する前提）。実際のクライアント実装は外部（別モジュール）で提供される想定。

Fixed
- DuckDB executemany の互換性対応
  - news_nlp.score_news などで executemany に空リストを渡さないようガードを追加（DuckDB 0.10 の制約に対応）。

Security
- 環境変数の取り扱いに注意
  - Settings._require により必須環境変数未設定時は明示的に ValueError を送出。自動ロードは保護セットを用い OS 環境変数の上書きから防御。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode（response_format={"type":"json_object"}）を使用する設計。API 失敗時の挙動は各モジュールで明示的に定義（リトライ／フォールバック）。
- ルックアヘッドバイアス防止のため、AI 系処理・研究処理は内部で date.today() を参照せず、明示的な target_date を必須引数として受け取る設計。
- 多くの DB 書き込みは「冪等（DELETE → INSERT / ON CONFLICT）」で実装され、部分失敗時の既存データ保護を意識している。

Authors
- このリリースは kabusys コードベースに基づいて生成されました。