# CHANGELOG

すべての重要な変更を Keep a Changelog の形式で記載します。  
初版リリース: 0.1.0（2026-04-02）

## [0.1.0] - 2026-04-02

Added
- 基本パッケージ初期実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0。公開モジュール群として data, research, ai, などをエクスポート。
- 環境設定（kabusys.config）
  - .env 自動ロード機構を実装（プロジェクトルートの .git または pyproject.toml を探索してルートを決定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを考慮。
  - protected（OS 環境変数保護）を考慮した上書きロジック。
  - Settings クラス実装: J-Quants / kabu station / Slack / DB パス / 監視しきい値 / env/log_level 判定等のプロパティを提供。必須環境変数未設定時は ValueError を送出。
  - デフォルト値: KABUSYS_ENV=development、KABUSYS API ベース URL 等や DB パス（DuckDB/SQLite）の既定値を用意。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news, news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）に JSON モードでバッチ評価して ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換）を正確に計算するユーティリティを実装（calc_news_window）。
  - バッチ処理（1 回につき最大 20 銘柄）・1 銘柄あたり記事最大 10 件、文字数トリム（3,000 文字）を実装。
  - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ、その他エラーはスキップして継続するフェイルセーフを実装。
  - レスポンスのバリデーション機構を実装（厳密な JSON チェック、"results" 構造、未知コードの無視、数値型チェック、スコア ±1 のクリップ）。
  - DB 書き込みは部分失敗を避けるため、取得済みコードだけを DELETE → INSERT で置換（冪等化・既存スコア保護）。
  - テスト注入のために内部の OpenAI 呼び出し点を差し替え可能にしている（unittest.mock.patch を想定）。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定する実装を追加。
  - ma200_ratio の計算（target_date 未満のデータのみ使用してルックアヘッドを防止）、マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini、JSON mode）、合成スコア計算、閾値判定を実装。
  - OpenAI API の呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - 結果は market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行。

- データ関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未登録日のフォールバックは曜日ベース（土日非営業）で一貫して扱う。最大探索範囲 _MAX_SEARCH_DAYS を導入して無限ループを回避。
    - calendar_update_job: J-Quants API クライアント（jquants_client）から差分取得して market_calendar テーブルへ冪等更新。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）
    - ETLResult dataclass を実装（取得数・保存数・quality issues・errors を保持）。has_errors / has_quality_errors / to_dict を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュール）を想定した設計。J-Quants クライアントとの連携ポイントを想定。
  - ETL の公開インターフェース（etl.py）で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算モジュール（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER、ROE）を DuckDB 上の SQL と Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の扱い（None を返す）やスキャンウィンドウ設定を実装。
  - 特徴量解析（feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、horizons の検証）、IC（Spearman ランク相関）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）の実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB で完結する実装。
  - research パッケージの __init__ で主要関数を再エクスポート。

Other
- OpenAI 関連の実装は直接的に openai.OpenAI クライアントを使用（model: gpt-4o-mini、JSON mode、temperature=0、timeout=30）。
- いくつかの内部ユーティリティ（_table_exists, _to_date, etc.）やログ出力を整備。
- テストしやすい設計: OpenAI 呼び出しポイントや内部関数をモック可能に実装。

Known limitations / Notes
- 外部依存: duckdb、openai（OpenAI SDK）、および J-Quants クライアント（kabusys.data.jquants_client を想定）に依存します。
- 本リリースは初期実装であり、以下の点は将来の改善対象:
  - 並列化やバッチ処理の最適化（特に OpenAI コールの並列実行）。
  - 詳細な入力検証・型注釈の一貫性チェック。
  - 大規模データでのパフォーマンスチューニング。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY
  - その他: DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

Security
- 特記事項なし（初期実装）。環境変数の取り扱いは protected set による上書き保護を実装。

Deprecated
- なし

Removed
- なし

Fixed
- 初期リリースのため "Fixed" 記録なし。ただしフェイルセーフやリトライ戦略を組み込んで運用上の堅牢性を高めています。

---

補足:
- 個々の関数・モジュールの詳細な利用方法（引数・返り値・例外仕様）は各モジュールの docstring を参照してください。README や API リファレンスを整備することで、導入・運用が容易になります。