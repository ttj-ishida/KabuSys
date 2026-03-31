# Changelog

すべての重要な変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- 初回リリースを公開。
- パッケージのエントリポイントを定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"
  - パブリック API に data, strategy, execution, monitoring をエクスポート。
- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
  - .env と .env.local の自動読み込みをサポート（プロジェクトルート判定は .git / pyproject.toml を基準）。
  - export 形式の行、クォート付き値、インラインコメント処理に対応したパーサ実装。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL）。
  - env, log_level の入力検証（許容値チェック）と利便性メソッド（is_live / is_paper / is_dev）を実装。
- AI 関連モジュールを追加（src/kabusys/ai/）。
  - ニュースセンチメントスコアリング: score_news（src/kabusys/ai/news_nlp.py）
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ定義（calc_news_window）。
    - raw_news と news_symbols を元に銘柄ごとに記事を集約（最大記事数・文字数でトリム）。
    - OpenAI の gpt-4o-mini を JSON mode でバッチ呼び出し（最大 20 銘柄/リクエスト）。
    - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスの厳密バリデーション（results 配列、code/score の検証、スコアのクリップ ±1.0）。
    - 成功した銘柄のみ ai_scores テーブルへ冪等書き込み（DELETE → INSERT、DuckDB executemany 空配列対策）。
  - 市場レジーム判定: score_regime（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み合成（MA:70%、マクロ:30%）してレジーム（bull/neutral/bear）を日次で判定。
    - マクロ記事はキーワードフィルタで抽出し、OpenAI で JSON レスポンスを期待。
    - API 呼び出しのリトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時の ROLLBACK ハンドリング。
  - AI モジュールの public export（src/kabusys/ai/__init__.py）で score_news を公開。
- リサーチ（研究）モジュールを追加（src/kabusys/research/）。
  - factor_research.py: モメンタム／ボラティリティ／バリュー系のファクター計算
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離等を計算（prices_daily に依存）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合して PER, ROE を計算（最新報告日以前の財務データを使用）。
  - feature_exploration.py: 将来リターン・IC・ランク・統計要約
    - calc_forward_returns: 指定ホライズン先の将来リターンを一括取得（データ存在チェック、horizons の検証）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（不足データ時は None を返す）。
    - rank / factor_summary: ランク変換（同順位平均ランク）・基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージの __init__ で主要関数を再エクスポート。
- データプラットフォーム関連モジュールを追加（src/kabusys/data/）。
  - calendar_management.py: 市場カレンダー管理と営業日ユーティリティ
    - market_calendar テーブル優先の営業日判定（未取得日は曜日ベースのフォールバック）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・保存（fetch & save を jquants_client に委譲）。健全性チェックやバックフィルの仕組みを実装。
  - pipeline.py: ETL パイプライン基盤と ETLResult（src/kabusys/data/pipeline.py）
    - ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラーの集約）。
    - 差分取得用のヘルパ（_get_max_date 等）とテーブル存在チェックを実装。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - jquants_client との連携箇所（fetch/save）は設計上分離（jquants_client 側実装に依存）。
- データユーティリティ: DuckDB を主なストレージ層として使用する実装が多数にわたって導入。

### 変更 (Changed)
- コード全体で「ルックアヘッドバイアス」を避ける設計方針を採用。
  - datetime.today() / date.today() を内部ロジックの直接参照に使用しない（target_date を引数で明示）。
  - DB クエリは target_date 未満/未満等の排他条件を適切に設定。
- OpenAI API 呼び出しはモジュールごとに独立した _call_openai_api 実装にし、テスト時の差し替えを容易にした（unittest.mock.patch を想定）。
- DuckDB のバージョン差異に配慮した実装（executemany の空配列回避、list バインドの互換性等）。

### 修正 (Fixed) / 耐障害性向上 (Hardening)
- OpenAI API 呼び出しに対して詳細な例外ハンドリングとリトライ（429/タイムアウト/接続エラー/5xx）を実装し、最終的に安全にフォールバックする（スコア 0.0 やスキップ）。
- JSON モード応答のパースで余計な前後テキストが混入するケースを考慮し、最外の波括弧を抽出して復元を試みる処理を追加。
- DB 書き込みをトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK の失敗時は警告ログを出力するように改善。
- calendar_update_job における「最後の取得日が極端に将来の日付」の健全性チェックを追加し、異常時は処理をスキップしてログを残すようにした。
- news_nlp と regime_detector の設計では、API キーが未設定の場合に ValueError を送出し、呼び出し側で明示的に対応できるようにした。

### ドキュメント (Documentation)
- 各モジュール冒頭に設計方針・処理フロー・注意点を詳細に記載。  
  - 例: news_nlp / regime_detector / calendar_management / pipeline / factor_research の各ファイル先頭の説明コメントに処理手順と設計上の注意を明示。

### 互換性について (Breaking Changes)
- 初回リリースのため既存互換性の破壊はなし。ただし今後のバージョンで DB スキーマや公開 API を変更する場合は changelog に明記予定。

### 必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 用設定（KABU_API_BASE_URL はデフォルトあり）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- OPENAI_API_KEY: OpenAI 呼び出しで使用（score_news / score_regime の api_key 引数が None の場合参照）
- DUCKDB_PATH, SQLITE_PATH: データベースファイルパス（デフォルト値あり）
- KABUSYS_ENV: 開発/ペーパー/本番判定（development, paper_trading, live）

---

注記:
- 実行には DuckDB と OpenAI の公式 Python SDK が必要です。
- jquants_client / quality / 及び一部外部依存は別実装を想定しているため、実行環境ではそれらの提供が必要です。