CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠しています。
安定版リリースや互換性の扱いはセマンティックバージョニングに従います（MAJOR.MINOR.PATCH）。

Unreleased
----------

- （現時点のコードベースからは未リリースの変更はありません）

0.1.0 - 2026-03-31
------------------

初回公開リリース。日本株自動売買／データ解析プラットフォーム「kabusys」の基本コンポーネントを実装しました。

Added
- パッケージ基礎
  - kabusys パッケージ初期化（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - パブリック名前空間に data, strategy, execution, monitoring を公開予定のトップレベルモジュールとして定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定読み込みを実装。
  - 自動 .env ロード機能（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装: export プレフィックス、クォート文字列、エスケープ、インラインコメント扱い等に対応。
  - Settings クラス経由で設定を型付けして取得可能に:
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - その他: KABU_API_BASE_URL（デフォルト localhost）、DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH
    - 監視閾値: CPU/MEM/DISK の閾値（数値、デフォルト値あり）
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）に対するバリデーション（許容値の定義）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols テーブルから記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）で銘柄ごとに -1.0〜1.0 のスコアを取得。
    - タイムウィンドウ: 前日15:00 JST〜当日08:30 JST（UTC 変換済み）を明確に定義し、ルックアヘッドを防止。
    - バッチ処理（最大20銘柄／リクエスト）、記事数・文字数トリム、JSON レスポンスバリデーション実装。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ。部分失敗時も他銘柄のスコアを保護するため書き込みは対象コードに限定。
    - テスト容易性のため API 呼び出し関数が差し替え可能（unittest.mock.patch 想定）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で regime ('bull'/'neutral'/'bear') を判定し market_regime テーブルへ書き込み。
    - ma200 計算は target_date 未満のみを参照（ルックアヘッド防止）。
    - マクロニュースの抽出キーワード定義、OpenAI 呼び出し、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - 出力は regime_score のクリップ・閾値判定、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

- データプラットフォーム関連（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 優先、未登録日は曜日（週末）ベースのフォールバック。最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - calendar_update_job 実装: J-Quants から差分取得 → 冪等保存、バックフィル処理、健全性チェック。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（取得数・保存数・品質情報・エラー等を含む）。
    - 差分取得、保存（jquants_client 経由）、品質チェックのワークフローを実装するための基盤。
    - jquants_client、quality モジュールとの連携設計（実装は参照）。
    - etl.py で ETLResult を再エクスポート。

- リサーチ / ファクター（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB 上の prices_daily / raw_financials を参照して計算。
    - データ不足時の None 扱い、営業日ベースでのラグ/移動平均処理、結果は (date, code) ベースの dict リストで返却。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman のランク相関）計算（calc_ic）、ランク変換、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。
  - research パッケージの __init__ で主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から参照）。

Changed
- （初回リリースにつき過去からの変更はありません）

Fixed
- （初回リリースにつき過去からの修正はありません）

Security
- OpenAI の API キーは関数引数で注入可能。環境変数 OPENAI_API_KEY を利用する場合は Settings /個別関数での明示的なチェックを行い、未設定時には ValueError を発生させる設計（誤った無効化を防止）。

Notes（実装上の設計上の注意／既知の挙動）
- ルックアヘッドバイアス対策として、AI モジュールおよびその他の算出ロジックは datetime.today() / date.today() を内部ロジックで直接参照せず、必ず caller が target_date を渡す設計になっています。
- OpenAI 呼び出しに対する堅牢性: リトライ、5xx 判定、JSON パース失敗時のフォールバック（スコア 0.0／空結果）を採用し、処理が全面停止しないようにしています。
- DuckDB の executemany の互換性を考慮した実装（空パラメータの事前チェックなど）を取り入れています。
- テスト容易性のため、各モジュールの外部 API 呼び出し部分（OpenAI 呼び出し等）は単体テストで差し替え可能な設計です（内部関数を patch して挙動を制御可能）。

Backward Incompatible Changes
- 0.1.0 は初回リリースのため該当なし。

参考（環境変数の一覧）
- 必須（呼び出し環境で設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- 任意 / デフォルトあり
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
  - OPENAI_API_KEY（API 呼び出し関数で引数として上書き可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD（1 で自動 .env 読み込みを無効化）

感想 / 今後の予定（推測）
- strategy / execution / monitoring の具象実装（実行ロジック、発注連携、監視アラート送信など）が今後追加される想定。
- jquants_client や quality モジュールの実実装、および integration テストを経て安定化が進む見込み。

--- 
（以上）