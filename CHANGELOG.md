# Changelog

すべての注記は Keep a Changelog の形式に準拠しています。  
現在のバージョン: 0.1.0（初期リリース）

## [0.1.0] - 2026-03-31

### Added
- 全体
  - 初期リリース。パッケージ名は `kabusys`。パッケージ版の __version__ は `0.1.0`。
  - パブリック API としてサブパッケージを公開: `data`, `strategy`, `execution`, `monitoring`（`__all__` に明示）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - OS の既存環境変数は保護され、.env.local/.env による意図しない上書きを防止。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用）。
    - プロジェクトルートは `__file__` を起点に `.git` または `pyproject.toml` を探索して検出（CWD に依存しない）。
  - .env パーシングはシェル形式（`export KEY=val`、クォート、エスケープ、インラインコメント）に対応。
  - `Settings` クラスで設定値をプロパティ経由で取得:
    - J-Quants / kabu API / Slack / DB パス（DuckDB/SQLite）/ 監視閾値 / 実行環境（development/paper_trading/live）/ログレベル 等。
    - 必須キー未設定時は明確なエラーメッセージで ValueError を送出。
    - `env` と `log_level` は許容値チェックを行い、不正値は ValueError。

- AI（自然言語処理）モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp.score_news`)
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを取得。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数上限・文字数トリム等のトークン肥大対策を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフとリトライ実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の存在、既知コードの検証、数値の有限判定）。
    - スコアは ±1.0 にクリップ。部分成功時に既存の ai_scores を保護するため、取得済みコードのみ DELETE→INSERT で置換。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して DB クエリに使用。ルックアヘッドバイアスを避ける設計。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。テスト時差し替え用に内部の API 呼び出し関数を patch 可能に実装。
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出はマクロキーワード群でフィルタ（日本・米国・グローバル関連語）。
    - OpenAI 呼び出しは JSON パース・エラーや API 障害時にフェイルセーフ（macro_sentiment=0.0）で継続。
    - 計算結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）、書き込み失敗時は ROLLBACK を試行して上位に例外を伝播。

- データプラットフォーム / ETL (`kabusys.data`)
  - ETL 結果を表す `ETLResult` データクラスを提供（`kabusys.data.pipeline.ETLResult` を `kabusys.data.etl` で再エクスポート）。
    - ETL の取得数 / 保存数 / 品質問題 / エラーを保持し、辞書化メソッドを提供。
  - パイプライン設計（`kabusys.data.pipeline`）
    - 差分更新・バックフィル・品質チェックの方針を実装（品質問題は収集して呼び出し元が判断できるように）。
    - DuckDB を前提としたテーブル存在チェック、最終取得日の算出ユーティリティ等を実装（安全な SQL バインドに注意）。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダー（market_calendar）を使った営業日判定ユーティリティ群: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB に登録がある場合は DB 値を優先し、未登録日は曜日ベースのフォールバック（週末除外）で一貫した挙動を提供。
    - 夜間バッチ job (`calendar_update_job`) を実装。J-Quants から差分取得し idempotent に保存。バックフィルと健全性チェックを備える。
    - 最大探索日数やルックアヘッド等の安全パラメータを定義して無限探索を防止。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（データ不足時は None を返す）。
    - Volatility / Liquidity: 20日 ATR（平均）、相対 ATR、20日平均売買代金、出来高比率等。
    - Value: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から取得）。
    - 全て DuckDB の prices_daily / raw_financials を参照し、外部 API にはアクセスしない（研究用）。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応（デフォルト [1,5,21]）。ホライズン引数のバリデーションを実施。
    - IC 計算（calc_ic）: ランク相関（Spearman の ρ）を内部実装（ties の平均ランク処理含む）。
    - 統計サマリー（factor_summary）とランク変換（rank）ユーティリティを実装。
  - データ正規化ユーティリティ（zscore_normalize）は `kabusys.data.stats` から再エクスポート。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Deprecated
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 環境変数の取り扱いに注意:
  - API キー（OpenAI 等）を明示的に引数で注入可能。未設定時は ValueError を出して安全に停止する。
  - .env 自動ロードはデフォルトで有効だが、明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 実装上の重要な設計判断（ドキュメント的注記）
- ルックアヘッドバイアス対策:
  - AI・研究モジュールは内部で datetime.today() / date.today() を参照せず、必ず外部から target_date を与える設計。
  - DB クエリも target_date 未満 / 排他条件を明示して将来データの参照を避ける。
- DB 書き込みは冪等性を重視（DELETE→INSERT または ON CONFLICT 相当の保存を意図）。
- OpenAI API 呼び出し部分はテスト容易性のため patch 可能に実装（内部関数を差し替えられる）。
- DuckDB のバージョン差異（executemany の空パラメータ制約など）に配慮した実装が随所にある。

---

今後のリリースで期待される項目（予定、未実装）
- Strategy / Execution / Monitoring の詳細な実装と発注ロジック（現在はパッケージ構造のみ公開）。
- ai モデルやプロンプトのチューニング、より詳細な品質チェックの強化。
- テスト・CI 向けドキュメントとサンプル DB/データの提供。

（以上）