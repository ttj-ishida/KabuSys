# CHANGELOG

すべての変更は Keep a Changelog に準拠しています。  
リリース日: 2026-03-29

## [0.1.0] - 2026-03-29

Added
- 初版リリース。KabuSys 日本株自動売買システムのコアライブラリを実装。
- パッケージ初期化:
  - src/kabusys/__init__.py にバージョン番号 __version__ = "0.1.0" と公開サブパッケージ定義を追加。
- 設定・環境変数管理:
  - src/kabusys/config.py
    - .env/.env.local ファイル自動読み込み機能（プロジェクトルートは .git または pyproject.toml で判定）。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントの扱いに対応した .env 解析ロジックを実装。
    - OS 環境変数を保護する protected モード、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 必須環境変数の取得ヘルパー _require、環境値検証（KABUSYS_ENV, LOG_LEVEL）および既定値、DB パスの既定値（DUCKDB_PATH, SQLITE_PATH）を提供。
    - 必要な環境変数（例）: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時に ValueError を発生）。
- AI（ニュース NLP / レジーム判定）:
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を対象にニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）にバッチ送信してセンチメントを算出。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、トリム（記事数・文字数上限）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行ロジックを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造検証、未知コード無視、数値変換、スコアクリップ）。
    - idempotent な DB 書き込み（DELETE → INSERT、トランザクション、ROLLBACK 保護）。テスト用に _call_openai_api をモックできる設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組合せて日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio 計算、マクロキーワードで記事抽出、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、重み合成、market_regime へ冪等書き込みを実施。
    - API エラー・パースエラー時は macro_sentiment=0.0 とするフェイルセーフ、リトライ／バックオフ、JSON パース耐性を実装。
- データプラットフォーム（Data）:
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理ロジック（market_calendar テーブルの利用、営業日判定、next/prev/get_trading_days、is_sq_day）を実装。
    - DB 登録がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。探索範囲上限設定で無限ループを防止。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants クライアントを用いた差分取得・バックフィル・保存処理を提供。
  - src/kabusys/data/pipeline.py / etl.py
    - ETL パイプラインの骨格を実装。差分取得、保存（idempotent）、品質チェック呼び出しのフロー設計を記載。
    - ETLResult データクラスを定義（取得/保存件数、品質問題リスト、エラー一覧、ヘルパー判定メソッド、辞書変換）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得、カレンダーヘルパー（取引日調整）等を実装。
    - etl.py で ETLResult を公開再エクスポート。
  - src/kabusys/data/calendar_management.py / pipeline.py に jquants_client 連携ポイントを確保（API 呼び出しは別モジュールで注入可能）。
- リサーチ（Research）:
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上で SQL で計算。
    - 必要データ不足時は None を返す挙動、結果は (date, code) キーの dict リストを返す仕様。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、rank 関数（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存を避け、標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py で主要関数を公開（zscore_normalize は data.stats から）。
- その他実装上の方針・利便性:
  - ルックアヘッドバイアス防止: datetime.today()/date.today() をスコアリング関数内部で直接参照しない設計（target_date を明示的に受け取る）。
  - DuckDB を主なデータストアとして想定し、SQL と Python を組合せた実装。
  - トランザクション制御（BEGIN/DELETE/INSERT/COMMIT）とロールバック保護による冪等保存を徹底。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとクリッピングを行う。
  - テスト容易性を考慮し、OpenAI 呼び出し内部関数をパッチ差し替え可能に設計。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 環境変数の取り扱いは慎重に設計（例: OS 環境変数を保護する protected セット、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込みの無効化）し、誤上書きを防止。

注意事項（ユーザ向け）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（OpenAI キーは news/regime スコアリングで必要）。
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env/.env.local を自動読み込みします。
  - OS 環境変数を上書きしたくない場合デフォルトで保護されます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 周り:
  - レート制限や一時エラーは再試行（指数バックオフ）されますが、再試行全消費時はフェイルセーフとして中立スコア（0.0）やスキップを行います。
  - テストでは内部の _call_openai_api をパッチして外部 API をモックできます。
- データベース:
  - デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite は data/monitoring.db。必要に応じて環境変数で変更可能です。
- 互換性:
  - 現バージョンは初版リリースのため、今後のマイナー/メジャー変更で API や挙動が変わる可能性があります。外部に依存する挙動（OpenAI/J-Quants API の戻りや DuckDB バインディングの挙動）に起因する影響に留意してください。

今後の予定（予定・注目ポイント）
- AI スコアのモデル運用改善（モデル切替やプロンプト最適化）。
- ETL の品質チェックモジュール強化と自動通知（Slack 連携）。
- テストカバレッジ拡充・CI ワークフロー整備。
- ドキュメント（設計ドキュメント・API 使用例）の拡充。

--- 

（本 CHANGELOG はコードベースからの実装内容を元に推測してまとめたものであり、実際の運用手順や API キー配置はリポジトリの README / ドキュメントを参照してください。）