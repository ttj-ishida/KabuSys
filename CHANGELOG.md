# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回公開リリース。

### Added
- パッケージ初期構成
  - パッケージメタ情報を src/kabusys/__init__.py にて定義（version = 0.1.0）。
  - 公開サブパッケージ: data, strategy, execution, monitoring を想定したエクスポートを追加。

- 環境設定・自動.envローダー（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml が基準）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理をサポート。
  - OS 環境変数を保護するため .env.local の上書き時に既存キーを保護する仕組みを実装。
  - 必須環境変数取得ヘルパー `_require` と、Settings クラスを提供。主な設定項目:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - PID / KILL フラグパスやリソース閾値（CPU/Memory/Disk）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL 検証

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）の JSON mode で一括センチメントスコアを取得し、ai_scores テーブルへ保存する処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（DBはUTCで保存されている前提）。
  - バッチ処理: 最大20銘柄単位で API 呼び出し（_BATCH_SIZE = 20）。
  - トークン肥大化対策: 1銘柄あたり最大記事数/文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行（429 / ネットワーク断 / タイムアウト / 5xx）に対して指数バックオフでリトライ実装（最大試行回数制御）。
  - レスポンスの堅牢なバリデーションとパース（JSON 抜き出し・型検査・未知コード無視・スコア数値化・±1.0 クリップ）。
  - 部分成功時にも既存スコアを保護するため、書き込みは対象コードで DELETE（個別）→ INSERT の冪等置換を実行。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225連動型）について直近200日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
  - マクロニュースは news_nlp.calc_news_window で指定されるウィンドウからマクロキーワードでフィルタしてタイトルを抽出。
  - OpenAI API（gpt-4o-mini）を JSON モードで呼び出し、レスポンスをパースして macro_sentiment を取得。
  - データ不足や API 失敗時にはフェイルセーフとして中立値（ma200_ratio=1.0 / macro_sentiment=0.0）を使用。
  - 最終結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックを試行。

- 研究用ファクター計算（src/kabusys/research/）
  - factor_research.py:
    - モメンタム（1M/3M/6M）、200日移動平均乖離（ma200_dev）を calc_momentum で計算。
    - ボラティリティ/流動性指標（20日ATR、相対ATR、20日平均売買代金、出来高比率）を calc_volatility で計算。
    - バリュー指標（PER、ROE）を calc_value で raw_financials と prices_daily から計算。
    - 全関数は DuckDB 接続を受け取り SQL＋Python のハイブリッドで完結。外部APIや実際の発注にはアクセスしない設計。
  - feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（デフォルト horizons=[1,5,21]）を実装（LEAD を用いた単一クエリ取得、ホライズン検証）。
    - IC（Information Coefficient）を Spearman ランク相関で計算する calc_ic を実装。null/非有限値排除、最小レコード数検査。
    - ランク変換 util rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存しない純粋標準ライブラリ実装。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management.py:
    - market_calendar テーブルを用いた営業日判定ロジックを実装（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB にデータが無い/未登録日は曜日ベースのフォールバック（平日を営業日として扱う）で一貫した結果を返す設計。
    - calendar_update_job を実装し、J-Quants クライアント経由で差分取得→保存（バックフィル、健全性チェック含む）を行う。
  - pipeline.py:
    - ETLResult データクラス（ETL 実行のサマリ）を実装（取得件数・保存件数・品質問題・エラーメッセージ等を保持）。
    - 差分取得・バックフィル・品質チェック・idempotent な保存（jquants_client の save_* 想定）を行う ETL パイプラインの基盤を実装。
    - デフォルトのバックフィル日数やカレンダー先読み等の定数を定義。
  - etl.py:
    - pipeline.ETLResult の再エクスポートを提供。

- 共通
  - 全体として DuckDB を主要なローカルデータストアとして利用する設計（関数は DuckDB 接続を引数に取る）。
  - ロギングと警告を多用し、フェイルセーフ（例外を直接上位へ上げないケース）とデバッグ情報の提供に配慮。

### Changed
- （該当なし、初回リリースのため変更履歴はなし）

### Fixed
- （該当なし、初回リリースのため修正履歴はなし）

### Security
- （該当なし）

---

注記:
- OpenAI API を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または api_key 引数を必須とします。未設定時は ValueError を送出します。
- .env の自動ロードや DB 書き込みは実行環境に依存するため、テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD の設定や DuckDB のモック/テスト用 DB を利用してください。