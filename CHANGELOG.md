# Changelog

すべての重要な変更点をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（src/kabusys/__init__.py）。
  - バージョン情報: `__version__ = "0.1.0"`。

- 環境設定 & ロード
  - 環境変数 / .env ファイル管理モジュール（src/kabusys/config.py）を追加。
    - .env と .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用途）。
    - export 形式・コメント・クォート・エスケープに対応したパーサ `_parse_env_line` を実装。
    - 必須設定を取得する `_require`、各種設定値を取得する `Settings` クラス（`settings` インスタンス）を提供。
    - 主要環境変数例:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - OPENAI_API_KEY（AI モジュール用）
      - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）
      - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等のパス設定
      - KABUSYS_ENV（development / paper_trading / live）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データプラットフォーム
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - calendar_update_job: J-Quants から差分取得して `market_calendar` を更新（バックフィル・健全性チェックあり）
    - DB 登録がない場合は土日フォールバックで動作。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）により無限ループ回避。
  - ETL パイプライン & 結果型（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数 / 保存件数 / 品質チェック結果 / エラー情報 等を含む）。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計。
    - jquants_client 経由での idempotent な保存（ON CONFLICT / DELETE→INSERT パターン）を前提。
  - pipeline / etl の公開インターフェースをエクスポート。

- 研究（Research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）を追加:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）
    - calc_volatility: 20日 ATR, 相対ATR, 平均売買代金, 出来高比率
    - calc_value: PER（EPS が 0/欠損時は None）、ROE（raw_financials から取得）
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials を参照）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）を追加:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理
    - 標準ライブラリのみで実装（pandas 等非依存）
  - zscore_normalize を data.stats から再エクスポート（src/kabusys/research/__init__.py）。

- AI モジュール
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（UTC 換算で前日06:00 ～ 23:30）を対象（calc_news_window を提供）。
    - バッチサイズ: 最大 20 銘柄/1 API コール（_BATCH_SIZE）。
    - トークン肥大対策: 1 銘柄最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode を利用し厳密な JSON 出力を期待。レスポンスの堅牢なバリデーションを実装（_validate_and_extract）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフで再試行（設定: _MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - API 失敗時は該当チャンクをスキップし、部分成功は既存スコアを保護して成功分のみ置換（DELETE → INSERT）。
    - テスト用に OpenAI 呼び出しを _call_openai_api で抽象化（unittest.mock.patch による差し替え可能）。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数（int）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロキーワードによる raw_news フィルタリングを実施し、最大 20 記事を LLM に送信。
    - LLM モデル: gpt-4o-mini、JSON Mode、システムプロンプトで厳密な JSON を期待。
    - フェイルセーフ: LLM 呼び出し失敗時は macro_sentiment = 0.0 として継続。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。失敗時は ROLLBACK を試行。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）。未設定の API キーは ValueError を送出。

- 動作設計上の注意点（明示的に実装）
  - ルックアヘッドバイアス回避: datetime.today()/date.today() を内部で直接参照せず、target_date を外部から受け取る方式を採用。
  - DuckDB 互換性: executemany に空リストを渡さない等、DuckDB の制約に配慮した実装。
  - idempotent な DB 更新（削除 → 挿入）により部分失敗時のデータ保護を行う。
  - OpenAI 呼び出しは専用ラッパー関数を介しており、テスト時に差し替え可能。

### Fixed
- 初回リリースにつき該当なし。

### Changed
- 初回リリースにつき該当なし。

### Security
- API キー等の機密情報は環境変数から取得する設計。自動 .env 読み込みを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。

### Notes / Limitations
- OpenAI SDK（OpenAI）および duckdb パッケージへの依存があるため、実行環境にこれらをインストールする必要があります。
- news_nlp と regime_detector は gpt-4o-mini と JSON Mode を前提としている。API の応答形式変化があった場合はパース側で失敗し、失敗分はフェイルセーフでスキップされる設計です。
- J-Quants クライアント（jquants_client）への依存箇所が存在する（calendar_update_job / pipeline 等）。実環境では jquants_client の実装・認証情報が必要です。
- 本リリースは「データ処理 / 研究 / AI スコアリング」機能を中心に提供し、実際の売買・発注ロジック（execution 等）は別モジュールとして想定（パッケージ公開時に __all__ で execution, monitoring 等を露出）。

---

貢献・バグ報告・改善提案は issue を通じて受け付けます。