Keep a Changelog に準拠した CHANGELOG.md

すべての注目すべき変更を記録します。セマンティック バージョニングを使用しています。

未リリースの変更は "Unreleased" に記載します。

README やリリースノート作成時の補助として、コードベースの内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-29
初期リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加: バージョン __version__ = "0.1.0" を src/kabusys/__init__.py に定義。
  - パッケージの公開APIを __all__ で整理（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを追加。
  - 自動 .env ロード（プロジェクトルートは .git または pyproject.toml を探索して判定）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - 行末コメント処理（クォートなしの '#' をスペース/タブ直前でコメントとして扱う）。
  - .env 読み込み時の上書き制御（override, protected）により OS 環境変数を保護。
  - 必須設定取得ヘルパー _require と各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH など）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性チェック（許容値は定義済み）。

- AI モジュール (src/kabusys/ai/)
  - ニュースNLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ計算 calc_news_window（JST 前日15:00〜当日08:30 を UTC 変換）を提供。
    - バッチ処理（1回最大 20 銘柄）、1 銘柄あたりの記事上限・文字数トリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
    - OpenAI 呼び出しのリトライ・指数バックオフ（429/ネットワーク断/タイムアウト/5xx 対応）を実装。
    - レスポンスの厳格なバリデーション（JSON 抽出、"results" 構造、既知コードフィルタ、数値チェック）とスコアの ±1 クリッピング。
    - 部分成功時も他銘柄の既存スコアを消さないよう、DELETE→INSERT を銘柄ごとに実行（DuckDB 互換性考慮）。
    - OpenAI API キー必須（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等保存する機能を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを回避。
    - マクロキーワードに基づくタイトル抽出、OpenAI（gpt-4o-mini）での macro_sentiment スコアリング（JSON 応答想定）。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - リトライ・バックオフ、5xx の再試行ロジック、JSON パース失敗のフォールバック実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。失敗時は ROLLBACK を試行して例外を再送出。
    - API キーは引数または環境変数 OPENAI_API_KEY。

- データ (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダーの取得／夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得→保存（save_market_calendar 呼び出し）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定・探索ユーティリティ。
    - market_calendar 未取得時は曜日ベース（土日休み）でフォールバック。DB 登録値が優先され、未登録日は一貫した曜日フォールバックを使用。
    - 最大探索日数やバックフィル、健全性チェック（未来日付の異常検出）を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を追加（取得件数、保存件数、品質問題、エラー一覧などを含む）。
    - 差分更新、バックフィル設計、品質チェック連携のためのユーティリティを提供する基盤。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- Research（因子/特徴量解析） (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、ma200_dev）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB による SQL ウィンドウ関数利用により効率よく計算。データ不足時は None を返す仕様。
    - 外部 API にはアクセスせず prices_daily / raw_financials のみ参照。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas など外部依存なしでアルゴリズムを実装。
  - data.stats から zscore_normalize を再エクスポートする仕組みを提供。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- AI 機能は OpenAI API キー（OPENAI_API_KEY）を必須としており、キーの管理は環境変数経由を想定。
- .env 自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。OS 環境変数は上書き防止（protected）により保護される実装。

### Notes / 実装上の設計方針（重要な振る舞い）
- ルックアヘッドバイアス回避:
  - AI / リサーチ系処理は内部で datetime.today()/date.today() を参照せず、すべて target_date 引数に基づく計算を行う。
  - DB クエリは target_date より未来のデータを参照しないように設計。
- フェイルセーフ:
  - OpenAI API の失敗時は例外を投げず中立値（0.0）やスキップを選び、処理全体の停止を避ける方針。
- 冪等性/トランザクション:
  - market_regime, ai_scores, market_calendar 等のテーブル更新は冪等になるよう DELETE→INSERT / ON CONFLICT 相当の処理やトランザクションを用いて実装。
- DuckDB 互換性への配慮:
  - executemany の空リストバインド回避や list 型バインドの回避など、DuckDB のバージョン差分を考慮した実装がある。
- テスト容易性:
  - OpenAI 呼び出し部分は内部で _call_openai_api をラップしており、ユニットテストで patch / mock しやすいように分離。

### Breaking Changes
- なし（初回リリース）

---

上記は提供されたコード内容・コメントから推測して作成した CHANGELOG です。実際のリリースノートとして公開する際は、コミット履歴や実際の変更差分をもとに調整してください。