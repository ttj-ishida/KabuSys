Changelog
=========
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース。kabusys を構成する主要モジュールを追加。
  - パッケージ公開情報:
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0"、公開サブモジュールの __all__ を定義（data, strategy, execution, monitoring）。
- 環境変数・設定管理:
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
    - .env パーサーの実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
    - 読み込み順序: OS 環境 > .env.local > .env（.env.local は上書き可能）。
    - Settings クラスを提供し、必須設定値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を取得・検証する API を公開。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス指定、KABUSYS_ENV と LOG_LEVEL の許容値検証、is_live/is_paper/is_dev のヘルパーを追加。
- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄毎にニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（デフォルト _BATCH_SIZE=20）、1銘柄あたりの記事上限（_MAX_ARTICLES_PER_STOCK=10）と文字上限（_MAX_CHARS_PER_STOCK=3000）を実装。
    - API 呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフでのリトライ、その他エラー時は安全にスキップするフェイルセーフ実装。
    - レスポンス検証ロジック: JSON 抽出、"results" 配列の検証、コード照合、スコア数値性チェック、スコア ±1 にクリップ。
    - DuckDB へは部分置換（DELETE→INSERT）で書き込み、部分失敗時に既存スコアを保護する挙動を採用。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込み。
    - マクロキーワードによる raw_news フィルタ、OpenAI（gpt-4o-mini）を用いたマクロセンチメント算出、API リトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）等を実装。
    - ルックアヘッドバイアス防止の設計方針（datetime.today() を参照しない、prices_daily の date < target_date 条件等）。
    - モジュール内で独立した _call_openai_api を用意し、テスト時に差し替え可能。
- データプラットフォーム（DuckDB ベース ETL / カレンダー管理）:
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass を実装して ETL の取得数・保存数・品質問題・エラーを集約・報告可能にした。
    - 差分取得、バックフィル、品質チェックの方針をコードに反映（デフォルト backfill 日数・カレンダー先読み等）。
    - DuckDB 上での最大日付取得ユーティリティやテーブル存在チェック等を実装。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を外部公開するインターフェースを追加。
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar テーブル）を管理するユーティリティを実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
      - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
      - calendar_update_job: J-Quants API（jquants_client）から差分取得して market_calendar を冪等的に更新。バックフィル（直近 _BACKFILL_DAYS の再フェッチ）、健全性チェック（将来日付の異常検出）を実装。
- リサーチ（ファクター計算・特徴量探索）:
  - src/kabusys/research/factor_research.py
    - Momentum, Volatility, Value 等の定量ファクター計算を追加:
      - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日移動平均乖離率）等を計算。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS=0 の場合は None）。
    - DuckDB のウィンドウ関数や LAG/AVG を用いた実装で、データ不足時は None を返し安全に処理。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得する汎用実装。
    - calc_ic: Spearman（ランク）相関による IC 計算。欠損/定数分布の取り扱い、最小サンプル数チェック（>=3）を実装。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）を標準ライブラリで実装。
- テスト性・堅牢性に関する設計:
  - 各種 OpenAI 呼び出し点で個別の _call_openai_api を用意しており unittest.mock.patch による差し替えが可能。
  - 多くの箇所で「ルックアヘッドバイアス防止」を明確化（日時参照は引数で行い、date.today() を直接参照しない）。
  - API エラー時のフォールバック（0.0 やスキップ）や再試行（指数バックオフ）を幅広く実装。
  - DuckDB に対する executemany の空リスト問題回避（空パラメータ時には呼ばない分岐）や冪等性（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）の配慮。

Changed
- 新規リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Design decisions
- OpenAI モデルには gpt-4o-mini を採用し、JSON Mode（response_format）を使用。レスポンスのパース失敗に備えて JSON 抽出ロジックを用意。
- DuckDB をデータプラットフォームのストレージとして想定。SQL と Python を組み合わせて高速に処理。
- 外部サービス（J-Quants / OpenAI / kabuステーション / Slack 等）との連携ポイントを設定値経由で注入する設計。
- strategy / execution / monitoring はパッケージ公開対象として __all__ に含まれるが、本差分では主要な data / ai / research モジュールの実装に注力。

今後の予定（例）
- strategy / execution / monitoring の具象実装とエンドツーエンドの自動売買フロー実装。
- ユニットテスト・統合テストの追加（特に OpenAI / J-Quants クライアントのモックを用いたテスト）。
- ドキュメント（Usage / Deployment / DataPlatform / StrategyModel）の充実。

-----------------------------------------------------------------------------
（注）この CHANGELOG は提供されたソースコードから機能・設計方針を抽出して推定作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴や公開リリースノートに基づいて更新してください。