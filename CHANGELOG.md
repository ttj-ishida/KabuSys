CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
セマンティック バージョニングを採用しています。  

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初版リリース (version 0.1.0)。
  - パッケージルート: kabusys
  - 公開モジュール: data, research, ai, config, など（src/kabusys/__init__.py に __all__ 指定）

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は既存キーを上書き）。
  - .env フォーマットの堅牢なパーサ:
    - export VAR=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い、無効行（空行、#始まり）をスキップ。
  - protected オプションにより OS 環境変数の上書きを防止。
  - Settings クラスで主要設定をプロパティ化:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト local）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL の検証
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を用いたニュース -> 銘柄別センチメント生成機能。
  - score_news(conn, target_date, api_key=None) を提供:
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - 銘柄ごとに最新 n 件（デフォルト 10 件）を集約し、テキスト長でトリム（デフォルト 3000 文字）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）で OpenAI（gpt-4o-mini）の JSON mode を利用。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、"results" リスト、code の確認、数値検証）。
    - スコアは ±1.0 にクリップ。部分成功時は対象コードのみ DELETE → INSERT（冪等性・部分障害保護）。
    - API キー未設定時は ValueError を送出。
    - テスト用に OpenAI 呼び出しを差し替え可能（内部 _call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None) を提供:
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - ma200_ratio の計算は target_date 未満のデータのみを利用し、ルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp.calc_news_window で算出されるウィンドウから抽出し、最大 20 記事まで LLM で評価。
    - OpenAI 呼び出しは gpt-4o-mini、JSON mode を使用。API エラー時は macro_sentiment = 0.0 としてフォールバック（フェイルセーフ）。
    - 冪等的に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK。
    - threshold による regime_label 決定（BULL / BEAR の閾値指定あり）。

- 研究用ファクター計算 (kabusys.research)
  - calc_momentum(conn, target_date):
    - 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を銘柄毎に計算。データ不足時は None。
  - calc_volatility(conn, target_date):
    - 20 日 ATR、ATR 比率（atr_pct）、20 日平均売買代金、出来高比率を計算。トゥルーレンジの NULL 伝播を適切に処理。
  - calc_value(conn, target_date):
    - raw_financials から target_date 以前の最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を利用）を複数ホライズンで計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算（有効レコード < 3 は None）。
    - rank(values): 同順位は平均ランクで扱う実装（丸めによる ties の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。

- データプラットフォーム関連 (kabusys.data)
  - calendar_management:
    - JPX カレンダーを扱うユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
      - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバック（土日非営業日）。
      - 最大探索日数 (_MAX_SEARCH_DAYS=60)、カレンダー先読み・バックフィル、健全性チェックを実装。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を冪等保存。エラーハンドリングとログ出力。
  - ETL パイプライン:
    - ETLResult dataclass を公開（kabusys.data.etl から再エクスポート）。
    - pipeline モジュール: 差分取得、保存（jquants_client の save_* を利用）および品質チェック（quality モジュール）を想定するユーティリティ群（ETLResult に品質・エラーを集約）。
    - 内部ユーティリティとして DuckDB テーブル存在チェック、最大日付取得処理を提供。

Security / Hardening / Design
- ルックアヘッドバイアス防止:
  - AI モジュールおよびファクター計算は datetime.today()/date.today() を内部で参照せず、呼び出し側から target_date を受け取る設計。
  - DB クエリでは date < target_date / date = target_date 等の排他条件を明示。
- フェイルセーフ動作:
  - OpenAI API 呼び出し失敗時にプロセス全体を停止させない（news_nlp: チャンク失敗はスキップ、regime_detector: macro_sentiment=0.0）。
- テスト容易性:
  - OpenAI 呼び出しを行う内部関数はテストで patch できるよう設計されている（例: kabusys.ai.news_nlp._call_openai_api の差し替え）。
- DuckDB 前提:
  - 多くの処理は DuckDB 接続を受け取り SQL を用いて完結する（外部 API コールを行わない関数も多い）。
  - DuckDB バージョン差異に対する互換性考慮（executemany の空リスト注意など）。

Known limitations / Notes
- jquants_client モジュールは参照されているが、本変更セット内に実装ファイルは含まれていない（別パッケージまたは別ファイルで提供される想定）。
- 一部のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提となるため、ETL 実行前に DB スキーマ準備が必要。
- OpenAI モデルは gpt-4o-mini を想定。利用には OPENAI_API_KEY（関数呼び出し引数でも指定可）が必要。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

（以上）