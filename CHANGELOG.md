CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-29
--------------------

初回リリース。日本株の自動売買およびリサーチ用ユーティリティ群を提供します。主な追加点と設計上の重要な振る舞いを以下にまとめます。

Added
- パッケージ基盤
  - kabusys パッケージの初期実装。__version__ = "0.1.0"。
  - 公開サブパッケージ (data, research, ai, monitoring, strategy, execution を想定) を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ の親階層から探索
  - .env パーサ実装（export 付き行・クォート内のバックスラッシュエスケープ・インラインコメント処理に対応）
  - 環境変数必須チェックを行う _require() と Settings クラスを提供。
    - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH (デフォルト data/kabusys.duckdb), SQLITE_PATH (デフォルト data/monitoring.db)
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーションを実装
    - is_live / is_paper / is_dev のヘルパープロパティ

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄別センチメント（ai_scores）を生成する score_news(conn, target_date, api_key=None) を提供。
    - 時間ウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（UTC に変換してクエリ）。
    - バッチ処理: 最大 20 銘柄/コールで OpenAI (gpt-4o-mini) に JSON モードで問い合わせ。
    - 再試行ロジック: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフと最大リトライ回数。
    - レスポンス検証: JSON 抽出/検証（results 配列、code と score の存在）、スコアを ±1.0 にクリップ。
    - DB 書き込みは「該当コードのみ」DELETE→INSERT で置換し、部分失敗時の既存データ保護を行う。
    - テスト用に _call_openai_api の差し替えが可能。
    - calc_news_window(target_date) ユーティリティを公開（UTC naive datetime を返す）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime(conn, target_date, api_key=None) を提供。
    - マクロニュース抽出は news_nlp.calc_news_window を利用。
    - OpenAI 呼び出し部分は独立した内部実装で、テスト時は差し替え可能。
    - フェイルセーフ: API 失敗やパース失敗時は macro_sentiment=0.0 を採用して処理を継続。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。

- Research モジュール (kabusys.research)
  - factor_research モジュール
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value(conn, target_date): raw_financials から EPS/ROE を参照し PER/ROE を計算。
    - 計算は DuckDB 上の prices_daily / raw_financials を参照し、外部 API に依存しない設計。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=None): 複数ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）計算。
    - rank(values): 平均ランク処理（同順位は平均ランク）を実装。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理、営業日判定および next/prev/get_trading_days/is_sq_day 等のユーティリティを実装。
    - DB に market_calendar が存在する場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を冪等更新するジョブ（バックフィル・健全性チェックあり）。
  - pipeline (ETL)
    - ETLResult データクラスと ETL ユーティリティ（差分取得・保存・品質チェックフロー）を実装。
    - _get_max_date 等の内部ユーティリティを提供。
    - デフォルトの backfill_days と calendar lookahead を設定し、品質チェックの収集方針（Fail-Fast ではなく全件収集）を明記。
  - etl を再エクスポートするインターフェース（kabusys.data.etl で ETLResult を公開）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数に API キーを依存（OPENAI_API_KEY 等）。必須キー未設定時は ValueError を raise して明示的に失敗する設計。

Notes / 設計上の重要な点
- ルックアヘッドバイアス回避
  - 多くの処理が datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る）。
  - DB クエリは target_date 未満や排他条件を用いるなどルックアヘッドを回避。

- フェイルセーフと冪等性
  - LLM/API 失敗時は例外を投げずスコアをスキップまたは中立値（0.0）にフォールバックして継続する箇所がある（運用で安全に動く設計）。
  - DB 書き込みは可能な限り冪等に実装（DELETE→INSERT、ON CONFLICT など）し、部分失敗時の既存データ保護を意識。

- DuckDB 互換性注意
  - executemany に空リストを投げない等、DuckDB のバージョン差異に対するワークアラウンドあり（特に DuckDB 0.10 系）。

- テスト性
  - OpenAI 呼び出し（_call_openai_api）や一部内部関数は unittest.mock.patch で差し替え可能にしている。

Known issues
- 初期バージョンのため実運用でのエッジケース検証は限定的。大規模データや長期運用時の性能チューニング、エラーハンドリングの追加強化が想定される。

Migration
- 初回リリースのためマイグレーション指示はなし。

作者注
- 各モジュールには詳細な docstring と処理フロー・設計方針が含まれています。運用開始前に環境変数（特に OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）の設定と DuckDB のスキーマ整備を行ってください。