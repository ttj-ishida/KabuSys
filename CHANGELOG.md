CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

目次
-----
- [0.1.0] - 2026-03-27

[0.1.0] - 2026-03-27
--------------------

初期リリース。日本株自動売買システムのコアライブラリを公開します。以下はコードベースから推測して記載した主な追加機能・設計上の注意点です。

Added
- パッケージ基礎
  - kabusys パッケージの初期バージョンを追加（__version__ = "0.1.0"）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に一部記載）。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env パーサーは export KEY=val 形式、シングル/ダブルクオート、バックスラッシュエスケープ、行内コメント（'#'）の処理に対応。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require() と Settings クラスを提供。
  - Settings が公開する主要設定項目:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV 値検証（development / paper_trading / live）
    - LOG_LEVEL 値検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を用いた銘柄別センチメント集計と ai_scores テーブルへの書き込み機能。
    - OpenAI（gpt-4o-mini）を用いた JSON Mode により銘柄毎に -1.0〜1.0 のスコアを生成。
    - バッチ処理（最大20銘柄/チャンク）、記事トリム（最大記事数・最大文字数）によりトークン膨張を回避。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフを実装。API失敗時には該当チャンクをスキップ（フェイルセーフ）。
    - レスポンスの厳格バリデーション（JSONパース、results 配列、code/score の検証、スコアクリップ）。
    - calc_news_window(target_date) による JST ベースの集計ウィンドウ計算（前日15:00〜当日08:30 JST 相当）。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（unittest.mock.patch でモック可能）。

  - regime_detector: 市場レジーム判定（'bull' / 'neutral' / 'bear'）。
    - ETF 1321（Nikkei225 連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成。
    - マクロキーワードによる raw_news の抽出、LLM による macro_sentiment 評価（gpt-4o-mini）。
    - レジームスコア合成と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API失敗時は macro_sentiment=0.0 にフォールバックし処理継続（フェイルセーフ）。
    - OpenAI クライアントは環境変数 OPENAI_API_KEY または api_key 引数から解決。未設定時は ValueError。

- Research モジュール (kabusys.research)
  - factor_research: ファクター計算機能を提供。
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200日MA乖離率）。
    - Volatility / Liquidity: 20日 ATR, ATR比率, 20日平均売買代金, 出来高比率。
    - Value: PER（EPS が無効な場合は None）と ROE（raw_financials から取得）。
    - DuckDB を用いた SQL ベース実装。結果は (date, code) をキーとする dict のリストを返す。
  - feature_exploration:
    - calc_forward_returns: 将来リターンの計算（デフォルト horizons=[1,5,21]）。
    - calc_ic: スピアマンランク相関（IC）計算。
    - factor_summary: ファクターの基本統計量計算（count/mean/std/min/max/median）。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats から）等を再エクスポート。

- Data モジュール (kabusys.data)
  - calendar_management: JPX カレンダーの管理・判定ロジック。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未設定時は曜日ベースのフォールバック（土日非営業日）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルや健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラス（ETL 実行結果の集約）を提供（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - pipeline モジュールは差分更新、品質チェック（quality モジュール連携）、backfill の取り扱いを想定した設計。

- テスト・運用上の配慮
  - datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。すべての処理は target_date を引数で受ける。
  - OpenAI 呼び出し関数はモジュールごとに分離され、テスト時に差し替え可能。
  - DuckDB への executemany に関する互換性（空リスト回避）へ配慮した実装。

Fixed
- （初版のため該当なし）

Changed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数の扱いについて:
  - OS 環境変数は .env によって上書きされないよう protected セットで保護。
  - 自動読み込みを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - OpenAI API キー・各種トークンは必須項目（Settings のプロパティで未設定時に例外）。

Compatibility / Requirements
- DuckDB に格納されるテーブル（暗黙の前提）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など。
- OpenAI SDK（コード中では OpenAI クライアントを使用）への依存。
- Python 型注釈を多用（>=3.10 以降を想定）。
- ローカルデフォルト DB パス: data/kabusys.duckdb, data/monitoring.db（必要であれば環境変数で上書き可能）。

Migration notes
- 初回導入時:
  - 必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を .env/.env.local に設定するか OS 環境変数で設定してください。
  - 自動 .env 読み込みはプロジェクトルートの判定に .git または pyproject.toml を使用するため、配布パッケージ化後に挙動を変えたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化してください。
  - DuckDB のテーブルスキーマは各モジュールが期待するカラムを持つこと（prices_daily の date/close/high/low/volume/turnover 等、raw_news の id/title/content/datetime 等）。

Notes / Implementation remarks
- AI モジュールはレスポンスパース失敗や API エラー時にスコアを 0.0 または該当チャンクスキップとして安全に継続する（フェイルセーフ設計）。
- 各ETL/カレンダー更新処理は冪等（既存レコードの置換）を意識した実装となっています。
- リサーチ関連関数は外部 API に依存しないため、オフラインでのバックテストや解析に利用可能。

今後の予定（想定）
- ai/models やニュースフィードの拡張、追加品質チェックの強化。
- 監視・実行（execution, monitoring）サブパッケージの具体的実装。
- ドキュメント（Usage / API / DB スキーマ）の追補。

以上。追加で特定ファイルや関数の変更履歴（コミット単位）を反映したい場合は、コミットログやリリースノート元データを提供してください。