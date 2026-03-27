# CHANGELOG

すべての変更は「Keep a Changelog」のフォーマットに従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買システムのコアライブラリを提供します。主な内容は環境設定管理、データETL／カレンダー管理、研究用ファクター計算、ニュース NLU・市場レジーム判定、ならびにそれらを支えるユーティリティ群です。

### Added
- パッケージ初期化
  - kabusys パッケージの __init__.py を追加。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョンを "0.1.0" に設定。

- 環境変数・設定管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）。
  - protected 引数による OS 環境変数上書き防止ロジックを実装。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB/SQLite） 等の設定を取得。
    - KABUSYS_ENV のバリデーション（development/paper_trading/live）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev ヘルパーを提供。
  - 必須環境変数未設定時に ValueError を発生させる _require ヘルパーを実装。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）を実装:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（デフォルト _BATCH_SIZE=20）、記事数・文字数トリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - JSON Mode 応答の検証・復元ロジック（前後ノイズが混在する場合の {} 抽出）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx を対象に指数バックオフ、最大リトライ数 _MAX_RETRIES）。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。
    - calc_news_window(target_date) を実装（JST 基準: 前日15:00 ～ 当日08:30、UTC 変換済み）。
    - テスト容易性のため internal の _call_openai_api を patch 可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）を実装:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重量 70%）と、マクロニュースの LLM センチメント（重量 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロキーワード（デフォルトリスト）による raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
    - 合成スコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値によりラベル付け（_BULL_THRESHOLD/_BEAR_THRESHOLD）。
    - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。
    - API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - テスト容易性のためこのモジュール内の _call_openai_api は news_nlp の実装と分離（結合回避）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）管理ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB に情報が無い場合の曜日ベースフォールバック（週末は非営業日）。
    - calendar_update_job を実装: J-Quants API（jquants_client 経由）から差分取得し market_calendar を冪等保存。バックフィル・健全性チェック実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（各種取得数・保存数・品質問題・エラーの集約）。
    - ETL の内部ユーティリティ（テーブル存在確認、最大日付取得、trading day 調整など）を実装。
    - kabusys.data.etl モジュールで ETLResult を再公開。
  - jquants_client と quality との連携ポイントを用意（実際のクライアント実装は別モジュール想定）。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily, raw_financials テーブルを参照）。
    - Momentum: 1M/3M/6M リターン（営業日ベース）、200日移動平均乖離（ma200_dev）。
    - Volatility: 20日 ATR, ATR 比率, 20日平均売買代金, 出来高比率。
    - Value: PER（株価/EPS）と ROE（raw_financials から最新報告を取得）。
    - 入力データ不足時には None を返す仕様。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（デフォルト horizons=[1,5,21]）を一括クエリで算出。horizons のバリデーションあり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。レコード数不足時は None。
    - rank: 同順位は平均ランクで扱うランク変換実装（丸めにより ties 検出漏れ対策）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - kabusys.research.__init__ で主要関数をまとめて公開（zscore_normalize は kabusys.data.stats から利用）。

### Changed
- （初回リリースにつき過去変更なし）

### Fixed
- （初回リリースにつき過去修正なし）

### Security
- 環境変数の自動読み込みにおいて、既存 OS 環境変数が上書きされないよう protected セットを導入。

### Notes / Implementation details / 注意点
- 時間帯／ルックアヘッドバイアス防止:
  - news と regime 判定は target_date を引数に取り、内部で datetime.today()/date.today() に依存しない設計。
  - prices_daily クエリは target_date 未満のみを参照する等、将来情報の混入を避ける実装に配慮。
- OpenAI（gpt-4o-mini）利用:
  - API キーが与えられない場合（引数または環境変数 OPENAI_API_KEY）には ValueError を送出する（明示的なエラーハンドリング）。
  - API 呼び出しはリトライ／バックオフされるが、全リトライ失敗時は該当処理を中立（0.0）やスキップして継続するフェイルセーフを採用。
- DuckDB に対する互換性注意:
  - executemany に空リストが渡せないケース（DuckDB 0.10）に配慮したガードを実装。
  - SQL 文字列内の table/column 組み立ては基本的に定数・パラメータバインドを利用。
- テスト容易性:
  - OpenAI 呼び出し箇所（各モジュール内の _call_openai_api）を unittest.mock.patch で差し替え可能にしている。
- 未実装/制約:
  - strategy / execution / monitoring モジュールの具体的実装は本リリースでは公開APIでエクスポートされているが、詳細実装は別途（今後のリリースで追加想定）。
  - 一部の財務指標（PBR・配当利回りなど）は現バージョンでは未実装。

---

もしリリースノートの形式や日本語表現の調整（より詳細な変更ログ、セクションの分割、既知のバグリスト追加など）をご希望でしたら指示をください。