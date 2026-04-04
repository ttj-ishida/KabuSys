# CHANGELOG

すべての非互換性のある変更はメジャー番号を上げて記載します。  
このプロジェクトは Keep a Changelog の慣習に従って記録されています。

全てのリリースは semantic versioning に従います。

## [Unreleased]

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買プラットフォームのコアライブラリ群を追加しました。以下は実装された主な機能・設計方針・注意点の概要です。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化とバージョン情報を追加（__version__ = 0.1.0）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env のパース機能を実装（export 形式対応、シングル／ダブルクォート内のエスケープ処理、インラインコメント判定ロジック等）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / データベース / 監視 / システム設定などのプロパティを環境変数から取得。
    - 必須値取得時は未設定だと ValueError を送出する (_require)。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の値検証を実装。
    - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）、PID / Kill-flag パス、閾値（CPU/MEM/DISK）などをデフォルト値付きで提供。

- AI ニュース解析 (kabusys.ai.news_nlp)
  - raw_news / news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON mode）でセンチメント分析して ai_scores テーブルへ書き込む機能を追加。
  - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）を正確に計算する calc_news_window を実装。
  - バッチ処理（1 コール最大 20 銘柄）・記事数 / 文字数のトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
  - API 呼び出しのリトライ（429・ネットワーク切断・タイムアウト・5xx）と指数バックオフを実装。
  - レスポンスの堅牢な検証ロジック（JSON 抽出、results 配列検証、コード正規化、数値チェック、±1.0 のクリップ）を実装。
  - 部分失敗耐性のため、書き込みは対象コードのみを DELETE → INSERT（トランザクション）で置換。

- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込むロジックを実装。
  - OpenAI 呼び出し（gpt-4o-mini, JSON mode）は独立実装。記事無しや API エラー時は macro_sentiment=0.0 のフェイルセーフ。
  - DuckDB クエリはルックアヘッドを防止するため target_date 未満のデータのみを参照する設計。
  - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とエラーハンドリング（ROLLBACK と警告ログ）を実装。

- リサーチ（ファクター計算・特徴量探索） (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離などのモメンタム指標を計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials を参照して PER（EPS が 0 または欠損時は None）、ROE を計算。
    - DuckDB を用いた SQL ベースの計算でルックアヘッドの防止とデータ不足時の None 値処理を徹底。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21] 営業日）を一度のクエリで取得する実装。
    - calc_ic: Spearman（ランク相関）による IC 計算（結合・欠損処理・最小サンプル数のチェック）。
    - rank: 平均ランク（同順位は平均ランク）を返すユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出する統計要約。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を元に営業日判定（is_trading_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ判定（is_sq_day）を提供。
    - DB 登録が無い日には曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants API から差分取得・バックフィル・健全性検査（未来日チェック）・冪等保存を行う。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。ETL のメタ情報（取得数、保存数、品質問題、エラー一覧）を格納。
    - ETL パイプライン設計に準拠した差分フェッチ、保存（idempotent）、品質チェック（quality モジュール連携）を想定した基盤を追加。
  - jquants_client による外部 API 通信部分はデータモジュールから呼び出す設計（実装は別モジュール想定）。

- テスト性・堅牢性
  - OpenAI 呼び出し箇所は内部の _call_openai_api を経由しており、テスト時に差し替え可能（unittest.mock.patch でモック化容易）。
  - DuckDB の executemany で空リストを渡せない制約を考慮した実装（空チェックを行う）。
  - ログ出力を多用し、失敗時は例外を抑えてフェイルセーフで継続する箇所を明確化。

### 変更 (Changed)
- 初版のため変更履歴はありません（将来のリリースで記載予定）。

### 修正 (Fixed)
- 初版のため修正履歴はありません（将来のリリースで記載予定）。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI API キーは明示的に引数（api_key）で注入可能。未設定時は環境変数 OPENAI_API_KEY を使用。未設定の場合は ValueError を発生させ安全策を講じる。
- .env 自動ロード機能は環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注記（運用・開発者向け）
- ルックアヘッドバイアス回避: AI・リサーチ関連の関数は datetime.today()/date.today() を参照せず、必ず caller が target_date を渡す設計です。テストやバッチ運用時は target_date を明示してください。
- OpenAI とのやり取りは gpt-4o-mini と JSON Mode を想定したプロンプト／レスポンスパーサを用いています。API レスポンスの変動（余分な前後テキスト等）に対応するため冗長なパースロジックを実装していますが、将来的に SDK の挙動変更があれば調整が必要です。
- DuckDB のバージョン互換性に注意（executemany の空リストなど既知の挙動を考慮していますが、DB バージョンが変わると微調整が発生する可能性があります）。

もしリリースノートに追記や修正したい点があれば、対象の機能・ファイルを指定して指示してください。