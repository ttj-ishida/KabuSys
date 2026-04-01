CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

Unreleased
----------

- なし（初回リリース以降の未リリース変更はここに記載します）。

0.1.0 - 2026-03-31
-----------------

Added
- 初回公開リリース。
- パッケージ概要
  - kabusys: 日本株自動売買システムの基盤ライブラリ。
  - パッケージ配下に data, research, ai, research, （および将来的な strategy / execution / monitoring 用のエクスポートプレースホルダ）を用意。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装:
    - プロジェクトルート検出は __file__ から親ディレクトリを探索し .git または pyproject.toml を基準に行うため、CWD に依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメント判定（スペース直前の # をコメント扱い）などに対応。
  - Settings クラスを提供し、主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI モジュールで参照）などの必須チェック。
    - ログレベル・環境（development / paper_trading / live）のバリデーション。
    - デフォルトの DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）や監視しきい値等の既定値を定義。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを提供。取得件数、保存件数、品質問題、エラー一覧などを集約。
    - 差分更新・バックフィル・品質チェックを想定した設計。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定機能を提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等（上書き）保存する夜間バッチ処理を実装。バックフィルや健全性チェックを含む。
  - jquants_client 経由のデータ取得/保存を想定（fetch/save 関数呼び出し、例外ハンドリング）。

- ニュース NLP / AI（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合、LLM（gpt-4o-mini、JSON mode）へバッチ送信してセンチメントを算出。
    - タイムウィンドウ定義（JST 基準: 前日 15:00 〜 当日 08:30、内部は UTC naive datetime で扱う）。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数トリムを実装。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト検査、コード整合性、数値チェック）を行い、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ。
    - フェイルセーフ: API 失敗やパース失敗時は個別チャンクをスキップし処理継続。
    - テスト容易性: _call_openai_api のモック差し替えを前提に設計。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - マクロタイトル抽出（キーワードベース）→ LLM 評価（gpt-4o-mini JSON mode）→ スコア合成 → market_regime へ冪等書き込みを実装。
    - API 呼び出し失敗時は macro_sentiment=0.0 を使うフェイルセーフ。リトライと 5xx の判定を含む。
    - ルックアヘッドバイアス回避の設計（date < target_date 等）を厳守。
    - テスト容易性: news_nlp と独立した _call_openai_api 実装でモジュール結合を抑制。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research モジュール
    - モメンタム: mom_1m / mom_3m / mom_6m、ma200_dev（200 日 MA）を計算。データ不足時は None を返す。
    - ボラティリティ & 流動性: 20 日 ATR、相対 ATR（atr / close）、20 日平均売買代金、出来高比率を計算。
    - バリュー: raw_financials から最新財務を取得して PER（EPS が 0 または欠損時は None）と ROE を計算。
    - DuckDB の SQL を主体に実装し、prices_daily / raw_financials のみを参照。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）: 指定 horizon（例: 1,5,21 日）の LEAD を使った一括取得。
    - IC（calc_ic）: スピアマンランク相関の実装（ランクは同順位で平均ランク）。
    - rank, factor_summary: ランク変換と基本統計量（count/mean/std/min/max/median）を提供。
    - pandas 等に依存せず標準ライブラリ＋DuckDB で完結。

- DB とトランザクション
  - 各種書き込みは明示的な BEGIN / DELETE / INSERT / COMMIT（失敗時は ROLLBACK）で冪等に実装。
  - DuckDB を前提とした SQL 実装（executemany の空リスト扱いなど DuckDB バージョン特性に配慮）。

- ロギング / エラーハンドリング
  - 重要箇所での logger による情報・警告・例外ログ出力を充実。
  - 外部 API 呼び出し失敗時の明示的フォールバック（ゼロスコアやスキップ）設計を採用。

Notes / Usage
- OpenAI API を利用する関数（score_news, score_regime）は OPENAI_API_KEY の設定（引数または環境変数）を必須とする。未設定時は ValueError を送出する。
- 環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY, KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パス等は Settings クラスのプロパティで確認・上書き可能。

Changed
- なし（初回リリース）。

Fixed
- なし（初回リリース）。

Security
- なし（既知のセキュリティ修正はありません）。  
  注意: API キーやパスワード類は .env や環境変数で管理し、リポジトリに含めないでください。

以上。今後の変更は Unreleased セクションに記載し、バージョンを上げて本ファイルを更新してください。