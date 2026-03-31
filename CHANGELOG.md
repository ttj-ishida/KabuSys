Keep a Changelog
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点の変更はありません）

0.1.0 - 2026-03-31
-----------------

Added
- 基本パッケージを初回リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの検出基準: .git または pyproject.toml を起点とするため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS 環境変数は protected として上書き防止。
  - 独自の .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープの扱い、コメント処理）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - 必須値チェック (例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID) は未設定時に ValueError を送出。
    - DUCKDB/SQLite のデフォルトパス、KABU_API_BASE_URL のデフォルト値、環境値検証 (KABUSYS_ENV, LOG_LEVEL) を実装。
    - is_live / is_paper / is_dev ユーティリティを提供。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント (ai_scores テーブル) を算出・書き込み。
    - 特長:
      - JST 基準のニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）: calc_news_window を提供。
      - 銘柄ごとに最大記事数・文字数でトリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)。
      - 1 回の API コールで最大 20 銘柄をバッチ処理（チャンク化）。
      - JSON Mode を利用した厳密なレスポンス検証とパース（余分な前後テキストが混入した場合の復元処理を含む）。
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
      - API 失敗やパース失敗時はスキップして継続（フェイルセーフ）。取得済みコードのみを DELETE → INSERT して部分失敗時に既存データを保護。
      - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に設計（_call_openai_api のパッチ）。
      - DuckDB executemany の互換性に配慮（空リスト渡しを避けるチェック）。

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロニュースの LLM センチメント (重み 30%) を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込み。
    - 特長:
      - ma200_ratio の計算は target_date 未満のみを参照し、ルックアヘッドを排除。
      - マクロニュースはマクロキーワードでフィルタして最大件数を取得し、LLM でスコア化（gpt-4o-mini を使用）。
      - LLM 呼び出し失敗時は macro_sentiment=0.0 とするフェイルセーフ。
      - OpenAI API 呼び出しを独立実装（news_nlp とは共有しない）でモジュール結合を低減。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、例外時は ROLLBACK を試行。

- Research モジュール (kabusys.research)
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、ATR 比率（atr_pct）、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から最新財務を取得し PER・ROE を計算（EPS が無効な場合は None）。
    - 設計方針: DuckDB 上の SQL + Python で完結、外部 API を呼ばない、(date, code) キーの dict リストを返す。
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターン (営業日ベース) を一括で取得。
    - calc_ic: スピアマンランク相関（IC）を実装。レコード不足やゼロ分散を考慮して None を返す場合あり。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸めによる ties を考慮）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
    - 外部依存を持たず標準ライブラリのみで実装。

- Data モジュール (kabusys.data)
  - calendar_management.py
    - JPX カレンダー管理と営業日ロジックを実装。
    - 提供関数:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job: J-Quants API からの差分取得・market_calendar への冪等保存（fetch / save を jquants_client に委譲）。
    - 設計上の挙動:
      - market_calendar 未取得時は曜日ベースでフォールバック（土日を非営業日扱い）。
      - DB 登録値が優先され、未登録日は曜日ベースで補完（next/prev/get に一貫性）。
      - 最大探索範囲を _MAX_SEARCH_DAYS で制限（無限ループ防止）。
      - バックフィル、先読み、健全性チェックをサポート。
  - pipeline.py / etl.py
    - ETLResult dataclass を公開（etl.py は pipeline.ETLResult を再エクスポート）。
    - ETLResult に品質チェック結果やエラー概要を含められるよう実装。
    - ETL 実行の内部ユーティリティ（テーブル存在チェック・最大日付取得など）を提供。
    - 設計方針:
      - 差分更新・バックフィル対応、品質チェックは重大度を記録しつつ ETL を継続する設計。

- その他
  - パッケージのトップレベル __all__ に主要サブパッケージを設定（data, strategy, execution, monitoring）。
  - 各所で DuckDB を前提とした実装（DuckDB 接続オブジェクトを引数に取る設計）。
  - 日付参照についてルックアヘッドバイアス防止のため datetime.today()/date.today() を内部処理の基準に多用しない設計（多くの関数は target_date を受け取る）。

Security
- 環境変数の自動ロードにおいて OS 環境を上書きしない保護機構を導入（protected set）。
- 必須の機密情報（OpenAI API キー等）は明示的に要求し、未設定時は例外を送出して安全性を確保。

Testing / Extensibility
- OpenAI 呼び出し箇所は内部関数として抽象化しており、unittest.mock.patch による差し替えでテスト可能。
- DB 書き込みは明示的なトランザクション制御を行い、例外時はロールバックを試みることで一貫性を保護。

Known limitations / Notes
- news_nlp と regime_detector は gpt-4o-mini（JSON mode）を前提に設計されているため、API レスポンス仕様変更があった場合にパースロジックの調整が必要。
- DuckDB のバージョン差異に起因する executemany の挙動（空リスト禁止など）に対して注意喚起をコード内に記載。
- 本リリースでは Strategy / Execution / Monitoring の具体的実装ファイルは付随しない（パッケージエクスポートは __all__ に含めているが将来実装想定）。

Contributors
- 初回実装（コード提供元に準拠）。

---

（この CHANGELOG はソースコード注釈と実装から推測して作成しました。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて更新してください。）