CHANGELOG
=========
このファイルは Keep a Changelog の形式に準拠しています。
全ての重要な変更をここに記録します。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 脱落 (Removed) 等

0.1.0 - 2026-03-28
------------------

Added
- 初回リリース: kabusys パッケージ (バージョン: 0.1.0) を追加。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に設定。

- 環境設定/ロード機能 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: 現在ファイル位置から .git または pyproject.toml を探索してプロジェクトルートを特定（CWD に依存しない）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート中のエスケープ処理、行内コメントの扱い等に対応する堅牢なパーサを実装。
  - 上書き制御: override / protected オプションにより OS 環境変数保護と上書き挙動を制御。
  - Settings クラスを提供（settings インスタンス経由で利用）。
    - J-Quants: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password（必須）、kabu_api_base_url（デフォルト http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - DBパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env (development|paper_trading|live 検証)、log_level 検証、is_live/is_paper/is_dev ヘルパー

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換して DB を参照）。
    - バッチ処理: 最大 20 銘柄/コール、1 銘柄あたり最大 10 記事・最大 3000 文字にトリム。
    - 再試行/バックオフ: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ実装（最大リトライ _MAX_RETRIES）。
    - レスポンス検証: JSON パース復元（前後余分テキストが混入した場合の {} 抽出）、構造チェック、未知コード無視、数値バリデーション、±1.0 クリップ。
    - DB 書き込み: ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。部分失敗でも既存スコアを保護するため code を限定。
    - テスト容易性: OpenAI 呼び出しは _call_openai_api を経由するためモック可能。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロ記事抽出は news_nlp.calc_news_window と共通ウィンドウを使用し、マクロキーワードでフィルタ。
    - LLM 呼び出しは OpenAI SDK（gpt-4o-mini）を使用、失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 冪等 DB 書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）。
    - テスト容易性: news_nlp と同様に内部 API 呼び出しを差し替えやすい実装。

- Data モジュール (kabusys.data)
  - calendar_management
    - market_calendar を用いた営業日判定/操作ユーティリティ群を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日非営業日）。
    - _MAX_SEARCH_DAYS による探索制限と安全策を実装。
    - calendar_update_job: J-Quants API クライアント経由で差分取得し market_calendar を冪等更新。バックフィル、健全性チェック（将来日付異常検出）を実装。
    - DuckDB 型変換ヘルパーやテーブル存在チェックを提供。

  - pipeline（kabusys.data.pipeline）
    - ETLResult データクラスを追加（ETL 実行結果の集約: 取得/保存件数・品質問題・エラー等）。
    - ETL 実行に関するユーティリティ: テーブル存在判定、最大日付取得、market_calendar 補正ヘルパーなど。J-Quants クライアントと quality チェック連携の設計を反映。
    - etl モジュールから ETLResult を再エクスポート（kabusys.data.etl）。

  - jquants_client と quality モジュールとの連携を想定した設計（fetch/save 関数を呼び出すフロー）。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比など流動性/ボラティリティ指標を計算。
    - calc_value: raw_financials から直近の財務データを取得し PER（EPS が 0/欠損なら None）と ROE を計算。PBR/配当利回りは未実装。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズン検証あり）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクを採るランク化ユーティリティ（round による ties の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリユーティリティ。
  - research.__init__.py で主要関数を再エクスポート。

Changed
- 設計方針・実装上の留意点をコードコメントとして明確化:
  - ルックアヘッドバイアスの排除（datetime.today()/date.today() を直接参照しない方針を各所で採用）。
  - DuckDB 0.10 の executemany 空リスト制約への対処（空パラメータは実行をスキップ）。
  - API 呼び出し失敗時のフォールバック（例: macro_sentiment=0.0、スコア取得失敗はスキップ）によるフェイルセーフ設計。
  - OpenAI 呼び出しのレスポンス検証や JSON 復元（前後余計なテキスト）を実装して堅牢性を強化。

Fixed
- （初回リリース）多くの既知リスクに対する防御的実装を導入:
  - .env パースのエスケープ/クォート/コメント処理を改善。
  - OpenAI API の 5xx / レート制限 / ネットワークエラーに対する再試行ロジックを実装。
  - DuckDB からの日付型取り扱い（文字列→date の変換）をユーティリティ化。

Known limitations / Notes
- 一部の機能は将来拡張予定:
  - factor_research.calc_value: PBR・配当利回りは未実装。
- OpenAI 呼び出しは gpt-4o-mini を想定している（API キーは引数または OPENAI_API_KEY 環境変数で供給）。
- jquants_client / quality モジュールの具体的実装はこの差分に含まれておらず、外部実装との連携を前提としている。
- calendar_update_job と pipeline の API 呼び出しは外部サービス依存のため、ネットワーク障害時は該当処理が 0 件返却するなどのフェイルセーフ動作をする。

参考
- この CHANGELOG はリポジトリのコードコンテンツから推測して作成しています。実際のリリースノート作成時には変更履歴やコミット単位の差分を反映してください。