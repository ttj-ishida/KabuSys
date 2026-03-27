CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」準拠です。

現在のバージョン
----------------

0.1.0 - 2026-03-27
+++++++++++++++++

Added
- 基本情報
  - パッケージ初期リリース (バージョン: 0.1.0)。パッケージメタデータ: src/kabusys/__init__.py に __version__ を追加し、主要サブパッケージを __all__ で公開。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して .env, .env.local を自動読み込み（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数を保護する protected set を導入し、.env/.env.local の上書き挙動を制御。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメントの扱い(クォート有無での違い)を実装。
    - 読み込み失敗時は警告を発行。
  - 設定プロパティ:
    - J-Quants / kabuステーション / Slack / DB パス (DuckDB/SQLite) / 環境 (development/paper_trading/live) / ログレベル 等の取得メソッド。
    - 必須環境変数チェック（_require）により未設定時は ValueError を送出。
    - is_live/is_paper/is_dev ヘルパー。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して各銘柄ごとのセンチメント ai_score を算出。
    - 時間ウィンドウ計算 (前日15:00 JST〜当日08:30 JST) を calc_news_window で提供（UTC naive datetime を返す）。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ごとに API コール。
    - 1銘柄あたりのトークン肥大化対策: _MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK によるトリム。
    - リトライ: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフと再試行。
    - レスポンス検証: JSON 抽出、"results" の構造検証、未知コードの無視、スコア数値変換、±1.0 でクリップ。
    - DB 書き込み: 部分失敗時に既存スコアを守るため、取得済みコードのみ DELETE → INSERT を行う。DuckDB の executemany の挙動への配慮あり。
    - 主要 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。API キーは引数または環境変数 OPENAI_API_KEY を参照。
  - レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動）を用いた 200 日移動平均乖離（ma200_ratio）と、マクロニュースの LLM センチメントを重み付き合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース取得は news_nlp.calc_news_window を利用、raw_news からキーワードでフィルタ。
    - LLM 呼び出しは独立実装（news_nlp とは共有しない）で gpt-4o-mini を使用。API エラー時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 合成スコア: 70%(ma) / 30%(macro) の加重、クリップして閾値でラベル付け。
    - DB 書き込み: market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）登録。
    - 主要 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。API キーの未設定は ValueError。

- Data モジュール (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー（market_calendar）を扱うユーティリティを提供。
    - 営業日判定ロジック:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - DB にデータがある場合は DB 値を優先。未登録日は曜日ベース（平日）でフォールバック。
      - 最大探索日数 (_MAX_SEARCH_DAYS) を設定し無限ループを回避。
      - market_calendar が未作成・空の場合のフォールバック挙動を明確化。
    - 夜間バッチ更新 job (calendar_update_job):
      - J-Quants から差分取得し market_calendar を IDempotent に更新。
      - バックフィル（直近 _BACKFILL_DAYS 再取得）・健全性チェック（将来日付の異常検知）・API 例外ハンドリング実装。
    - DuckDB から返る日付値の安全変換ユーティリティ等を実装。
    - jquants_client との連携を想定（fetch_market_calendar / save_market_calendar 呼び出し）。
  - ETL / パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - ETLResult dataclass を定義し ETL 実行結果を構造化して返却 / ログ用辞書化 (to_dict) を提供。
    - 差分更新・バックフィル・品質チェック（quality モジュール）を行うパイプライン設計を想定。J-Quants クライアントとの連携点を確保。
    - ETLResult を data.etl 経由で再エクスポート。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
    - 設計上、品質チェックは Fail-Fast しない（全件収集し呼び出し元で判断する）。
  - 依存・前提:
    - DuckDB を主な永続化およびクエリ基盤として使用。

- Research モジュール (src/kabusys/research/)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日 MA 乖離）を prices_daily から計算。データ不足時は None。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio などのボラティリティ・流動性指標を計算。true_range の NULL 伝播制御により集計精度を担保。
    - calc_value: raw_financials から直近財務 (eps, roe) を取得し PER/ROE を計算。EPS が 0 または欠損時は None。
    - 全関数は DuckDB 接続を受け取り、prices_daily/raw_financials のみ参照（外部 API へのアクセスなし）。
    - 結果は (date, code) をキーとする dict のリストで返す。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 与えた horizons（デフォルト [1,5,21]）に対する将来リターン計算。入力バリデーション（horizons は 1〜252）あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。有効レコードが 3 未満なら None。
    - rank: 同順位は平均ランクを返すランク変換。浮動小数点の丸めで ties を安定検出。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 実装は標準ライブラリのみで依存を最小化。

- パッケージ公開 API 整備
  - ai.__init__, research.__init__ で主要関数を明示的に再エクスポート。

Security / Reliability / Design notes
- ルックアヘッドバイアス回避:
  - datetime.today()/date.today() を関数内部で参照しない設計（すべて target_date ベース）。
  - ニュース・価格クエリは target_date 未満・ウィンドウ制御等でルックアヘッドを防止。
- フェイルセーフ設計:
  - OpenAI API の失敗時は例外を投げずに 0.0（中立）やスキップで継続する箇所を多数実装。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK の失敗は警告ログで通知。
- OpenAI SDK 例外ハンドリング:
  - RateLimitError / APIConnectionError / APITimeoutError / APIError を考慮したリトライ戦略とログ出力。
  - APIError の status_code を安全に取得して 5xx 系のみリトライ対象とする処理。
- DuckDB 互換性考慮:
  - executemany の空リスト禁止への対応（空時に呼ばない）。
  - 日付型の取り扱いを安全化（_to_date ユーティリティ等）。

Notes / Breaking changes
- 初回リリースのため Breaking changes はありません。

Unreleased
----------
- なし

補足
- 上記はソースコードの内容から推測して作成した変更履歴です。実際のリリースノート作成時は、変更差分やコミット履歴・リリース担当者による確認を行ってください。