# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加
- パッケージのエントリポイントを追加
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - 公開サブモジュールとして data, strategy, execution, monitoring を想定（__all__ に定義）。

- 環境設定管理
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索して自動ロード（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。`.env.local` は上書き可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env パース実装は export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの扱いに対応。
    - 環境変数必須チェック用の _require() と Settings クラスを提供。主要設定:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
      - KABUSYS_ENV（development/paper_trading/live の検証）
      - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - Settings に利便性プロパティ: is_live / is_paper / is_dev。

- ニュース NLP（AI）モジュール
  - ai パッケージ公開（src/kabusys/ai/__init__.py）。
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントスコアを算出して ai_scores テーブルへ書き込む。
    - 時間ウィンドウ: JST 基準で「前日 15:00 ～ 当日 08:30」（内部は UTC naive datetime に変換）を対象。
    - API 呼び出しは銘柄を最大 20 件／チャンクでバッチ送信（_BATCH_SIZE=20）。
    - 1銘柄あたり最大 10 記事、最大 3000 文字でトリム（トークン肥大対策）。
    - レスポンスは JSON mode を期待し、堅牢なバリデーション（JSON 抜き出し、results 配列、code/score 検証、スコアの数値性・有限性）を実施。
    - スコアは ±1.0 にクリップ。部分書き込み時に既存スコアを保護するため、該当コードのみ DELETE → INSERT の置換を実行。
    - リトライ方針: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数設定）。
    - API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp を用いたマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロ記事はニュースタイトルをフィルタ（日本・米国関連のマクロキーワード群）して上限 20 件取得。
    - LLM 呼び出しは独立実装で実行（news_nlp と内部実装を共有しない設計）。
    - API 呼び出し失敗やパースエラー時は macro_sentiment=0.0 としてフェイルセーフに継続。
    - 結果は market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で書き込み。
    - API キー注入のサポート（api_key 引数または OPENAI_API_KEY）。

- Data モジュール
  - data パッケージと ETL インターフェースを追加（src/kabusys/data/*）。
  - pipeline モジュール（src/kabusys/data/pipeline.py）
    - ETL の結果を表す ETLResult dataclass を提供（取得数・保存数・品質問題・エラー集約・ユーティリティ to_dict）。
    - 差分取得・バックフィル・品質チェックの方針を実装するためのユーティリティを準備（_get_max_date, _table_exists 等）。
    - デフォルトのバックフィル日数やカレンダー先読み設定を含む定数群を定義。
  - etl モジュールで ETLResult を再エクスポート（src/kabusys/data/etl.py）。
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定・検索ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にカレンダー情報がない場合の曜日ベースフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar への冪等保存（バックフィル・健全性チェックを含む）。
    - 最大探索日数やバックフィル日数等の安全パラメータを定義し無限ループ・異常値に備える。
    - J-Quants クライアント呼び出し点を想定（kabusys.data.jquants_client）。

- Research（リサーチ）モジュール
  - research パッケージの公開（src/kabusys/research/__init__.py）。
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M）、200 日移動平均乖離、ATR（20日）、20日平均売買代金・出来高比率等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上の SQL ウィンドウ関数を活用して効率的に計算。
    - データ不足時の None 扱いやログ出力を含む設計。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）を実装、少数の有効レコード時に None を返す。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を提供。
    - 外部依存（pandas 等）を用いず標準ライブラリのみで実装。

### 変更
- （初版につき過去の変更はなし）

### 修正
- （初版につき過去の修正はなし）

### 注意事項 / マイグレーション
- OpenAI API:
  - news_nlp/regime_detector は OpenAI（gpt-4o-mini）を想定。実行には OPENAI_API_KEY が必要（関数引数で注入可能）。
  - API 呼び出しはリトライ・バックオフを実装しているが、API レスポンスの不正時はスコアをゼロにフォールバックするなどフェイルセーフの振る舞いがあります。ロギングで警告が出力されます。
- 環境変数:
  - いくつかのキーは必須で、Settings プロパティを参照すると未設定時に ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
  - 自動 .env ロードはプロジェクトルートが検出できない場合スキップされます。CI/テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化してください。
- データベース:
  - 内部では DuckDB を想定（DuckDB の executemany の制約等を考慮した実装になっています）。DuckDB のバージョン差による挙動に注意してください。
- レークアヘッドバイアス対策:
  - 全ての AI / スコア計算関数は内部で datetime.today()/date.today() を直接参照しない設計です。必ず target_date を渡して使用してください。

### 既知の制約・設計上の決定
- LLM 呼び出し結果のバリデーションは厳密に行うが、LLM 側の不整合や API 障害時は「安全側」へフォールバックして処理を継続する設計（例外を投げずにスキップまたは 0.0 を返す箇所あり）。
- news_nlp と regime_detector はそれぞれ独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しないことで結合度を下げている。
- データ書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 想定）や部分置換を行い、部分失敗時に既存データを不必要に消さないようにしている。

今後の予定（例）
- strategy / execution / monitoring の実装拡充（実際の発注ロジック・監視機能の追加）。
- jquants_client 等外部クライアントの具体実装とテスト用モックの提供。
- CI / テストケース、型チェック、より詳細なドキュメントの追加。

--- 

その他、コード内ドキュメント（docstring）に詳細な設計意図・安全策が記載されています。実運用時は各モジュールの docstring を参照してください。