CHANGELOG
=========

すべての注目すべき変更履歴をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。

v0.1.0 - 2026-04-03
-------------------

Added
- 基本パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報 (src/kabusys/__init__.py) を導入。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード実装。
  - プロジェクトルート探索ロジックを導入（.git または pyproject.toml を起点に探索）。これにより CWD に依存せず配布後も正しく .env を参照可能。
  - .env/.env.local の優先度管理（OS 環境 > .env.local > .env）。.env.local は override=True（OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env パーサ実装:
    - コメント行・空行・export プレフィックス対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い。
    - クォートなし値の '#' によるコメント判定（直前が空白/タブの場合のみ）。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして公開（J-Quants、kabuステーション、LINE、DB パス、監視閾値、ログレベル等）。
  - 設定値のバリデーション:
    - KABUSYS_ENV は {development, paper_trading, live} のみ許可。
    - LOG_LEVEL は標準ログレベルのみ許可。
    - 必須変数未設定時は ValueError を送出する _require 関数を採用。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して銘柄ごとのセンチメント ai_score を生成し ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST を UTC に変換) を提供する calc_news_window 関数を追加。
    - 銘柄ごとに記事を集約して最大記事数／最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - OpenAI へのバッチ送信（最大 _BATCH_SIZE=20 銘柄／コール）、JSON mode を利用したレスポンス検証。
    - API 呼び出しのリトライ（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）、非再試行例外は即スキップ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" 構造、コード整合性、数値チェック、±1.0 でクリップ）。
    - 書込みは部分失敗に強く、取得できた銘柄コードのみ DELETE → INSERT を行う実装（DuckDB の executemany 空リスト制約への対策あり）。
    - テスト容易性のため内部の OpenAI 呼び出し関数を patch 可能に設計（kabusys.ai.news_nlp._call_openai_api）。
    - API キー未設定時は ValueError を送出。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225 連動ETF）の 200 日 MA 乖離とマクロニュース LLM センチメントを合成して market_regime テーブルへ冪等的に書き込む。
    - MA 計算（200 日）および不足時のフォールバック（データ不足時は中立値 1.0 を返す）。
    - マクロニュース抽出はキーワードベース（_MACRO_KEYWORDS）でタイトルを取得し、最大件数で制限。
    - OpenAI 呼び出し: model=gpt-4o-mini、JSON レスポンスをパースして macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げない）。
    - レジームスコア合成は MA 成分 70% / マクロ成分 30%、スコアは -1.0〜1.0 にクリップ。閾値により "bull"/"neutral"/"bear" を判定。
    - DB 書込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。失敗時は ROLLBACK を試行して例外を伝播。
    - テスト用に内部の OpenAI 呼び出し関数を patch 可能（kabusys.ai.regime_detector._call_openai_api）。
    - Look-ahead バイアス回避の設計（内部で date.today() を参照しない、prices_daily クエリは target_date 未満を参照）。

  - ai パッケージの __init__ で score_news を公開。

- リサーチ / ファクター (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から最新財務を取り込み PER、ROE を計算。EPS が 0/欠損の場合は None。
    - DuckDB のウィンドウ関数を活用した SQL ベース実装。戻り値は date/code を含む dict のリスト。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。horizons の検証あり（1〜252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman IC（ランク相関）を計算。有効レコード数が少ない場合は None を返す。
    - rank(values): 同順位は平均ランクを返すランク関数（丸め処理で ties 対応）。
    - factor_summary(records, columns): count/mean/std/min/max/median 等の統計サマリーを算出。
  - research パッケージの __init__ で主要関数を公開。

- データ / カレンダー / ETL (src/kabusys/data/)
  - calendar_management.py:
    - 市場カレンダー管理機能を提供:
      - is_trading_day(conn, d), is_sq_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, s, e)
    - market_calendar が未取得の場合の曜日ベースフォールバック（DB 登録があれば DB 値優先）。
    - 最大探索日数 (_MAX_SEARCH_DAYS) による無限ループ防止、カレンダー更新用の calendar_update_job 実装（J-Quants から差分取得し保存）。
    - calendar_update_job はバックフィル、健全性チェックを行い、fetch/save の例外を捕捉して安定動作。
  - pipeline.py:
    - ETLResult dataclass を導入（ETL の取得数／保存数／品質問題／エラーを保持）。
    - ETL の差分更新・backfill・品質チェックを想定した設計（詳細実装の骨子）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得ロジックなど。
  - etl.py:
    - data.pipeline.ETLResult を再エクスポート。

Changed
- 設計方針として、AI スコアリング系およびレジーム判定でルックアヘッドバイアスを避けるため、
  datetime.today()/date.today() を直接参照しない（すべて target_date 引数に基づく設計）。

Fixed
- （初版のため該当なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供。未設定時は明確に例外を送出して誤操作を防止。

Notes / 既知の挙動
- DuckDB に対する executemany の振る舞い（空リスト不可など）に配慮した実装が多数（ai スコア書き込み等）。
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON mode を利用。API 変化に備えてエラーハンドリングを広めに取っている（500 系はリトライ、非5xx はスキップ）。
- テストしやすさを考慮し、OpenAI 呼び出し箇所は patch 可能（モジュール内のプライベート関数を差し替えられる設計）。
- 一部モジュールは jquants_client や quality モジュール等外部依存を想定（実際の API クライアント実装が別モジュールにある前提）。

今後の予定（提案）
- ドキュメント追加: 各関数の使用例や DB スキーマ例を README / API リファレンスに追加
- テスト追加: DuckDB を用いた統合テスト、OpenAI 呼び出しをモックした単体テスト
- エラー監視: ETLResult の活用による監査ログ・アラート連携

--- 

（この CHANGELOG は現在のソースコードから推測して作成しています。実際のリリースノートとして採用する際は、実装済み API、リリース日、影響範囲をプロジェクト実作業に合わせて補正してください。）