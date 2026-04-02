# Changelog

すべての重要な変更はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

現在のバージョンはパッケージ内の __version__ に基づき 0.1.0 です。

## [0.1.0] - 2026-04-02

### 追加 (Added)
- 基本パッケージ構成
  - パッケージエントリポイントを追加。__version__ = 0.1.0、公開サブパッケージを __all__ で定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を探索して検出（CWD非依存）。
    - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は .env を上書き）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは以下に対応：
    - export KEY=val 形式、シングル/ダブルクォート（バックスラッシュエスケープ含む）、インラインコメントの扱い（クォート有無による差別化）。
  - OS 環境変数を保護する protected パラメータによる上書き制御。
  - Settings クラスを公開（settings）。必須値の取得時は未設定で ValueError を送出。
    - 必須項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルト値や型変換（duckdb/sqlite パスの Path 変換、しきい値は float）を実装。
    - KABUSYS_ENV と LOG_LEVEL の値検証を追加（許容値チェック）。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- ニュースNLP / AI (kabusys.ai)
  - ニュースセンチメント解析モジュールを追加（news_nlp.score_news）。
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得。
    - バッチサイズ、記事数・文字数制限、JSON Mode を用いた厳密なフォーマット、レスポンスのバリデーションを実装。
    - 再試行（429/ネットワーク/TIMEOUT/5xx）に対する指数バックオフを実装。部分失敗時でも他銘柄の既存スコアを消さない idempotent な DB 書き込み（DELETE → INSERT）を行う。
    - DuckDB の executemany に対する空リスト対策（空時は実行しない）。
    - レスポンスパース失敗時は警告ログを出し該当チャンクをスキップするフェイルセーフ設計。
    - calc_news_window(target_date) を提供（JST ベースのニュース集計ウィンドウを UTC naive datetime で返却）。
  - 市場レジーム判定モジュールを追加（regime_detector.score_regime）。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日ごとの市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算、マクロ記事抽出、OpenAI 呼び出し（独自 _call_openai_api 実装）、合成ロジック、閾値によるラベリング、market_regime テーブルへの冪等書き込みを実装。
    - OpenAI API の失敗時は macro_sentiment = 0.0 のフォールバックを採用（フェイルセーフ）。
    - API 呼び出しに対してリトライ・指数バックオフを実装。

- Data プラットフォーム（kabusys.data）
  - マーケットカレンダー管理モジュールを追加（calendar_management）。
    - market_calendar テーブルを前提とした営業日判定ユーティリティを提供：
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない/未登録日の場合は曜日ベース（土日非営業）でフォールバック。
    - カレンダー夜間更新ジョブ calendar_update_job を追加（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数の制限やバックフィル、未来日健全性チェックなどの安全策を実装。
  - ETL パイプラインインターフェースを追加（pipeline.ETLResult を etl モジュールで再エクスポート）。
  - ETL パイプライン（data.pipeline）を追加（差分更新 / 保存 / 品質チェック方針を実装）。
    - ETLResult dataclass を提供：各種取得数・保存数、品質問題リスト、エラー一覧、便利プロパティ（has_errors, has_quality_errors）、to_dict を実装。
    - 差分取得の既定動作（backfill_days の考慮、カレンダー先読みなど）に準拠。
    - 品質チェックでの重大度管理（severity に基づく has_quality_errors）を実装。

- リサーチ（kabusys.research）
  - ファクター計算・解析モジュールを追加。
    - factor_research: calc_momentum, calc_volatility, calc_value
      - Momentum：1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す）
      - Volatility：20日 ATR（平均）、相対 ATR、20日平均売買代金、出来高比率
      - Value：raw_financials から EPS/ROE を用いて PER/ROE を計算
    - feature_exploration: calc_forward_returns, calc_ic (Spearman rank), rank, factor_summary
      - 将来リターンをまとめて取得する高速 SQL 実装、horizons のバリデーション
      - IC 計算は rank を用いたスピアマン ρ の算出（データ不足時は None）
      - factor_summary は count/mean/std/min/max/median を算出
    - kabusys.research パッケージ __init__ で主要関数を再エクスポートし、zscore_normalize を data.stats から再利用できるように設定。

### 変更 (Changed)
- 設計上の方針と安全対策を明確化
  - すべての「日付基準」処理で datetime.today()/date.today() に依存しない実装を徹底し、ルックアヘッドバイアスを防止。
  - OpenAI 呼び出し部分は各モジュールで独立実装とし、モジュール間のプライベート関数共有を避けることで結合度を下げる設計。
  - DuckDB バインドの互換性問題（executemany に空リストを与えない）に対応。

### 修正 (Fixed)
- OpenAI レスポンスのパース耐性向上
  - JSON Mode でも前後に余計なテキストが混入する場合を想定し、最外の {} を抽出して復元するフォールバックを追加。
  - レスポンス構造（resultsキーや各要素の型）に異常がある場合は警告ログを出してそのチャンクをスキップするよう改善。
- API エラー処理強化
  - RateLimit / 接続エラー / タイムアウト / 5xx に対するリトライ・バックオフを標準化し、非再試行エラーは即スキップしてシステム全体の停止を防止。

### 注意事項 (Notes)
- 環境変数の必須項目（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）は未設定時に ValueError を送出します。README/.env.example を参照して設定してください。
- デフォルトの DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- OpenAI クライアント（gpt-4o-mini）利用部分は API キー注入が可能（api_key 引数または環境変数 OPENAI_API_KEY）。
- 一部モジュールは外部 jquants_client / quality モジュールへの依存を持ちます（実行時に利用可能である必要があります）。
- このリリースは初期機能群（データ収集・ETL、カレンダー管理、AI ベースのニュース解析とレジーム判定、研究用ファクター群）を提供することを目的としています。運用時は設定・APIキー・DB スキーマの準備を行ってください。

---

今後のリリースでは、テストカバレッジの拡充、モジュールの分割リファクタ、追加のファクタ/戦略実装、監視・運用機能の強化を予定しています。