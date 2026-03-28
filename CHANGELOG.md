# Changelog

すべての注目すべき変更点を記録します。This project adheres to "Keep a Changelog" のフォーマットおよびセマンティック バージョニング (https://keepachangelog.com/ja/1.0.0/)。

## [Unreleased]
（現時点のリリース履歴は以下の初回リリースにまとめられています）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムの基盤となるモジュール群を実装しました。主な機能はデータ取得／ETL、マーケットカレンダー管理、ファクター計算・特徴量探索、ニュース NLP を用いた銘柄センチメント評価、マーケットレジーム判定、設定・環境変数管理などです。

### Added
- パッケージメタ
  - kabusys パッケージ初版（__version__ = 0.1.0）。
  - パッケージ公開用 __all__ に data, strategy, execution, monitoring を定義。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルの自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env / .env.local の読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装: コメント、export prefix、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - _load_env_file に override/protected 機構を導入し、OS 環境変数保護や上書き制御を実現。
  - Settings クラスを提供し、主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）をプロパティで取得。env/log レベルのバリデーション（有効値チェック）を実装。
  - settings インスタンスを公開。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）に JSON mode で問い合わせて銘柄別センチメント（-1.0〜1.0）を算出する機能を実装（score_news）。
  - タイムウィンドウ計算（前日15:00 JST 〜 当日08:30 JST）を calc_news_window で提供（UTC naive datetime の返却）。
  - バッチ処理（最大20銘柄 / リクエスト）とトークン肥大対策（1銘柄あたり最大記事数／最大文字数でトリム）を実装。
  - リトライ（429・ネットワーク断・タイムアウト・5xx）および指数バックオフを実装。API 失敗時は安全にスキップして継続するフェイルセーフ設計。
  - OpenAI 呼び出しを行う内部フック _call_openai_api を用意（ユニットテストで差し替え可能）。
  - レスポンス検証 (_validate_and_extract) を実装し、JSON 抽出、型検証、未知コードの無視、数値チェック、スコアの ±1.0 クリップを行う。
  - DuckDB への書き込みは冪等性を意識し、対象コードのみ DELETE → INSERT を行う（executemany の空リストを回避する処理あり）。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ冪等的に書き込む機能を実装（score_regime）。
  - マクロキーワードによる raw_news フィルタリング、OpenAI（gpt-4o-mini）への問い合わせ、リトライ・フォールバック戦略を実装。API 失敗時は macro_sentiment=0.0 として継続。
  - 内部での MA 計算は DuckDB クエリで行い、ルックアヘッドバイアスを避けるため target_date 未満のデータのみを使用。
  - OpenAI 呼び出し用の内部関数を独立実装し、news_nlp と内部実装を共有しないことでモジュール結合を防止。

- 研究（research）モジュール
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の扱い（None）を明示。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播等を考慮。
    - calc_value: raw_financials から最新財務を取得して PER（EPS が 0/欠損時は None）・ROE を計算。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 複数ホライズンの将来リターンを一度のクエリで計算（horizons の検証あり）。
    - calc_ic: Spearman ランク相関（Information Coefficient）計算（レコード結合・None 除外・有効件数閾値）。
    - rank: 同順位は平均ランクとするランク関数（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の基本統計量を算出。
  - research パッケージの __all__ で主要関数を公開。

- データ基盤（data）
  - calendar_management モジュールを実装:
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定ユーティリティ。
    - market_calendar が未取得の場合の曜日ベースのフォールバック、DB 値優先の一貫性、探索上限（_MAX_SEARCH_DAYS）による安全策を実装。
    - calendar_update_job: J-Quants API（jquants_client）から差分フェッチして market_calendar を冪等更新。バックフィルおよび健全性チェック（未来日異常検出）を実装。
  - ETL パイプライン（data.pipeline）を実装:
    - ETLResult dataclass を実装（取得数／保存数／品質問題／エラーの集約、辞書変換ユーティリティ付き）。
    - 差分取得、バックフィル、品質チェック連携（quality モジュール経由）を行う設計（実装はパイプライン骨組み）。
    - DuckDB テーブル存在確認や最大日付取得ユーティリティを提供。
  - data.etl は pipeline.ETLResult を再エクスポート。

- 共通
  - 多くの DB 書き込みで BEGIN / DELETE / INSERT / COMMIT を用いた冪等書き込み、例外時の ROLLBACK とログ出力を実装。
  - DuckDB を主要なローカル分析 DB として利用（DuckDBPyConnection を引数とする公開 API が多い）。

### Changed
- （初回リリースのため過去からの変更はありません）

### Fixed
- （初回リリース、既知のバグ修正履歴はなし）

### Notes / Migration
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI を使用する機能（score_news, score_regime）は OPENAI_API_KEY が必要（api_key 引数で注入可能）。
- デフォルトの DB パス:
  - DUCKDB_PATH = data/kabusys.duckdb（expanduser 対応）
  - SQLITE_PATH = data/monitoring.db
- DuckDB バージョン差異への配慮:
  - executemany に空リストを渡せない環境（例: DuckDB 0.10）に対応する条件分岐を導入。
- テスト向けフック:
  - OpenAI 呼び出し関数（各モジュール内の _call_openai_api）を unittest.mock.patch で差し替え可能。

---

今後のリリース案内やバグ修正・機能追加はこの CHANGELOG に追記します。必要であれば、各モジュールごとの API 使用例や環境構築手順を別途ドキュメント化します。