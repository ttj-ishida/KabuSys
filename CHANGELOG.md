# CHANGELOG

このプロジェクトは Keep a Changelog の形式に従っています。  
重要な変更履歴はこのファイルに記載します。

全般注記:
- 本リリースはコードベースから推測して作成した初期リリースの変更履歴です（バージョンはパッケージの __version__ = "0.1.0" に準拠）。
- 日付は本ファイル作成日（2026-03-31）を使用しています。実運用での正式リリース日がある場合は適宜更新してください。

Unreleased
----------
- （将来の変更はここに記載）

[0.1.0] - 2026-03-31
--------------------
Added
- パッケージの初期機能群を追加（kabusys v0.1.0）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - 読み込みは OS 環境変数 > .env.local > .env の優先順位。
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - Settings クラスを提供し、各種必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）やデフォルト値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, LOG_LEVEL 等）を取得可能。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- AI 関連 (kabusys.ai)
  - ニュースセンチメント：score_news
    - raw_news / news_symbols を集約して銘柄ごとにテキストをまとめ、OpenAI（gpt-4o-mini）の JSON Mode でバッチ解析して ai_scores テーブルへ書き込み。
    - JST のタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して DB クエリで扱う calc_news_window を実装。
    - バッチ処理は最大 20 銘柄/回、記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - API エラー（429・ネットワーク断・タイムアウト・5xx）に対する指数バックオフリトライ。致命的でない失敗はスキップし処理継続（フェイルセーフ設計）。
    - レスポンスの厳密なバリデーションとスコア ±1.0 のクリッピングを実装。
    - テスト用に _call_openai_api をパッチ差替え可能（unittest.mock.patch に対応）。

  - 市場レジーム判定：score_regime
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI で -1.0〜1.0 の JSON スコアを取得。API 失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - 計算結果を market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。

- データプラットフォーム (kabusys.data)
  - ETL ユーティリティ:
    - pipeline.ETLResult を公開（ETL の集計結果・品質問題・エラーを保持）。
    - 差分取得／バックフィル／品質チェック等を想定した設計（jquants_client, quality モジュールと連携）。
  - カレンダー管理:
    - JPX カレンダー同期バッチ（calendar_update_job）を追加。J-Quants から差分取得し market_calendar を冪等に保存。
    - 営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが無い場合は曜日ベースでフォールバック（週末を非営業日扱い）。
    - 最大探索日数・バックフィル日数・健全性チェック等の防護ロジックを実装。

- リサーチ（kabusys.research）
  - ファクター計算:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）を prices_daily から計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER, ROE を算出（最新報告日ベース）。
  - 特徴量探索:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank, factor_summary: ランク化と基本統計量集計ユーティリティを提供。
  - 設計方針:
    - DuckDB 接続を受け取り SQL と標準ライブラリで完結。取引 API にはアクセスしない（安全）。

- データユーティリティ:
  - calendar_management, pipeline, etl 等で DuckDB に対する各種互換性・耐性（空の executemany 回避、日付変換ユーティリティ等）を実装。
  - DB 書き込みはできる限り冪等化（DELETE→INSERT または ON CONFLICT 相当）を意識。

Changed
- 新規リリース（初版）につき該当なし。

Fixed
- 新規リリース（初版）につき該当なし。

Security
- OpenAI API キーは明示的に引数で注入可能。環境変数 OPENAI_API_KEY を使う場合は Settings ではなく各関数の api_key 引数でも上書き可能な設計。  
- .env 自動ロード時に OS の既存環境変数はデフォルトで保護（上書きされない）。.env.local は override=True で後から読み込んで上書き可能だが、OS 環境変数は保護される。

Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須（未設定時は ValueError を送出）。
  - OpenAI 呼び出しを行う score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必要とします。
- デフォルトファイルパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PID_FILE_PATH: data/execution.pid
- DB スキーマ期待値（本リポジトリではスキーマ定義ファイルは含まれていません。実運用時は以下のテーブルが存在することを前提）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
- テストのしやすさ:
  - OpenAI 呼び出しの内部ラッパー関数（news_nlp._call_openai_api, regime_detector._call_openai_api）を unittest.mock.patch などで差し替えてテスト可能。
- ルックアヘッド対策:
  - 各モジュール（score_news, score_regime, ファクター計算等）は内部で datetime.today()/date.today() を直接参照せず、target_date 引数を基準に処理することでルックアヘッドバイアスを防止する設計になっています。
- 互換性:
  - DuckDB のバージョンや executemany の挙動差異に配慮した実装（空リストの executemany を回避するチェック）を行っています。

既知の制約・今後の改善候補
- ai モデルは gpt-4o-mini の JSON Mode を想定。API のバージョンやモデル変更に伴うレスポンス仕様差異に注意。
- raw_financials からの PBR・配当利回り等は未実装（将来的な拡張候補）。
- calendar_update_job / pipeline の外部依存（jquants_client, quality モジュール）は実装に依存するため、接続先 API の安定性が動作に影響します。

著記
- 本 CHANGELOG はリポジトリのソースコードから推測して作成しています。実際のリリースノート作成時はコミットログ・リリースチケット等に基づいて調整してください。