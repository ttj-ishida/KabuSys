CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。
リリース日付は YYYY-MM-DD 形式で記載しています。

[Unreleased]: https://example.com/kabusys/compare/HEAD...main

0.1.0 - 2026-03-27
------------------

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージのエントリポイントと __version__ = "0.1.0" を追加。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - export KEY=val 形式・クォートやエスケープ、インラインコメント等の .env パーシングロジックを実装（_parse_env_line）。
    - 環境変数の読み取り用 Settings クラスを提供。J-Quants / kabu ステーション / Slack / DB パス / システム環境（env, log_level）などのプロパティを定義。
    - 必須環境変数未設定時は ValueError を発生させる _require を実装。
    - 有効な環境値やログレベルのバリデーションあり。

- AI（ニュースNLP・レジーム検出）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols から記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出する機能を実装。
    - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）算出関数 calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/リクエスト）、各銘柄のトリミング（最大記事数／最大文字数）、JSON Mode での厳密なレスポンス検証を実装。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）と指数バックオフ、フェイルセーフ（API失敗時はスキップして継続、空レスポンスはログ出力）を採用。
    - テスト容易性のため、内部の OpenAI 呼び出しを置き換え可能な実装（_call_openai_api）とした。
    - score_news(conn, target_date, api_key=None) を提供。成功時は書き込んだ銘柄数を返す。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
    - マクロ記事抽出（マクロキーワードリスト）・LLM 呼び出し（gpt-4o-mini）・リトライ・JSON パースの堅牢化を実装。API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - レジームスコアを market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - score_regime(conn, target_date, api_key=None) を提供。API キー未設定時は ValueError を発生。

- Data（ETL・カレンダー）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）管理と営業日ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といったユーティリティを提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業）でフォールバックする一貫した動作を採用。
    - calendar_update_job(conn, lookahead_days=90) で J-Quants API から差分取得→保存（バックフィル処理・健全性チェック含む）する処理を実装。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETL の結果を表す ETLResult データクラスを実装（to_dict により品質問題をシリアライズ可能）。
    - 差分取得・バックフィル・保存（jquants_client の save_* を想定した idempotent 保存）・品質チェック統合のための基礎を提供。
    - 内部での最大データ日付取得やテーブル存在チェックユーティリティを実装。

- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value（PER・ROE）のファクター計算を実装。
    - calc_momentum(conn, target_date): mom_1m / mom_3m / mom_6m / ma200_dev を計算。
    - calc_volatility(conn, target_date): ATR20 / atr_pct / avg_turnover / volume_ratio を計算（真の範囲 true_range は NULL の伝播を明示制御）。
    - calc_value(conn, target_date): 最新の財務情報（raw_financials）と株価を組み合わせて PER / ROE を算出。
    - DuckDB の SQL ウィンドウ関数を多用し、営業日スキャン範囲のバッファやデータ不足時の None 処理を行う。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を一括クエリで計算する汎用実装。
    - calc_ic(factors, forwards, factor_col, return_col): スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - rank(values): 同順位を平均ランクとするランク化ユーティリティ（丸めによる ties 回避）。
    - factor_summary(records, columns): count/mean/std/min/max/median を返す統計サマリー関数。
    - いずれも pandas 等外部依存を使用せずに標準ライブラリ＋DuckDB のみで実装。

- その他
  - src/kabusys/ai/__init__.py と src/kabusys/research/__init__.py で主要 API を再エクスポートして利用を簡単化。
  - 複数モジュールで DuckDB 接続を受け取り SQL と Python を組み合わせる設計。外部（発注）API 等には依存しない安全設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは呼び出し時に引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用する設計。キーが未設定の場合は明示的に ValueError を発生させることで誤動作を防止。

Notes / Design decisions（重要事項）
- ルックアヘッドバイアス回避: AI モジュール・リサーチモジュールのいずれも内部で datetime.today()/date.today() を直接参照せず、呼び出し側が target_date を渡す設計になっています。これによりバックテスト時のルックアヘッドバイアスを回避。
- フェイルセーフ: LLM/API 呼び出しが失敗してもプロセスを中断せず、適切な中立値（0.0 やスキップ）で継続する設計。ログに詳細を出力。
- テスト容易性: OpenAI 呼び出し箇所は内部関数でラップしており、ユニットテスト時にモック差し替えが容易。
- DuckDB 互換性: executemany に空リストを渡すとエラーとなる点等に配慮した実装（空チェックや個別 DELETE を利用）。

今後の予定（未定）
- strategy / execution / monitoring サブパッケージの具体的な売買ロジック・注文管理・監視機能の実装。
- jquants_client の具象実装とそれに対する統合テスト。
- ドキュメント（Usage、データベーススキーマ、運用手順）の拡充。

リリースノートに関する問い合わせや誤りの報告は issue を通じてお願いします。