CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
日付はリリース日を示します。コード内容から推測できる機能・修正・設計上の注意点を記載しています。

Unreleased
----------
- 今のところなし。

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージの初期リリースを追加（kabusys v0.1.0）。
  - パッケージメタ情報:
    - __version__ = "0.1.0"
    - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理（kabusys.config）を実装:
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パースの堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の取り扱い。
  - 自動ロード無効化のフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数取得ユーティリティ Settings を提供（プロパティ経由）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、空文字が既定）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等の監視設定
    - CPU/MEMORY/DISK の閾値設定（%）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール（kabusys.ai）を実装:
  - ニュース NLP（kabusys.ai.news_nlp）:
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約して銘柄ごとのニュースを作成
      - OpenAI(gpt-4o-mini) の JSON モードを使ったバッチスコアリング（最大バッチサイズ 20）
      - 1銘柄あたりの記事数/文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
      - レスポンスバリデーション（JSON 復元ロジック含む）、スコア ±1.0 にクリップ
      - DuckDB への冪等書き込み（DELETE → INSERT）、部分失敗時に他銘柄の既存スコアを保護
      - 429 / ネットワーク断 / タイムアウト / 5xx について指数バックオフでリトライ
      - API キー未提供時は ValueError を送出
      - ルックアヘッドバイアス防止のため datetime.today() を参照しない（target_date ベース）

  - 市場レジーム判定（kabusys.ai.regime_detector）:
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成してレジーム（bull/neutral/bear）を判定
      - マクロキーワードで raw_news のタイトルをフィルタし、OpenAI に渡して macro_sentiment を算出
      - OpenAI 呼び出しは専用の内部実装を持ち、リトライ・5xx 判定・JSON パース失敗時は macro_sentiment=0.0 でフォールバック
      - レジームスコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
      - API キー未提供時は ValueError を送出
      - ルックアヘッドバイアス防止の設計

- 研究用機能（kabusys.research）を実装:
  - factor_research モジュール:
    - calc_momentum(conn, target_date)
      - mom_1m/mom_3m/mom_6m、ma200_dev（必要データ不足時は None）
    - calc_volatility(conn, target_date)
      - atr_20 / atr_pct / avg_turnover / volume_ratio（必要データ不足で None）
    - calc_value(conn, target_date)
      - per / roe（raw_financials の最新報告日までのデータを利用）
    - 設計: DuckDB (prices_daily, raw_financials) のみ参照し、本番発注 API にはアクセスしない

  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）
    - calc_ic(factor_records, forward_records, factor_col, return_col) — スピアマンのランク相関（IC）
    - rank(values) — 同順位処理は平均ランク
    - factor_summary(records, columns) — count/mean/std/min/max/median を計算
    - 外部ライブラリ非依存（標準ライブラリのみ）、ルックアヘッドバイアス対策済み

- データ基盤モジュール（kabusys.data）を実装:
  - calendar_management:
    - market_calendar を基にした is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供
    - market_calendar が未取得時は曜日ベース（土日休み）でのフォールバック
    - 最大探索日数制限で無限ループ防止
    - calendar_update_job(conn, lookahead_days) — J-Quants から差分取得して market_calendar を更新、バックフィルと健全性チェックを実装
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.pipeline と etl のインターフェース）
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックのためのユーティリティ（jquants_client / quality と連携を想定）
    - DuckDB テーブル有無チェック、最大日付取得などの内部ユーティリティ
  - jquants_client との統合ポイントを想定（fetch / save 関数を呼ぶ設計）

- 互換性 / 実行環境:
  - DuckDB を利用することを前提とした SQL 実装
  - OpenAI SDK（OpenAI クライアント）の利用を前提（gpt-4o-mini モデル）
  - 設計上、外部ネットワーク/API エラー時はフェイルセーフ（スキップして継続）する箇所が多い

Changed
- （初回リリースにつきなし）

Fixed
- （初回リリースにつきなし）

Security
- 環境変数の取り扱いについて:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY は機密情報のため .env を利用する場合は取り扱いに注意すること
  - 自動 .env 読込は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - Settings._require は未設定時に ValueError を送出して早期検出を支援

Notes / Migration / 運用上の注意
- OpenAI API キーが未設定だと score_news / score_regime は ValueError を投げます。CI やテストではモック（unittest.mock.patch）で _call_openai_api を差し替えてください。
- news_nlp と regime_detector はそれぞれ専用の _call_openai_api を持ち、モジュール間でプライベート関数を共有しない設計です。テスト時はモジュール単位で差し替えてください。
- DuckDB の executemany に空リストを渡すと問題になるため、コード中で空パラメータを渡さないガードを実装しています（部分書き込み保護）。
- 日付取扱いはすべて date / naive datetime を前提とし、ルックアヘッドバイアス防止のため datetime.today() の直接参照を避けています。
- calendar_update_job は外部 API（J-Quants）呼び出しに失敗した場合に例外をキャッチして 0 を返すフェールセーフな設計です。

今後の予定（推測）
- strategy / execution / monitoring パッケージの実装・公開（現在は __all__ に名前はあるがコードは未提示）
- テストカバレッジ拡充（OpenAI 呼び出し、DuckDB 操作、ETL の品質チェック）
- CLI / Cron ジョブや監視ダッシュボードの追加

もし特定リリースノートの形式や記載の粒度（例: さらに細かいモジュール別の変更履歴）を希望される場合は、どのレベルで詳述すべきか教えてください。コードの追加ファイルやコミット履歴があれば、より正確な CHANGELOG を作成できます。