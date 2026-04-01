# Keep a Changelog
すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の慣習に準拠しています。  

なお、本リリース内容はソースコードの実装から推測して記載しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-04-01
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開対象モジュールのエクスポート: data, strategy, execution, monitoring（将来的なモジュール構成を想定）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用途）。
  - .env パーサ: export 形式、引用符付き値のエスケープ、インラインコメント処理などに対応。
  - 環境変数アクセサ（Settings クラス）を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須変数取得
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等のパス既定値
    - CPU/MEM/DISK の閾値、ログレベル検証、環境（development/paper_trading/live）検証ヘルパ

- AI（自然言語処理）関連 (src/kabusys/ai)
  - ニュースセンチメント分析 (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を基に銘柄毎のニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを算出。
    - バッチ処理（1コール最大 20 銘柄）、1銘柄あたりの記事数・文字数上限、レスポンス検証を実装。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なパースとバリデーション（results 配列、code・score の検証、スコア ±1.0 でクリップ）。
    - calc_news_window 関数でニュース対象ウィンドウ（JST基準）を算出。target_date を引数に取りルックアヘッドバイアスを防止。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を算出。
    - DuckDB から prices_daily, raw_news を参照、計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは専用の内部実装を使用し、API のリトライ・エラー時は macro_sentiment=0.0 にフォールバック。
    - LLM モデルは gpt-4o-mini を採用。

  - テスト容易性: API 呼び出しラッパー（_call_openai_api）はテストでモック差し替え可能（unittest.mock.patch）。

- 研究 / ファクター計算 (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6Mリターン、200日MA乖離）、Value（PER, ROE）、Volatility（20日ATR）、Liquidity（20日平均売買代金、出来高比）を DuckDB の prices_daily / raw_financials から計算。
    - 欠損データやデータ不足時の扱い（None を返す）を明記。
  - feature_exploration.py
    - 将来リターン計算（複数ホライズン指定可）、Spearman ランク相関（IC）計算、ランク変換関数、カラム統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDBのみで実装。

- データプラットフォーム (src/kabusys/data)
  - calendar_management.py
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）および夜間バッチ更新 job を実装。
    - DBデータがない場合は曜日ベースでフォールバック。最大探索日数やバックフィル等の安全策を導入。
  - pipeline.py / etl.py
    - ETLResult データクラスおよび ETL パイプラインの基礎ロジック（差分取得、保存、品質チェック呼び出し方針）を実装。
    - jquants_client (別モジュール想定) と連携して差分取得および idempotent 保存（ON CONFLICT）を行う設計。

### 変更 (Changed)
- （初回リリースのため特記すべき変更はありません）

### 修正 (Fixed)
- （初回リリースのため特記すべき修正はありません）

### セキュリティ (Security)
- .env ロード時、既存の OS 環境変数を保護するため protected セットを導入。override=True の場合でも OS 環境変数は上書きしない設計。
- 機密情報は Settings 経由で取得し、必須環境変数未設定時は ValueError を発生させ明示。

### 既知の制約 / 設計上の注意点（重要）
- OpenAI API
  - AI 機能（score_news, score_regime）は OPENAI_API_KEY を引数または環境変数で必須。未指定の場合は ValueError を送出。
  - 使用モデルは gpt-4o-mini。API 応答は JSON モード（厳密な JSON）を前提にしているが、余剰テキストを含む場合の復元ロジックも備える。
- DB スキーマ依存
  - 多くの関数は DuckDB 接続と特定テーブル（prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols, market_calendar 等）を前提とする。事前に該当スキーマ/テーブルを準備する必要がある。
- ルックアヘッドバイアス回避
  - 全ての分析関数は内部で date.today()/datetime.today() を参照せず、必ず target_date を引数に取る設計。
- フェイルセーフ
  - API 呼び出し失敗時は基本的に例外を投げずフォールバック（0.0 やスキップ）し、部分失敗でその他データが消えないように部分的な DELETE→INSERT を採用。
- DuckDB の互換性
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への対応をコード内で考慮。

### 互換性 / マイグレーション (Migration)
- 初回リリースのため既存バージョンとの互換性設定は不要。
- 利用開始時のチェックリスト（主な環境変数、DB 等）:
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN（J-Quants API）
    - KABU_API_PASSWORD（kabuステーション API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
    - OPENAI_API_KEY（AI 機能を使う場合）
  - 任意/デフォルト:
    - DUCKDB_PATH（default: data/kabusys.duckdb）
    - SQLITE_PATH（default: data/monitoring.db）
    - PID_FILE_PATH（default: data/execution.pid）
    - KABUSYS_ENV ∈ {development, paper_trading, live}（default: development）
    - LOG_LEVEL ∈ {DEBUG, INFO, WARNING, ERROR, CRITICAL}（default: INFO）
  - .env.example を参照して .env/.env.local を作成してください。
  - 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### テスト / 開発者向けメモ
- OpenAI 呼び出しラッパー（各モジュールの _call_openai_api）は unit test で patch 可能。LLM 呼び出しのモックを容易に行える設計。
- 主要な関数（score_news, score_regime, calc_* シリーズ）は DuckDB のコネクションと target_date を引数に取るため、テスト用のインメモリ DB を用意してユニットテストを行いやすい。

---

今後のリリースで想定される改善点（例）
- strategy / execution / monitoring モジュールの具体的実装追加（現在はエクスポート予定のみ）。
- jquants_client の実装と認証ワークフローの洗練。
- AI モデルの選択肢やプロンプト調整の外部設定化。
- ETL の差分取得・品質チェックの具体的な実装追加と監査ログ機能。

もし CHANGELOG に反映してほしい追加情報や日付修正などがあれば教えてください。