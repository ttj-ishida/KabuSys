# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
本ファイルはコードベースから推測して作成したもので、実際のリリースノートは適宜調整してください。

## [Unreleased]

## [0.1.0] - 2026-03-28
初期リリース — 日本株自動売買 / データプラットフォーム / 研究用ユーティリティ群の基盤実装。

### Added
- パッケージ基盤
  - kabusys パッケージ初期バージョン（__version__ = 0.1.0）。
  - パッケージ公開 API: data, research, ai, などのモジュールをエクスポート。

- 環境設定 / ロード（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 強固な .env パーサ実装：
    - export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱いなどに対応。
  - .env 読み込み時の上書き制御と保護機能：
    - OS 環境変数は protected として扱われ、上書きから保護。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=true）。
  - Settings クラスを提供し、環境変数の取得とバリデーションを統一的に実施。以下を含むプロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の許容値検証（development / paper_trading / live）
    - LOG_LEVEL の許容値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- ニュース NLP（kabusys.ai.news_nlp）
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini, JSON Mode）で評価し、ai_scores テーブルへ書き込む機能を実装。
  - 主な機能:
    - calc_news_window: JST ベースのニュース集計ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST 相当の UTC 範囲）。
    - score_news: raw_news と news_symbols を集約し、銘柄ごとに記事をまとめてバッチ（最大 20 銘柄）で LLM に投げる。
    - 1 銘柄あたりのトリム制御（記事数 / 文字数上限）を実装し、トークン爆発を抑制。
    - レスポンスのバリデーション（JSON 抽出、results 配列・型チェック、コード照合、数値チェック）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ。
    - 書き込みは冪等性を確保（対象コードのみ DELETE → INSERT）し、部分失敗時に他コードの既存スコアを保持。
    - エラー時は例外を上げずスキップする設計（フェイルセーフ）。空結果時のログ出力。

  - テスト容易性:
    - OpenAI 呼び出し部分は _call_openai_api を通しており、unit test で差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動）の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
  - 主な特徴:
    - _calc_ma200_ratio: DuckDB の prices_daily からルックアヘッドを防ぐ形で計算。データ不足時は中立(1.0)フォールバック。
    - _fetch_macro_news: マクロキーワードでタイトルをフィルタして取得（最大 20 件）。
    - _score_macro: OpenAI により macro_sentiment (-1.0〜1.0) を取得。API エラー時は 0.0 へフォールバック。
    - score_regime: MA と macro_sentiment を重み付け合成しクリップ、ラベル付け、market_regime テーブルへ冪等書き込みを実行。
    - OpenAI 呼び出しはニュース NLP と別実装でモジュール結合を避ける。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None）を DuckDB SQL ベースで計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算（True Range の NULL 伝播制御あり）。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得して PER / ROE を算出。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API に依存しない。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて一括取得。horizons の妥当性検証あり。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足時は None。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めによる ties 対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research パッケージは必要なユーティリティを再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - 市場カレンダー（market_calendar）を扱うユーティリティ群を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job: J-Quants（jquants_client 経由）からの差分取得と保存（バックフィル・健全性チェック付き）。
    - 最大探索範囲（_MAX_SEARCH_DAYS）やバックフィル・先読み等の設定と安全策を実装。
  - pipeline (ETL)
    - ETLResult dataclass を実装（ETL 結果、品質問題、エラー一覧などを保持）。
    - _table_exists / _get_max_date 等のユーティリティを実装し ETL 処理の基礎を提供。
  - etl モジュールは ETLResult を再エクスポート。

### Changed
- （初期リリースのため無し）

### Fixed
- （初期リリースのため無し）

### Security / Behaviour notes
- 設定キーが必須のプロパティ（例: OPENAI_API_KEY を必要とする score_news/score_regime、JQUANTS_REFRESH_TOKEN 等）は未設定時に ValueError を送出して明示的に失敗する設計。
- .env 読み込み時に OS 環境変数を上書きしない（デフォルト）。.env.local は上書き可能だが、既存 OS 環境変数は保護される。
- OpenAI の呼び出しはタイムアウト・リトライ・5xx の扱いが細かく定義され、API エラーで処理全体を停止しないフェイルセーフ設計。

### Testing / Extensibility
- OpenAI 呼び出し部分は内部関数（_call_openai_api）を通すことでユニットテストで差し替え可能（unittest.mock.patch 推奨）。
- DuckDB を想定した SQL 実装で互換性維持（executemany の空リスト制約回避等の対策あり）。

---

注記:
- 本 CHANGELOG はコードベースから推測して作成したもので、実際のコミット履歴・リリースノートとは異なる可能性があります。必要に応じて日付・項目の追加・修正を行ってください。