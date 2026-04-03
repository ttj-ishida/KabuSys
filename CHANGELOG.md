# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定バージョンをセマンティックバージョニングで管理します。

## [Unreleased]


## [0.1.0] - 2026-04-03
初回リリース。

### Added
- パッケージ骨組み
  - パッケージ名: kabusys
  - エントリポイント設定 (src/kabusys/__init__.py) により、data, strategy, execution, monitoring を公開。

- 設定管理
  - 環境変数 / .env ファイル自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは __file__ 起点で .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは export 構文やシングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - protected（既存 OS 環境変数）を上書き不可にする仕組みを導入。
  - Settings クラスを提供し、各種必須/任意設定をプロパティとして取得可能:
    - J-Quants: JQUANTS_REFRESH_TOKEN（必須）
    - kabu ステーション: KABU_API_PASSWORD（必須）、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE: LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DB パス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - 監視ファイル: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - リソース閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
    - 環境モード検証: KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の妥当性チェック

- データ基盤関連（DuckDB ベース）
  - マーケットカレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（週末は非営業日）。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・冪等保存を実装。健全性チェック（将来日付の過大値スキップ）あり。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 差分更新・保存・品質チェックのフローを実装。
    - ETLResult データクラスを定義して ETL の結果（フェッチ数・保存数・品質問題・エラー等）を集約。etl モジュールで再エクスポート。
    - 初回ロード開始日、バックフィル挙動、品質チェック（重大度）の扱いに関する設計を導入。

- AI / NLP 機能（OpenAI API を利用）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信して ai_scores テーブルへ保存。
    - JST ベースのニュース収集ウィンドウを定義（前日15:00〜当日08:30 JST、内部は UTC naive datetime）。
    - バッチサイズ制御、1銘柄あたりの記事数・文字数トリム、最大リトライ（429/ネットワーク/タイムアウト/5xx）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造チェック、コード検証、数値検証）と ±1.0 クリッピング。
    - API 呼び出し部分はテスト容易性のため差し替え可能に設計（_call_openai_api を patch 可能）。
    - フェイルセーフ: API エラーやパース失敗時は該当チャンクをスキップし、処理継続。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数 を返す。
    - モジュール初期化で score_news を公開 (src/kabusys/ai/__init__.py)。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュースは raw_news からマクロキーワードでフィルタして取得し、OpenAI により JSON で macro_sentiment を取得（フェイルセーフで失敗時は 0.0）。
    - リトライ、指数バックオフ、レスポンスパース耐性を備える。
    - 判定結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。公開 API: score_regime(conn, target_date, api_key=None)。

- リサーチ / ファクター
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から算出する関数を実装。
    - データ不足時の None ハンドリング、営業日スキャン幅のバッファ設計。
    - 関数: calc_momentum, calc_volatility, calc_value を公開。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン算出（calc_forward_returns）: 複数ホライズンを同時取得、入力検証、バッファ日数設計。
    - IC 計算（calc_ic）: Spearman ランク相関（同順位は平均ランク）を実装。十分なサンプルがない場合は None を返す。
    - ランク関数（rank）や統計サマリー（factor_summary）を実装。
    - 既存の zscore_normalize を data.stats から再利用。
    - research パッケージの __init__ で主要関数を公開。

- 汎用 / 実装上の工夫
  - DuckDB を主要な分析 DB として想定。SQL を多用した実装により大量データでも効率的に処理可能な設計。
  - ルックアヘッドバイアス回避: モジュール内で datetime.today() / date.today() を直接参照しない方針を採用（すべて target_date を明示的に受け取る）。
  - OpenAI への呼び出しは冪長性・回復性（リトライ、バックオフ、5xx 判定）を考慮して実装。
  - DB 書き込みは部分失敗を避けるため、書き込み対象コードを限定して削除・挿入する設計（ai_scores など）。
  - テスト容易性を意識した設計（_call_openai_api のパッチ、API キー注入、自動.envロード抑止フラグ）。

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

注: 本CHANGELOGはコードベースからの推測に基づいて作成しています。実際の仕様や追加のモジュール（strategy, execution, monitoring など）については別途ドキュメントまたは将来のリリースノートで補足される予定です。