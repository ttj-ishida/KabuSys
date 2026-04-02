CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 既知の問題:
  - kabusys.data.pipeline 内の内部ユーティリティ関数 `_get_max_date` の実装が途中で切れており（ソース内に "return date.fro" のような断片が存在）、正しい動作を期待できません。CI/リリース前に修正が必要です。
  - 一部モジュール（例: src/kabusys/data/__init__.py）が空のプレースホルダになっているため、パッケージ公開時にエクスポート整理が必要かもしれません。

0.1.0 - 2026-04-02
-----------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージ公開インターフェースとして __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export 形式・クォート・エスケープ・インラインコメント等に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定をプロパティ経由で取得。
    - 必須項目は _require によって未設定時に ValueError を送出（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
    - KABUSYS_ENV, LOG_LEVEL の検証（許容値のバリデーション）。
    - パス系設定は Path 型で返却（例: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）。
    - しきい値設定は float 化（CPU/MEM/DISK）。

- AI モジュール (src/kabusys/ai/)
  - news_nlp モジュール
    - score_news(conn, target_date, api_key=None)
      - raw_news と news_symbols を集約し、銘柄ごとに記事をまとめて OpenAI (gpt-4o-mini) に送信してセンチメントを算出。
      - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたり記事数・文字数上限を設計（過負荷対策）。
      - JSON mode レスポンスの厳密なバリデーションとスコアの ±1.0 クリップを実装。
      - API の一時エラー (429 / 接続断 / タイムアウト / 5xx) に対する指数バックオフ・リトライを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
      - 書き込みは部分置換（DELETE WHERE date=? AND code=? を executemany → INSERT）で、部分失敗時に既存スコアを保護。
    - calc_news_window(target_date) ユーティリティを提供（JST 基準の前日15:00〜当日08:30 を UTC naive datetime に変換）。
  - regime_detector モジュール
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime に日次で書き込み。
      - マクロニュース抽出は内部で news_nlp.calc_news_window を利用、OpenAI 呼び出しは独立実装（モジュール結合を避ける）。
      - API 呼び出し時のリトライ、JSON パース失敗時のフェイルセーフ（macro_sentiment=0.0）を実装。
      - DB へは冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。失敗時は ROLLBACK を試行し例外を伝播。

- Data プラットフォーム関連 (src/kabusys/data/)
  - calendar_management モジュール
    - JPX マーケットカレンダー管理のロジックを実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベース（土日除く）でフォールバック。
      - 最大探索範囲の制限や不整合（極端な将来日付）の健全性チェックを実装。
    - calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得して market_calendar を冪等保存する夜間バッチ処理。
      - バックフィル日数・健全性チェック・API エラー時のログ処理を実装。
  - pipeline / ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を実装（ETL 実行結果の構造化、品質問題やエラー一覧の保持、to_dict メソッド）。
    - 差分更新、バックフィル、品質チェックの設計方針とユーティリティ関数を追加（_table_exists 等）。
    - src/kabusys/data/etl.py で ETLResult を再エクスポート。
    - （注意）内部実装の一部が途中で切れている箇所あり（詳細は Unreleased を参照）。

- Research / ファクター計算 (src/kabusys/research/)
  - factor_research モジュール
    - calc_momentum(conn, target_date)
      - mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date)
      - 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。部分ウィンドウでも安定して動作。
    - calc_value(conn, target_date)
      - raw_financials から最新財務を結合し PER / ROE を算出（EPS が 0/欠損なら None）。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])
      - 指定ホライズン先の将来リターンをまとめて取得（性能考慮でリードを用いた単一クエリ）。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンランク相関（IC）を実装（同順位は平均ランクで扱う）。有効レコードが 3 未満なら None。
    - rank(values), factor_summary(records, columns)
      - ランク変換、統計サマリー（count/mean/std/min/max/median）を実装。
  - research パッケージの __init__ で主要な関数を再エクスポート（zscore_normalize は kabusys.data.stats から）。

Changed
- なし（初版のため既存リリースとの差分はありません）。

Fixed
- API 呼び出しまわりの堅牢性向上（news_nlp / regime_detector）
  - OpenAI API の一時障害や 5xx を考慮したリトライとバックオフを導入し、致命的失敗にならないフェイルセーフ挙動を採用。

Security
- なし（特記事項なし）。

Notes / 運用上の注意
- OpenAI API の利用
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必要です。未設定時は ValueError を送出します。
  - API 呼び出しは gpt-4o-mini を想定した JSON Mode を利用しています。レスポンス形式のバリデーションを厳密に行っています。
- 環境変数
  - 複数の必須環境変数があります（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。settings を利用して不足を検出してください。
- データベース
  - 各機能は DuckDB 接続を引数に受け取り prices_daily / raw_news / ai_scores / market_calendar / raw_financials 等のテーブルを参照します。テーブルスキーマの整合性を事前に確保してください。

今後の予定（例）
- pipeline._get_max_date の修正。
- パッケージの公開時に data/__init__.py などのエクスポート整理。
- ユニットテスト強化（OpenAI 呼び出しのモックを含む）と CI 設定。

--- 
記載はソースコードの実装と docstring から推測してまとめています。実際のリリースノート作成時は変更差分（git のコミット履歴等）に基づく追補を推奨します。