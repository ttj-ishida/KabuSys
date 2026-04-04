# CHANGELOG

すべての注目すべき変更点をここに記載します。本ファイルは Keep a Changelog の形式に従っています。

なお、本CHANGELOGは与えられたコードベースから仕様・実装を推測してまとめたものであり、実際のリリースノート作成時は実装者による確認を推奨します。

## [Unreleased]
（現時点での未リリースの変更はありません）

## [0.1.0] - 2026-04-04
初回公開リリース

### Added
- パッケージ基本情報
  - kabusys パッケージの初期バージョン（__version__ = "0.1.0"）。

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env のパース機能を強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメントの扱い（クォートの有無に応じたコメント判定）。
  - 環境設定を取得する Settings クラスを提供（settings インスタンスを公開）。
    - J-Quants / kabu API / LINE / DB（DuckDB/SQLite）/監視関連/システム（env/log_level）等のプロパティを用意。
    - 必須環境変数未設定時は ValueError を発生させる _require 関数を利用。
    - env 値の検証（development / paper_trading / live のみ許可、LOG_LEVEL の値検証等）。
    - Path 型での既定パス（例: DUCKDB_PATH, PID_FILE_PATH 等）をサポート。

- AI モジュール（kabusys.ai）
  - ニュース中心の NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメント評価を実施。
    - 時間ウィンドウ（JST 基準、前日 15:00 ～ 当日 08:30 = UTC で前日 06:00 ～ 23:30）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（1リクエスト最大 20 銘柄）、1銘柄あたり記事数 / 文字数制限（デフォルト: 最大10件・3000文字）を実装してトークン肥大化を防止。
    - JSON Mode を想定した堅牢なレスポンスバリデーション（JSON 抽出、results 配列検証、コード照合、数値検証）を実装。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ処理を実装。
    - 部分失敗を考慮した DB 書き込み（取得済みコードのみ DELETE → INSERT）により既存スコア保護。
    - テスト容易性のため OpenAI 呼び出し関数（_call_openai_api）を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を計算、raw_news からマクロキーワード一致タイトルを取得し LLM（gpt-4o-mini）で macro_sentiment を算出。
    - レジームスコアは clip で -1～1 に制限ししきい値でラベル付け（デフォルト閾値 BULL/BEAR = 0.2）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。API失敗時は macro_sentiment = 0.0 で継続（フェイルセーフ）。
    - OpenAI 呼び出しは news_nlp と独立した実装にしてモジュール間結合を避ける設計。

- データ処理 / ETL（kabusys.data）
  - ETL の公開インターフェースとして ETLResult を提供（kabusys.data.etl 再エクスポート）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックを組み合わせた ETLResult データクラスを実装。
    - 保存件数・取得件数・品質チェック問題・エラー情報を保持し、has_errors / has_quality_errors プロパティを提供。
    - DuckDB に対するテーブル存在チェックや最大日付取得など ETL 補助ユーティリティを実装。
    - 設計上、id_token 等を引数で注入でき、テスト容易性を考慮。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを参照して営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB にデータが無い場合は曜日ベースのフォールバック（土日非営業）を返す一貫した挙動。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等的に保存（バックフィルや健全性チェック含む）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev を計算（DuckDB SQLベース、データ不足時 None を返す）。
    - Volatility: 20 日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - 各関数は prices_daily / raw_financials のみを参照し、本番発注等にはアクセスしない方針。
  - feature_exploration モジュール
    - 将来リターン計算 calc_forward_returns（デフォルト horizons = [1,5,21]）を提供。horizons の妥当性チェックあり。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ を実装、有効レコード 3 件未満で None を返す）。
    - rank（同順位は平均ランク）と factor_summary（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティとして kabusys.data.stats.zscore_normalize を再利用可能にエクスポート。

### Design & Implementation Notes
- ルックアヘッドバイアス対策
  - 各種処理で datetime.today()/date.today() を使用せず、外部から与えられる target_date を基準に処理する設計。
  - DB クエリでは date < target_date / date BETWEEN ... 等の排他条件を用いてルックアヘッドを防止。

- 信頼性・堅牢性
  - OpenAI API 呼び出しに対する細かな例外ハンドリング（429, ネットワーク, タイムアウト, 5xx）と指数バックオフを実装。
  - API レスポンスのパース失敗時は例外を投げずフェイルセーフで処理を継続（必要に応じて 0.0 や空スコアで代替）。
  - DuckDB への executemany に関する互換性（空リスト不可）を考慮した実装。
  - DB 書き込みは冪等操作（DELETE→INSERT/ON CONFLICT）を基本とし、部分失敗時に既存データを過度に消さない設計。

- テスト容易性
  - API キー注入や _call_openai_api の patch が可能な構造にしてユニットテストを容易に実行できるよう配慮。

### Fixed
- 特になし（初回リリース）

### Changed
- 特になし（初回リリース）

### Removed
- 特になし（初回リリース）

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）から解決。未設定時は ValueError を発生させることで誤動作を防止。

---

補足:
- この CHANGELOG はコードから仕様や実装意図を推測して作成しています。実際のリリースノートには変更履歴管理ポリシー（コミット単位／チケット単位）に従い、さらに詳細な差分（影響範囲、互換性、移行手順、例）を追記してください。