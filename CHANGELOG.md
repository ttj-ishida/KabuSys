CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はこのコードスナップショット作成日です: 2026-04-01

Unreleased
----------

(なし)

0.1.0 - 2026-04-01
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開用の __init__ を追加（__version__ = "0.1.0", __all__ 宣言）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local ファイルと OS 環境変数を統合して読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（配布後も動作）。
  - .env パーサを実装:
    - コメント行/空行無視、`export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなし値ではインラインコメント判定をスペース/タブ直前の `#` のみとする挙動。
  - _load_env_file による protected（既存 OS 環境変数）保護付き上書き制御。
  - Settings クラスを提供し、環境変数アクセスをラップ:
    - J-Quants / kabu ステーション / Slack / データベース（duckdb/sqlite） / 監視閾値 / システム設定（env, log_level）などをプロパティとして公開。
    - 必須変数未設定時は明確な ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
    - Path 型や float 型への変換を行うプロパティを用意。
    - is_live / is_paper / is_dev のヘルパー。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してセンチメントを算出。
      - バッチサイズ、記事数・文字数上限、タイムウィンドウ（JST基準）の厳密化（前日15:00〜当日08:30 JST → UTC変換）。
      - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ実装。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code・score 検証、スコアの ±1.0 クリップ）。
      - DuckDB への書き込みは部分失敗に備えて「取得済みコードのみ」DELETE → INSERT で冪等処理。
      - テスト用に _call_openai_api を patch 可能（テスト容易性を配慮）。
    - calc_news_window(target_date) ユーティリティを公開。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して
        市場レジーム ('bull' / 'neutral' / 'bear') を判定・保存。
      - マクロニュース取得は news_nlp.calc_news_window と raw_news クエリで実装。マクロキーワードリストを用いたフィルタリング。
      - OpenAI 呼び出しは gpt-4o-mini + JSON mode、リトライ・例外ハンドリングあり。API 失敗時は macro_sentiment=0.0（フェイルセーフ）。
      - レジームスコア合成と閾値判定、DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時 ROLLBACK を試行）。
      - テスト用に _call_openai_api を patch 可能。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダーの管理と判定ロジックを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
      - market_calendar データがない場合は曜日ベース（土日非営業）でフォールバックする一貫した振る舞い。
      - DB に登録済み値優先、未登録日は曜日フォールバック。探索は最大 _MAX_SEARCH_DAYS（デフォルト 60 日）で打ち止めして無限ループ防止。
      - calendar_update_job(conn, lookahead_days=90) による J-Quants からの差分取得・保存ロジック（バックフィル、健全性チェック、例外安全）。
      - DuckDB からの date 型変換ユーティリティ _to_date、テーブル存在チェック、NULL 値検出での警告ログなど堅牢性対策。
    - jquants_client を呼び出してフェッチ/セーブを行う設計（外部クライアント抽象化）。

  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult dataclass を追加（target_date・取得/保存件数・quality_issues・errors 等を格納）。
      - has_errors / has_quality_errors / to_dict ユーティリティを提供。
    - pipeline モジュール内に差分更新・保存・品質チェックの設計（jquants_client, quality モジュールとの連携を想定）。
    - kabusys.data.etl では pipeline.ETLResult を再エクスポート。

- 研究用ツール（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離などを計算（DuckDB ウィンドウ関数利用）。
    - calc_volatility(conn, target_date): 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算（NULL 伝播を考慮した true_range 計算）。
    - calc_value(conn, target_date): raw_financials から最新財務を取得して PER/ROE を計算。target_date 以前の最新レコード取得ロジックを実装。
    - 実行は DuckDB のみを参照し、本番発注 API に触れない設計。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一度に取得する高性能 SQL を実装（LEAD を使用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を実装。データ不足時の None 戻し。
    - rank(values): 同順位は平均ランクで処理、丸めで ties の検出漏れを防止。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計概要機能。

Security
- 環境変数の取り扱いについて:
  - 必須トークン類（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings で明示的に要求し、未設定時は例外を発生させる。
  - .env 自動読み込み時に既存 OS 環境変数は protected として上書きから保護。

Changed
- 初回リリースのため変更履歴なし。

Fixed
- 初回リリースのため修正履歴なし。

Removed
- 初回リリースのため削除履歴なし。

Notes / Known limitations
- OpenAI クライアント実装は gpt-4o-mini（JSON mode）を想定。将来のモデル・SDK 変更により動作確認が必要。
- news_nlp と regime_detector はそれぞれ独立して _call_openai_api を持ち、意図的に共有しない（モジュール間結合を避ける設計）。テストではそれぞれ patch が必要。
- DuckDB の executemany に関する互換性配慮（空リスト渡し不可）をコード内で扱っているが、将来の DuckDB バージョン変更で挙動差が出る可能性あり。
- pipeline モジュールの実装は設計方針に沿っているが、外部 jquants_client / quality モジュールの具体実装に依存する。
- calendar_update_job および ETL の外部 API 呼び出しはエラー時に 0 を返すフェイルセーフな実装だが、呼び出し側でログ/通知を適切に扱うことを想定。

Contact
- 問い合わせ・改善提案はリポジトリの issue へお願いします。