CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。
このプロジェクトではセマンティックバージョニングを採用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-27
--------------------

初期リリース。日本株自動売買システムのコア機能群を提供します。
主な追加点と実装上の注意を以下に示します。

Added
- パッケージ構成
  - kabusys パッケージの公開。__version__ = "0.1.0"。
  - サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ にて公開）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml を探索して決定）。
  - export KEY=val やクォート・エスケープ、インラインコメント処理に対応した独自パーサを実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - protected 機能により OS 環境変数を上書きから保護。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV 判定など）をプロパティ経由で取得可能。
  - env / log_level の値検証（有効な値セットを定義）。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news, news_symbols を読み、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へ送信しセンチメントを算出する score_news(conn, target_date, api_key=None) を実装。
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
  - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）と 1 銘柄あたり記事数・文字数のトリミング実装（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）。
  - JSON mode を利用した堅牢なレスポンス検証（_validate_and_extract）。前後余分テキスト混入時の復元ロジックあり。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ処理（上限回数設定）。
  - DuckDB への書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）。DuckDB の executemany の互換性考慮あり。
  - フェイルセーフ: API 失敗時は該当チャンクをスキップして他チャンクは継続。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime(conn, target_date, api_key=None) を実装。
  - マクロニュースは kquants 内のキーワードでフィルタし（複数キーワード定義）、LLM で macro_sentiment を算出。
  - レジームスコア合成、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - API 呼び出しは独立実装でモジュール結合を避ける。API エラー時は macro_sentiment=0.0 として継続するフェイルセーフ設計。
  - リトライ・バックオフ、JSON パース検証を実装。

- 研究用ファクター & 特徴量探索（kabusys.research）
  - factor_research モジュール
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev を計算（DuckDB SQL ベース）。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio 等を計算（ATR の NULL 伝播制御を含む）。
    - calc_value(conn, target_date): raw_financials と prices を組み合わせて PER / ROE を計算（最新報告日の取得ロジック含む）。
  - feature_exploration モジュール
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（LEAD を利用）を複数ホライズンで計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（ランク関数 rank を内部提供）。
    - factor_summary(records, columns): 各カラムの count/mean/std/min/max/median を計算。
  - データ処理は DuckDB 上で完結。外部 API / 発注処理にはアクセスしない仕様。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - market_calendar 管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - カレンダーデータが不足する場合は曜日ベースのフォールバック（週末判定）を採用。
    - calendar_update_job(conn, lookahead_days) により J-Quants から差分取得し保存（バックフィル・健全性チェック・保存結果を返す）。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl を経由して再エクスポート）。
    - pipeline モジュールにて差分取得・保存・品質チェック（quality モジュールとの連携）を行う設計。最小データ日・バックフィル日数などの定数を定義。
  - jquants_client との連携を想定した抽象化（fetch / save 関数を利用）。

- 設計上の注意点（ドキュメント的な説明をコード内に多数記載）
  - ルックアヘッドバイアス対策: datetime.today()/date.today() を主要処理で直接参照しない設計（target_date パラメータを明示）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 想定）。
  - OpenAI 呼び出しは JSON Mode を使い厳密な JSON 出力を期待、かつ復元ロジックを用意。
  - API 失敗時はフェイルセーフ（スコア = 0.0、チャンクスキップ）で続行し、致命的障害を回避。
  - DuckDB バージョン差異への配慮（executemany の空リスト回避等）。

Security / Ops
- 環境変数の必須チェックを Settings._require で行い、未設定時には ValueError を投げることで起動前に問題を検出。
- .env 読み込みで OS 環境変数を保護する protected 機構を実装。

Dependencies (実行時想定)
- duckdb
- openai (OpenAI SDK)
- jquants_client（プロジェクト内 data.jquants_client を参照する設計。実体は環境に依存）

Breaking Changes
- 初期リリースのため破壊的変更はありません。

Notes / Known limitations
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を発生させる設計。
- ニュースおよびレジーム判定の LLM 呼び出しはコストとレイテンシが発生するため、運用時は呼び出し頻度・バッチサイズの調整が必要。
- 一部の SQL は DuckDB 特有のウィンドウ関数や型の挙動に依存するため、DuckDB のバージョン差分に注意。
- calendar_update_job は jquants_client.fetch_market_calendar / save_market_calendar の挙動に依存する（API エラー時はジョブは 0 を返して失敗扱い）。

作者
- kabusys チーム

----- 

（この CHANGELOG はコードベースのコメント・関数名・実装内容に基づいて推測して作成しています。実際のリリースノートとして利用する場合は、追加の運用情報や既知のバグ・マイグレーション手順を追記してください。）