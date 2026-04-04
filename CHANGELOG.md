KEEP A CHANGELOG
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。
次の変更履歴は、パッケージ初版リリース (v0.1.0) における実装内容を
ソースコードから推測してまとめたものです。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更（該当なしの場合は省略）
- Fixed: バグ修正（該当なしの場合は省略）
- Security / Breaking: 破壊的変更やセキュリティに関する注意（該当があれば記載）

Unreleased
----------
（現時点のソースには未リリース分はありません）

[0.1.0] - 2026-04-04
-------------------
Added
- パッケージ初回公開。
- コアパッケージ名: kabusys、バージョン v0.1.0 を設定。
- パッケージ公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準として探索（CWD 非依存）。
  - .env パーサ実装:
    - コメント行、空行無視。
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内でのエスケープ処理に対応。
    - クォートなしの値でのインラインコメント判定（直前が空白/タブの場合はコメント扱い）。
  - 自動ロードの挙動:
    - 読み込み優先度: OS環境 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能（テスト等向け）。
    - OS側の既存環境変数を protected として上書き回避。
  - Settings クラスを提供（settings オブジェクトをエクスポート）:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等の必須値検査（未設定時は ValueError）。
    - KABU_API_BASE_URL、LINE 関連、データベースパス（DUCKDB_PATH, SQLITE_PATH）などのデフォルト値。
    - 監視関連ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）、閾値（CPU/MEM/DISK）等。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI モジュール (kabusys.ai)
  - news_nlp.py: ニュースの NLP（センチメント）スコアリング機能を実装。
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB クエリ。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（トークン肥大化対策）。
    - バッチ送信: 最大 20 銘柄 / チャンクで OpenAI (gpt-4o-mini) に JSON mode で送信。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" 配列、各 item の code/score 型検査、スコアは ±1.0 にクリップ。
    - 書き込み処理: スコアを取得できた銘柄のみ DELETE → INSERT（部分失敗で他銘柄の既存スコアを保護）。
    - DuckDB の executemany の互換性問題（空リスト不可）を考慮したガード。
    - API キーは引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。未指定時は ValueError。
    - date.today()/datetime.today() を使用せず、lookahead バイアスを防止する設計。

  - regime_detector.py: 市場レジーム判定機能を実装。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロニュースの LLM センチメント（重み 30%）を合成して日次で判定。
    - マクロキーワードで raw_news タイトルを抽出し、OpenAI に JSON 出力でセンチメント評価を依頼。
    - LLM の失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア合成後、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しは内部的に OpenAI SDK (OpenAI) を使用し、最大リトライ・指数バックオフ等を適用。
    - OpenAI レスポンスのパースに失敗する場合は安全に 0.0 を返し、例外を上げない設計。
    - API キーは引数優先、未指定なら環境変数 OPENAI_API_KEY を参照。

- Research モジュール (kabusys.research)
  - factor_research.py:
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。データ不足時は None を返す。
    - ボラティリティ/流動性: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率など。
    - バリュー: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損なら None）。
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装。
    - 出力は (date, code) をキーとする dict のリスト。
    - 設計上、本番の発注 API 等にはアクセスしない（読み取り専用）。
  - feature_exploration.py:
    - 将来リターン calc_forward_returns（任意 horizon 対応、入力検証あり）。
    - IC（Information Coefficient） calc_ic：Spearman（ランク相関）を内部実装で算出。
    - rank/util: 同順位は平均ランクを使う。丸め処理で ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を計算。

- Data モジュール (kabusys.data)
  - calendar_management.py:
    - JPX カレンダーの管理ロジック（market_calendar）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にカレンダー情報がない場合は曜日ベース（週末除外）でフォールバック。
    - next/prev/get_trading_days は DB 登録を優先し、未登録日は曜日フォールバックで一貫した結果を提供。
    - 最大探索日数の上限を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants クライアントを通じた差分取得・保存処理を実装（バックフィル/健全性チェック含む）。
    - jquants_client との連携を想定（fetch/save 関数呼び出し）。API エラー時にログ出力して 0 を返すフェイルセーフ。

  - pipeline.py / etl.py:
    - ETLResult dataclass を実装（取得件数・保存件数・品質問題リスト・エラーリスト等を保持）。
    - ETLResult.to_dict() により quality_issues を辞書化して出力可能。
    - データ差分取得、品質チェック（kabusys.data.quality）を含める設計方針を明記。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- データベース/DB 操作における安全対策
  - DuckDB を前提とした実装で、トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた冪等書き込みを行う箇所が多数存在。
  - ROLLBACK に失敗した場合は警告ログを出力して上位へ例外を伝播。
  - executemany の空リスト制約（DuckDB 0.10）に対するガードを導入。

- Logging / Observability
  - 重要イベントやフェイルセーフに関して詳細な logger 情報を出力する設計（info/warning/exception）。
  - 設定で LOG_LEVEL を検証し、無効な値は ValueError を発生させる。

Security / Breaking
- 環境変数に必須の機密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）があるため、
  運用時は適切に設定・管理すること（Settings._require により未設定時は ValueError）。.env.example に従うことを推奨。

Notes / Implementation details
- LLM 呼び出しについて:
  - OpenAI の Chat Completions を JSON mode（response_format={"type": "json_object"}）で利用する設計。
  - レスポンスが厳密な JSON でない場合の復元ロジック（文字列から最外の {} を抽出して再パース）を実装。
  - API 通信失敗時はリトライ & フォールバックで堅牢に動作（例外を無闇に上げない方針）。
- 時間ウィンドウ・日付扱い:
  - 全関数でルックアヘッドバイアスを避けるため datetime.today()/date.today() の直接参照を避ける設計。ただし calendar_update_job は実運用でのスケジュール実行のため date.today() を使用。
  - JST/UTC の変換ロジックについて明示（ニュース集計ウィンドウ等）。

Removed / Deprecated
- なし（初回リリース）

今後の検討点（コード上からの示唆）
- ai モジュールの OpenAI クライアント抽象化（テスト差し替えの利便性向上）。
- news_nlp のスコア／出力仕様拡張（PBR など他バリューファクターの追加）。
- calendar_update_job / ETL のより細かいエラー分類と再試行戦略。

参考: 主な環境変数名（Settings で参照されるもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (必須 for AI functions)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

---
この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する際は、実装者・リリース担当の確認を推奨します。