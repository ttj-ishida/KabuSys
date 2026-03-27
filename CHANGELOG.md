CHANGELOG
=========

すべての日付は YYYY-MM-DD 形式。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（次リリースに向けた変更はここに記載）

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - src/kabusys/__init__.py によりバージョンと公開モジュールを定義（__version__="0.1.0", __all__ = ["data", "strategy", "execution", "monitoring"]）。

- 環境設定・読み込み機能（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export KEY=val 形式やシングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱い等に対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き除外。
  - Settings クラスを提供（settings インスタンスをエクスポート）。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須チェック。
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスと Path 変換。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の判定プロパティ。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ JSON Mode でバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する機能を実装。
  - タイムウィンドウ定義（JST ベース）および calc_news_window(target_date) を提供。target_date に依存するが datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス回避）。
  - バッチ処理: 最大 _BATCH_SIZE=20 銘柄、1 銘柄あたり最大 _MAX_ARTICLES_PER_STOCK=10 件、最大文字数トリム _MAX_CHARS_PER_STOCK=3000。
  - エラー耐性: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフリトライ（_MAX_RETRIES／_RETRY_BASE_SECONDS）。それ以外のエラーはスキップして継続（フェイルセーフ）。
  - レスポンスの堅牢なバリデーション実装（JSON 抽出、"results" リストと各要素の code/score のチェック、スコアの数値化と ±1.0 クリップ）。
  - DB 書き込みは部分失敗に備え、スコア取得済みコードのみ DELETE→INSERT の形で置換（idempotent、DuckDB executemany の空パラメータ回避）。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の market_regime を算出・保存する機能を実装。
  - マクロ記事抽出はニュース NLP の calc_news_window を利用し、タイトルベースでマクロキーワードにマッチする記事を取得。
  - OpenAI 呼び出しは JSON Mode を用い、失敗時は macro_sentiment=0.0 で継続するフェイルセーフ設計。API 呼び出しのリトライ・5xx 判定・JSON パースエラーのハンドリングを実装。
  - レジーム合成はクリップ（-1.0〜1.0）し、閾値に基づき "bull"/"neutral"/"bear" を決定。結果は market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。API キーは引数 or 環境変数 OPENAI_API_KEY。

- Data モジュール（src/kabusys/data/*）
  - calendar_management.py
    - JPX 市場カレンダー管理機能を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が存在しない場合は曜日ベースでフォールバック（週末を非営業日扱い）。DB 登録値があれば DB を優先、未登録日はフォールバックで補完する一貫したロジック。
    - calendar_update_job(conn, lookahead_days=90) を実装。J-Quants API から差分取得し market_calendar を冪等的に更新。直近 BACKFILL_DAYS を再フェッチ、last_date の健全性チェックなどを含む。
    - 市場カレンダーがまばらな場合でも next/prev/get_trading_days が一貫して動作するよう設計。
  - pipeline.py
    - ETL パイプライン補助（差分取得、保存、品質チェックの流れ）用ユーティリティ。_get_max_date 等の内部ユーティリティを実装。
    - ETLResult dataclass を定義（target_date, fetched/saved counts, quality_issues, errors 等）。has_errors / has_quality_errors / to_dict を備える。
  - etl.py
    - pipeline.ETLResult を再エクスポート（kabusys.data.ETLResult）。

- Research モジュール（src/kabusys/research/*）
  - factor_research.py
    - ファクター計算実装（momentum / volatility / value）。
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev（200 日 MA 乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）などを計算。true_range の NULL 伝播を明示的に制御。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を算出。EPS が 0/欠損の場合は None。
    - DuckDB を活用した SQL ベースの実装で外部 API には依存しない。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 翌日/翌週/翌月等の将来リターン計算を実装（horizons デフォルト [1,5,21]、入力検証あり）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク）相関を実装。有効レコード数 < 3 の場合は None。
    - rank(values): 同順位は平均ランクにするランク化ユーティリティ（丸め処理で ties の誤差を抑制）。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリ関数。
  - research パッケージの __init__ で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats 由来）。

Misc / Implementation notes
- OpenAI クライアント呼び出しは各モジュールで独自の _call_openai_api を持ち、テスト時はパッチ可能（unittest.mock.patch 対応）に設計。
- 多くのモジュールで「ルックアヘッドバイアス防止」を明示的に設計（datetime.today()/date.today() を直接参照しない、SQL で date < target_date など）。
- API 呼び出し・DB 書き込みにおけるフェイルセーフと冪等性を重視（部分失敗時に既存データを保護する実装）。
- DuckDB のバインドや executemany の制約（空リスト不可）に配慮した実装が多く含まれる。

Known limitations / Notes
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY が必須（未設定時は ValueError を送出する関数あり）。
- ai/news 系は gpt-4o-mini と JSON Mode を前提に実装しているため、他モデルや旧 SDK での互換性は検証が必要。
- 一部設計（例: PER/ROE のみ提供）は初期段階であり、PBR・配当利回り等は未実装。

Breaking Changes
- 初回リリースのため無し。

Security
- 環境変数・機密情報の取り扱い: OS 環境変数は .env ファイルによって上書きされないよう protected 処理を導入。自動ロードは環境変数で無効化可能。

Contributors
- 初回コミットに含まれる実装を元に自動生成（README/CONTRIBUTORS はソースに含まれていません）。今後のリリースで明示します。

----- 

リリース内容や表現について追記や修正希望があれば、特に強調したい機能（例えば AI 関連のフェイルセーフ動作や ETL の振る舞い）を教えてください。