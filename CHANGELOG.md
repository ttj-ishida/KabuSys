# Changelog

すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
慣例: まずは新機能（Added）、そのほかの変更（Changed）、修正（Fixed）等を列挙します。

## [0.1.0] - 2026-04-04

### Added
- パッケージ骨格を追加
  - src/kabusys/__init__.py にてパッケージ名とバージョンを定義（__version__ = "0.1.0"）。公開サブパッケージ: data, strategy, execution, monitoring。

- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env ファイルの堅牢なパース実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント条件の扱い等）。
  - .env の読み込みは OS 環境変数を保護する仕組み（protected set）を採用。読み込み失敗時は警告を出力。
  - Settings クラスを提供。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須、未設定時は ValueError を送出）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE チャネル設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）
    - DB パス（DUCKDB_PATH, SQLITE_PATH）および監視関連設定（PID/KILL フラグ、閾値等）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値外は ValueError）
    - is_live / is_paper / is_dev ヘルパー

- ニュース NLP（AI）スコアリングを追加（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を対象に、指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST を UTC に変換）で記事を集計・銘柄毎にまとめて OpenAI（gpt-4o-mini）へ送信。
  - 1 銘柄あたりの最大記事数 / 最大文字数トリム、バッチ処理（最大20銘柄/コール）を実装。
  - OpenAI 呼び出しは JSON Mode を使用し、レスポンス検証（results 配列、code/score の検査、数値性確認、スコア ±1.0 クリップ）を実施。
  - 429 やネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。非再試行のエラーはスキップしてフェイルセーフに継続。
  - スコアは ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に他コードを保護。DuckDB の executemany に空リストを渡さないガードを追加。
  - テスト容易性のため、内部の OpenAI 呼び出し関数を patch できる設計。

- 市場レジーム判定モジュールを追加（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
  - prices_daily / raw_news を参照して値を計算し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書込失敗時はロールバックを試行して例外を伝播。
  - マクロキーワードによるニュース抽出、OpenAI 呼び出し（gpt-4o-mini）用のプロンプト、API 再試行・エラーハンドリング、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - テスト用に OpenAI 呼び出しを差し替え可能。

- リサーチ（因子計算・特徴量探索）モジュールを追加（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（200 日移動平均）を計算。データ不足時の挙動を明記（None / 警告）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮した設計。
    - calc_value: raw_financials から最新財務（report_date <= target_date）を取得し PER / ROE を計算。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得。horizons の検証（1..252）と SQL による効率的取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。十分な有効レコード（>=3）を要する旨を明示。
    - rank / factor_summary: 同順位の平均ランク処理、基本統計量（count/mean/std/min/max/median）を計算。
  - すべて DuckDB を用いた SQL + Python 実装で、外部 API への依存はなし。出力は (date, code) をキーとする dict のリスト。

- データ基盤モジュールを追加（src/kabusys/data/*）
  - calendar_management.py:
    - market_calendar テーブルに基づく営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB 登録値を優先し、未登録日は曜日ベースでフォールバック。
    - calendar_update_job: J-Quants からの差分取得・バックフィル・健全性チェック（未来日付上限）・保存処理を実装（jquants_client を利用）。
  - pipeline.py / etl.py:
    - ETLResult データクラスを定義（ターゲット日、取得/保存件数、品質問題、エラー一覧など）。
    - ETL パイプライン設計方針（差分更新、backfill、品質チェックの扱い、id_token 注入可能性）を実装予定のインターフェースとして記述。
    - etl.py で ETLResult を再エクスポート。

- 共通・運用設計上の注意点（全体）
  - ルックアヘッドバイアス防止のため、内部実装で datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主要なローカル DB として想定し、SQL と Python を組み合わせて処理を実装。
  - IDempotent な DB 書き込み（DELETE → INSERT、ON CONFLICT 処理、BEGIN/COMMIT/ROLLBACK の利用）を心がけ、部分失敗時の保護を実装。
  - OpenAI 呼び出しに関しては、モジュール間でプライベート呼び出しを共有せず各モジュールで独自実装（テストの分離性確保）。
  - 詳細なログ出力（info/debug/warning）を各処理に追加。

### Changed
- 該当なし（初期リリース）。

### Fixed
- 該当なし（初期リリース）。ただし各モジュールでエラー時のフォールバックやログ出力を追加し、堅牢性を高めている。

### Removed
- 該当なし。

### Security
- 該当なし。

---

備考:
- 各 AI モジュールは OpenAI API キー（引数または環境変数 OPENAI_API_KEY）を必要とし、未設定時は ValueError を送出します。テスト時は内部 API 呼び出し関数をモック可能です。
- DuckDB のバージョン依存（executemany の空リスト不可等）への対応や、API レスポンスの多様性（JSON モードでも余計なテキストが混入する可能性）に対する耐性を組み込んでいます。