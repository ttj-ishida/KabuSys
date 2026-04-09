# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0（初版） — 2026-04-09

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買・データ基盤・リサーチ・AI支援機能の骨格を提供します。

### 追加
- パッケージ基本情報
  - kabusys パッケージを追加。バージョン: 0.1.0。
  - パッケージ公開API: data, strategy, execution, monitoring（__all__ にて公開）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から自動的に設定を読み込む実装を追加。
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
  - .env パーサ実装: export プレフィックス対応、クォート・エスケープ処理、インラインコメント処理など。
  - 環境変数取得ユーティリティ Settings クラスを追加（settings でインスタンスを公開）。
    - J-Quants / kabu ステーション / LINE API / DB パス / Paper Trading 関連などのプロパティを用意。
    - バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG..CRITICAL）、PAPER_FILL_MODE（instant/partial/never/reject）等の値検査。
    - デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db", PAPER_TRADING_SQLITE_PATH="data/paper_trading.db" 等。

- データ基盤（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジックを追加。
    - market_calendar テーブル利用時は DB 値優先、未登録日は曜日ベースでフォールバック（週末は休場）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティを提供。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得して冪等保存、バックフィル・健全性チェックあり）。
  - etl / pipeline
    - ETLResult データクラスを追加（差分取得・保存件数・品質チェック結果・エラー情報を保持）。
    - ETL 処理の設計方針・設定（最小データ日・バックフィル・カレンダー先読み等）を含むパイプライン基盤を実装。
  - jquants_client など外部クライアント層との連携を想定（コード中で参照）。

- AI（kabusys.ai）
  - news_nlp
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出。
    - 機能:
      - ニュース集約窓: 前日 15:00 JST ～ 当日 08:30 JST（UTC 換算で前日 06:00 ～ 23:30）。
      - 銘柄ごとに最新 max 記事数・文字数でトリムしてプロンプト作成。
      - バッチ処理（_BATCH_SIZE=20）で API 呼び出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - レスポンスバリデーション（JSON パース復元、results 配列・code/score 検査、数値チェック）、スコアを ±1.0 にクリップ。
      - 成功した銘柄のみ ai_scores テーブルへ置換保存（部分失敗時に既存データを保護するため、DELETE→INSERT を銘柄単位で実施）。
    - テストしやすさを考慮し、OpenAI 呼び出し箇所は関数化してモック差し替えが可能。
  - regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来マクロセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を追加。
    - ワークフロー:
      - ma200_ratio 計算（target_date 未満のみ使用、データ不足時は中立扱い）。
      - raw_news からマクロキーワードによるフィルタで記事タイトル抽出（最大件数制限）。
      - OpenAI でマクロセンチメント評価（記事なし時は LLM 呼び出しをスキップし 0.0 を採用、API 失敗時も 0.0 にフォールバック）。
      - 合成スコアをクリップしてラベル付け、DB へトランザクションで書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - API 呼び出しリトライ・エラー分岐、テスト用モック差し替えを想定した設計。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER, ROE）等のファクター計算関数を追加。
    - DuckDB を用いた SQL + Python 実装で prices_daily / raw_financials のみを参照する安全設計。
    - データ不足時の None 扱い等、堅牢性に配慮。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、内部で LEAD を使用）、IC（情報係数）計算（スピアマンのランク相関）、rank、factor_summary（count/mean/std/min/max/median）などを追加。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。
  - research パッケージ __all__ に主要関数をエクスポート。

### 変更
- （初版のため過去からの変更はありません）

### 修正
- （初版のため過去からの修正はありません）

### 既知の仕様・設計上の注意（重要）
- ルックアヘッドバイアス防止:
  - AI / リサーチ関連モジュールは datetime.today() / date.today() に依存せず、明示的に与えた target_date を基準に処理します。
  - DB クエリは target_date 未満や半開区間でデータを取得することで将来情報の混入を防ぎます。
- OpenAI API の利用:
  - デフォルトモデルは gpt-4o-mini。API キーは api_key 引数または環境変数 OPENAI_API_KEY から取得。
  - API 呼び出しはリトライやフェイルセーフを備えるが、API 未設定時は ValueError を raise します。
- DuckDB 互換性:
  - DuckDB の executemany の空リストバインド制約（0.10 系）に配慮したガードを実装している箇所あり。
- 環境ファイルのパースはシェル互換の簡易処理を行うが、極端に特殊な .env 構文は想定外の扱いになる可能性があります。

### 互換性の破壊（Breaking Changes）
- なし（初回リリース）

### セキュリティ
- OpenAI API キーや外部サービスのトークンは環境変数経由で取り扱う設計です。運用時は権限管理に注意してください。

---

今後の予定（例）
- strategy / execution / monitoring の具象実装（発注ロジック・プロセスマネージャ・監視アラート）。
- 単体テストと統合テストの拡充、CI ワークフロー整備。
- ドキュメント（使用方法、運用ガイド、DB スキーマ）の拡充。

（必要があれば、各関数の利用例や環境変数一覧、マイグレーション手順を別途追記します）