# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。

リリースポリシー: ここに記載されたバージョンはパッケージの初期公開相当の機能セットを示します。

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージの初期リリース（kabusys v0.1.0）
  - パッケージメタ:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールとして data / strategy / execution / monitoring をエクスポート。
- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートの検出は __file__ を起点に親ディレクトリを走査し .git または pyproject.toml を基準として行うため、CWD に依存しない動作。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護（protected）され、.env の上書きを防止。
  - .env パーサを実装:
    - 空行・コメント行（#）・`export KEY=val` 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理・対応する閉じクォート検出。
    - クォートなしの場合のインラインコメント判定（直前がスペース/タブの場合のみコメント扱い）。
    - 無効行は無視。
  - .env 読み込み失敗時には警告を出す。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得可能（必須変数未設定時は ValueError を送出）。
    - J-Quants / kabu ステーション / Slack / DB パスなどのプロパティを実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証（有効な値セットに制限）。
    - デフォルトの DB パス: DUCKDB_PATH="data/kabusys.duckdb"、SQLITE_PATH="data/monitoring.db"。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None)
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
      - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1 銘柄あたり最新最大 10 件、文字数トリムあり）。
      - 最大 _BATCH_SIZE（デフォルト 20）件ごとに OpenAI（gpt-4o-mini）へバッチ送信し JSON Mode を使用して結果を受領。
      - API 呼び出しは 429／ネットワーク断／タイムアウト／5xx に対して指数バックオフでリトライ。
      - レスポンスの厳格バリデーションを実装（JSON 抽出、"results" リスト、各要素に code/score、未知コードは無視、スコアは ±1 にクリップ）。
      - スコア取得後は ai_scores テーブルへ冪等的に置換（DELETE→INSERT、部分失敗時に既存スコアを保護）。
      - DuckDB の executemany の制約（空リスト不可）に配慮。
      - テスト容易性のため _call_openai_api を patch して差し替え可能（unittest.mock を想定）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム ('bull'/'neutral'/'bear') を判定。
      - ma200_ratio は prices_daily の target_date 未満のデータのみを使用（ルックアヘッド回避）。
      - マクロニュースは news_nlp.calc_news_window を使ってフィルタし、最大 20 件までを LLM に投げる。
      - OpenAI 呼び出しは再試行ロジックを持ち、API 失敗時は macro_sentiment=0.0 としてフェイルセーフに継続。
      - レジームスコアの閾値（BULL/BEAR）は定数化されており、結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - LLM 呼び出し実装は独立しており、news_nlp の内部関数とは共有していない（モジュール結合の抑制）。
- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - calc_volatility(conn, target_date): 20 日 ATR／ATR 比率／20 日平均売買代金／出来高比率等を計算。
    - calc_value(conn, target_date): raw_financials から最新財務情報を取得して PER／ROE を計算（EPS が 0/欠損の場合は None）。
    - いずれも DuckDB の SQL を駆使して実装。外部 API 呼び出しは行わない。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（営業日ベース）の将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）計算。十分なサンプルがない場合は None。
    - rank(values): 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を標準ライブラリのみで計算。
    - 外部依存（pandas 等）を用いず、標準ライブラリと DuckDB のみで完結。
- Data モジュール (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理 API と連携する夜間バッチ処理 calendar_update_job(conn, lookahead_days=90) を実装。
      - market_calendar の最終取得日を確認し差分取得。バックフィルと健全性チェックを実装（直近 _BACKFILL_DAYS を常に再取得、last_date が極端に未来であればスキップ）。
      - J-Quants クライアント（jquants_client）を利用した差分取得と idempotent 保存を想定。
    - 営業日判定ユーティリティ:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar のデータがない場合は曜日ベース（土日休み）でフォールバックする設計。
      - DB に部分的データがある場合は DB 値を優先し、未登録日は曜日フォールバックで一貫した結果を返す。
      - 探索は _MAX_SEARCH_DAYS により制限し無限ループを防止。
  - ETL / Pipeline (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを提供（target_date、取得件数、保存件数、quality_issues、errors 等を含む）。
      - to_dict() で quality_issues をシリアライズ可能に変換。
      - has_errors / has_quality_errors のユーティリティを提供。
    - 差分更新のヘルパー関数（テーブル存在チェック、最大日付取得など）を実装し、初回ロード日やバックフィル方針を定義。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
- テストフレンドリー設計
  - OpenAI 呼び出しのラッパー関数をモジュール単位で用意し、unit test で差し替え可能（patch 対応）。
- ロギング・フェイルセーフ
  - 各種 API/DB 失敗時に例外を上位に投げる箇所と、警告ログを出してフェイルセーフ（0.0 やスキップ）で継続する箇所を明確に分離。
  - DuckDB の実装上の互換性（executemany の空リスト不可、日付型の扱い）に注意した実装。

Security, Requirements and Notes
- AI 機能（score_news, score_regime）は OpenAI API キー（引数 api_key または環境変数 OPENAI_API_KEY）が必須。未指定時は ValueError を送出する。
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は Settings のプロパティから取得し、未設定時は明示的なエラーを発生させる設計。
- .env の自動ロードは開発時に便利だがテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD で明示的に無効化できる。
- DuckDB を主なローカル分析 DB として使用。SQL は直接埋め込みで記述されているため、DuckDB の SQL 方言を前提とする。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- 初期リリースのため該当なし。

Removed
- 初期リリースのため該当なし。

Acknowledgements / Implementation details
- コードは「ルックアヘッドバイアス対策」を方針にしており、datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を利用しつつ、API の不整合に備えたパース回復ロジックを含む。
- SQL 部分は性能と DuckDB 互換性を考慮したウィンドウ関数中心の実装。

今後の予定（例）
- strategy / execution / monitoring の具現化（取引ロジック・注文実行・監視アラートの実装）
- 更なるテストカバレッジと CI/CD の整備
- J-Quants / kabu ステーションとの具体的な統合処理（API クライアント実装の追加）

[0.1.0]: https://example.com/releases/0.1.0