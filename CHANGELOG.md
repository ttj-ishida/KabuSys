CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
※日付はリリース日（本コードベースの初回バージョンとして想定）です。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

Added
- パッケージ基本情報
  - パッケージ名: kabusys、バージョン 0.1.0 を導入。
  - パッケージの公開モジュール群を __all__ で定義。

- 環境設定（kabusys.config）
  - .env/.env.local ファイル自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export KEY=val 形式やクォート・コメントのパースに対応した .env パーサを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / システム設定を環境変数から取得。
  - 必須環境変数未設定時に ValueError を投げる _require を実装。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
  - duckdb/sqlite パスのデフォルトや Path に展開する挙動を実装。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini の JSON Mode）でセンチメントを算出して ai_scores に書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を実装。
  - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの最大記事数/文字数制限、JSON レスポンスのバリデーションとスコアの ±1.0 クリップ実装。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
  - OpenAI 呼び出しのテスト差し替え用フック（_call_openai_api）とレスポンスの復元処理（前後余計なテキストが混ざる場合の {} 抽出）を実装。
  - DuckDB の executemany の互換性を考慮し、空リストの扱い回避を実装（部分失敗時に既存スコアを保護するため、DELETE → INSERT の置換戦略）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - マクロキーワードによる記事抽出、OpenAI 呼び出し（独立実装）、フェイルセーフ（API 失敗時は macro_sentiment=0.0）およびリトライ/バックオフを実装。
  - DB（market_regime）への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを参照する設計を採用。

- 研究用ファクター群（kabusys.research）
  - ファクター計算モジュール（factor_research）を追加：
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の計算。
    - calc_value: raw_financials を用いた PER / ROE の計算。
    - 設計上、prices_daily / raw_financials のみ参照し、本番発注など外部 API へはアクセスしないことを明示。
  - 特徴量探索モジュール（feature_exploration）を追加：
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）の将来リターン計算。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を出力。
    - rank: 同順位は平均ランクで扱うランク変換ユーティリティ。
  - 研究ユーティリティは外部ライブラリに依存せず、DuckDB + 標準ライブラリで完結する設計。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（pipeline）を実装：
    - 差分更新ロジック、バックフィル、品質チェック統合を想定した ETLResult dataclass を提供。
    - DuckDB のテーブル存在チェック、最大日付取得などのユーティリティを実装。
  - カレンダー管理（calendar_management）を実装：
    - JPX カレンダー（market_calendar）の夜間差分取得ジョブ calendar_update_job を実装（J-Quants client 経由で取得→保存）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - market_calendar 未取得時の曜日ベースフォールバック（週末を非営業日）や、DB 登録値優先の一貫した挙動を実装。
    - 健全性チェック、バックフィル期間、最大探索日数のガードを実装。

- OpenAI 関連
  - gpt-4o-mini を使った JSON mode 呼び出しの実装（news_nlp と regime_detector が独立した _call_openai_api を持つ）。
  - レスポンスパースやリトライの共通設計を採用し、API 側の不安定さに耐性を持たせた実装。

- ロギング / エラー処理
  - 各モジュールで詳細な info/warning/exception ログを追加し、処理状況やフェイルオーバーを明示。
  - DB 書き込み失敗時は ROLLBACK を試み、ROLLBACK 自体の失敗も警告ログに記録。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- N/A（初回リリース）

Notes / 実装上の留意点
- ルックアヘッドバイアス対策として、いずれのスコア計算でも datetime.today() / date.today() を内部参照せず、明示的な target_date を受け取る設計になっています。
- DuckDB のバージョン互換性（executemany に空リストを渡せない等）を考慮した実装がいくつかに含まれます（ai_scores 書込など）。
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で供給します。未設定時は ValueError を送出します。
- news_nlp / regime_detector ともに LLM レスポンスの失敗は全体処理を止めない（フェイルセーフで 0 相当やスキップ）設計です。ただし DB 書き込み部分での例外は上位へ伝播します。

Contributors
- 初回コードベース（設計・実装）: 実装者（コードから推測）

ライセンス／パッケージ配布に関する情報はソースに含まれていないため、本 CHANGELOG では記載していません。必要であれば別途 LICENSE 等の情報を追加してください。