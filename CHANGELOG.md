Keep a Changelog
================

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

フォーマットのバージョン: 1.0.0

Unreleased
----------

（作業中の変更点はここに記載してください）

0.1.0 - 2026-03-31
------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを追加。
  - パッケージエントリポイント: kabusys.__version__ = "0.1.0"、公開サブパッケージ: data, research, ai, monitoring 等。
- 環境設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動ロード。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーで以下に対応:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式
    - シングル・ダブルクォートされた値のバックスラッシュエスケープ処理
    - クォートなし値のインラインコメント処理（'#' の直前が空白/タブの場合にコメントと判定）
  - 環境変数の保護（OS 環境変数を protected 集合として扱い .env.local による上書きを制御）
  - Settings クラスによる設定参照とバリデーション:
    - 必須トークン: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）でセンチメントを取得。
    - バッチサイズ・最大トークン対策（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - JSON Mode 出力のバリデーション・パース耐性（余分な前後テキストから最外の {} を抽出する等）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch が想定）。
    - ルックアヘッドバイアス防止（datetime.today() を参照しない、タイムウィンドウは calc_news_window で明示）。
  - regime_detector.score_regime
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウ抽出、OpenAI（gpt-4o-mini）で JSON 出力を期待。
    - API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - API 呼び出しのリトライ・エラーハンドリングを実装。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）用 API 連携処理の夜間バッチ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にデータがない場合は曜日ベース（土日非営業日）でフォールバック。
    - カレンダー更新は差分取得・バックフィル（直近 _BACKFILL_DAYS 日）・健全性チェックを実施。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - 差分取得、保存（idempotent）、品質チェック（quality モジュール）を行う設計方針とユーティリティを実装。
    - テーブル存在チェック・最大日付取得等のユーティリティ実装。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を実装。
    - DuckDB 上の SQL を主体に安全に計算し、結果を list[dict] で返却。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。
    - 入力バリデーション（horizons の範囲チェック等）や欠損値処理を明確化。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数で注入可能（api_key 引数）か環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げることで誤動作を防止。

Notes / 設計上の重要点
- ルックアヘッドバイアス回避:
  - AI スコア算出やファクター計算で datetime.today()/date.today() を参照せず、呼び出し側が target_date を与える設計。
  - DB クエリでは target_date 未満／以前等の排他条件を明示。
- フェイルセーフ:
  - OpenAI や外部 API の一時的失敗時には例外で中断せずフェールバック（0.0）やスキップで継続する設計。
- テスト可能性:
  - OpenAI 呼び出し箇所はモック差し替えを想定した実装（内部 _call_openai_api を patch）。
  - API キーは引数で注入可能。
- DuckDB 互換性:
  - executemany に空リスト渡せないケースを考慮した分岐等、DuckDB の挙動に合わせた実装上の工夫あり。

Breaking Changes
- なし（初回リリース）

その他
- ロギングを適切に出力するように設計（処理状況・警告・例外時ログ）。必要に応じてログレベルは LOG_LEVEL 環境変数で制御。

今後の予定（例）
- AI モデルの選択肢の拡張やプロンプト最適化
- ETL の監視ダッシュボードとアラート統合
- 追加ファクター・アルファ研究の拡張

--- 
もし CHANGELOG に含めたい追加の変更点やリリース日付の修正があれば教えてください。