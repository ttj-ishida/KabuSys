CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のフォーマットに従って記載しています。

[0.1.0] - 2026-03-28
-------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムのコアライブラリを追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パッケージトップでは __all__ = ["data", "strategy", "execution", "monitoring"] を公開。

- 環境設定 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.gitまたはpyproject.tomlで判定）から自動読み込みする機能を実装。
  - 読み込みの優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト用途）。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント考慮などをサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベースパス 等の設定プロパティを公開。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）と便利な is_live / is_paper / is_dev プロパティ。

- ニュースNLP (kabusys.ai.news_nlp)
  - raw_news と news_symbols を用いて銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）を用いてセンチメントを算出する score_news を実装。
  - 適用タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を厳密に計算する calc_news_window を提供。
  - バッチ処理（1 API 呼び出しで最大 _BATCH_SIZE=20 銘柄）・1銘柄あたり記事上限/文字数トリム・JSON Mode を利用した厳密なレスポンス検証。
  - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、API失敗時はフェイルセーフでスキップ（例外は上位に伝搬しない）。
  - レスポンス検証ロジック (_validate_and_extract) により unknown code の無視、スコアの ±1 クリップ等を実装。
  - DuckDB への冪等書き込み（DELETE→INSERT）で部分失敗時の既存データ保護。空パラメータでの executemany に注意（DuckDB 互換性対応）。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321（日経225連動型）の直近200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - prices_daily / raw_news / market_regime テーブルを参照し、レジームを算出して market_regime テーブルへ冪等的に書き込む。
  - LLM 呼び出しは専用実装（news_nlp とプライベート関数を共有しない）で、API リトライ/フォールバック（API失敗時 macro_sentiment=0.0）を備える。
  - ルックアヘッドバイアス対策: date 比較は target_date 未満/前日ウィンドウ等で厳密に制御。

- 研究系機能 (kabusys.research)
  - factor_research: モメンタム（1M/3M/6M）、200日MA乖離、ATR20、20日平均売買代金・出来高変化率、PER/ROE（raw_financials から）などのファクター計算関数を追加:
    - calc_momentum(conn, target_date)
    - calc_volatility(conn, target_date)
    - calc_value(conn, target_date)
  - feature_exploration: 将来リターン・IC（Spearman）、rank ユーティリティ、統計サマリーを実装:
    - calc_forward_returns(conn, target_date, horizons=None)
    - calc_ic(factor_records, forward_records, factor_col, return_col)
    - rank(values)
    - factor_summary(records, columns)
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats から）や主要関数を再エクスポート。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management: market_calendar を用いた営業日判定/次営業日/前営業日/期間営業日取得/is_sq_day 判定などのロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
    - calendar_update_job: J-Quants からカレンダーを差分取得して市場カレンダーを upsert（バックフィル・健全性チェックあり）。
    - DB にデータが無い場合の曜日ベースフォールバック、最大探索日数制限で無限ループ回避。
  - pipeline: ETL の高レベル実装に用いる ETLResult データクラスを実装（取得/保存件数、品質チェック結果、エラー一覧等を含む）。
  - etl: pipeline.ETLResult を再エクスポート。

- DuckDB を主要なデータストアとして採用し、SQL と Python を組み合わせた計算を行う設計を採用（prices_daily / raw_news / raw_financials / market_calendar / ai_scores / market_regime 等を想定）。

- ロギングと堅牢性
  - 各モジュールで logging を活用し、警告/例外時の情報を出力。
  - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT（失敗時は ROLLBACK）で冪等性・整合性を確保。
  - ルックアヘッドバイアス対策を設計方針として明示的に取り入れ（datetime.today()/date.today() を参照しない箇所の実装方針）。

Changed
- 初版リリースのためなし（新規追加が中心）。

Fixed
- 初版リリースのためなし。

Security
- 初版リリースのためなし。

Notes / Implementation details
- OpenAI API（gpt-4o-mini）を Chat Completions JSON Mode で利用する箇所があるため、環境変数 OPENAI_API_KEY の設定が必須（各関数で未設定時は ValueError を送出）。
- .env パーサは比較的堅牢に実装しているが、極端なフォーマットの .env では予期しない挙動になる可能性あり。
- DuckDB バージョン差分による executemany 空リスト不可等の互換性問題をコード内で配慮している（空パラメータのチェック）。

今後の予定（例）
- strategy / execution / monitoring パッケージの具象実装（現状トップレベルでエクスポート予定）。
- より詳細な品質チェックモジュール (kabusys.data.quality) の拡張。
- 追加のファクターやバックテストユーティリティの実装。