# Changelog

すべての注目できる変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムの基盤となる主要機能を実装しました。

### Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）。
  - 柔軟な .env パーサ実装:
    - export KEY=val 形式対応、クォート（' "）のエスケープ処理、インラインコメント処理。
  - Settings クラスを提供してアプリ設定をプロパティで取得可能（J-Quants / kabuAPI / Slack / DB パス / 実行環境 / ログレベル等）。
    - 環境変数の必須チェック（未設定時は ValueError）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - duckdb/sqlite のデフォルトパスを用意。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出。
    - バッチ処理（_BATCH_SIZE=20）、1銘柄あたり記事数上限・文字数上限（トリム）を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。
    - レスポンス検証・スコアクリッピング（±1.0）。
    - ai_scores テーブルへの冪等的な置換書き込み（DELETE→INSERT、部分失敗時に既存スコアを保護）。
    - calc_news_window を提供（ニュース収集ウィンドウを JST ベースで UTC naive datetime に変換）。
    - テスト容易性のため OpenAI 呼び出しは差し替え可能（ユニットテスト向けパッチ箇所を想定）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロキーワードで raw_news をフィルタし、LLM（gpt-4o-mini）に JSON レスポンスを要求して macro_sentiment を取得。
    - API エラー・パースエラー時はフォールバック macro_sentiment=0.0 として継続（フェイルセーフ）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - lookahead バイアス防止: target_date 未満のデータのみを使用、datetime.today() を参照しない設計。
    - リトライ・バックオフ・最大試行回数などの制御。

- リサーチ / ファクター群（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（単純平均）、相対ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新の EPS/ROE を組み合わせて PER/ROE を算出（EPS が 0/欠損時は None）。
    - 設計: DuckDB の SQL と Python を組み合わせ、prices_daily / raw_financials のみ参照。本番 API とは独立。
  - feature_exploration:
    - calc_forward_returns: デフォルトホライズン [1,5,21] の将来リターンを計算。horizons 引数の検証あり。
    - calc_ic: Spearman（ランク相関）による Information Coefficient を実装（同順位は平均ランクで扱う）。
    - rank: 同順位を平均ランクで処理、丸め誤差対策あり（round(..., 12)）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research パッケージの __all__ に主要関数を公開。zscore_normalize を data.stats から再エクスポート。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を参照して営業日判定/is_sq_day/next/prev/get_trading_days のユーティリティを提供。
    - market_calendar が存在しない場合は曜日（平日）ベースのフォールバックを行う実装。
    - 最大探索日数制限で無限ループ防止。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル機構、健全性チェック、J-Quants クライアント経由で保存）。
  - pipeline:
    - ETL の差分取得 / 保存 / 品質チェックフローに対応。
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー集約・ヘルパーメソッド）。
    - 内部ユーティリティ（テーブル存在チェック、最大日付取得、トレーディング日補正等）。
  - etl: pipeline.ETLResult を再エクスポート。

- 実装方針（クロスカット）
  - DuckDB を主要ストレージとして利用（DuckDB 接続を引数に取る API を一貫して提供）。
  - ルックアヘッドバイアス防止の徹底（datetime.today()/date.today() の無分別使用を避け、ターゲット日を明示的に渡す）。
  - API 呼び出し失敗時のフェイルセーフ設計（LLM / 外部 API が失敗しても例外を投げずスコアにフォールバックまたは該当箇所のみスキップ）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT を想定）。
  - テスト容易性: OpenAI 呼び出し等は単体テストで差し替え可能な実装。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Notes / Development details
- OpenAI のモデル (gpt-4o-mini) を JSON Mode で利用する想定。レスポンスパースの堅牢性に配慮（余計な前後テキストの復元ロジック等）。
- DuckDB のバージョン差異に配慮した実装（executemany の空リスト禁止などへの対応）。
- J-Quants / kabu ステーション / Slack 等の外部設定は環境変数で管理（Settings で必須チェック）。
- 今後のリリースでは strategy / execution / monitoring の実装や CI/テストケースの追加、ドキュメント強化を予定。

---
（以降のバージョンはここに追記してください）