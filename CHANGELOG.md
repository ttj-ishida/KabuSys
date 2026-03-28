# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-28

初回公開リリース。日本株のデータ収集・研究・AIによるニュース解析・市場レジーム判定・カレンダー管理を行う自動売買補助ライブラリの基盤機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パブリックモジュールのエクスポート: data, strategy, execution, monitoring（__all__）。

- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサを実装:
    - export KEY=val の形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし行でのインラインコメント処理（直前が空白/タブの場合に # をコメントとみなす）。
  - 環境変数保護: OS 環境変数を保護するための protected キーセットを使用して .env.local により上書き制御。
  - Settings クラスを提供し、典型的な設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev ヘルパー

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブルの読み書き、営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の実装。
    - DB 未取得時は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job により J-Quants API から差分取得して冪等的に保存（バックフィル、健全性チェックあり）。
  - pipeline / ETL:
    - ETLResult データクラスの実装（ETL 実行結果の集約、品質問題・エラーメッセージの保持、辞書化メソッド）。
    - ETL ユーティリティの公開インターフェース（kabusys.data.etl から ETLResult を再エクスポート）。
    - DuckDB 互換性や最終日取得などの内部ユーティリティ実装。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン, 200日移動平均乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）を計算する関数を実装。
    - DuckDB SQL ベースで高速に計算し、(date, code) をキーとする辞書リストを返す設計。
    - データ不足時の挙動（None を返す等）を明確化。
  - feature_exploration:
    - calc_forward_returns（将来リターンの一括取得、任意ホライズン対応、入力検証）
    - calc_ic（スピアマンランク相関による IC 計算。3 件未満は None 戻し）
    - rank（同順位は平均ランクにする実装、丸めで ties の検出を安定化）
    - factor_summary（各カラムの count/mean/std/min/max/median を計算）
  - zscore_normalize は kabusys.data.stats から再エクスポート（__init__ に反映）。

- AI モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を用い、指定のニュースウィンドウ（JST 基準）から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）にバッチ送信し、ai_scores テーブルへ書き込む処理を実装。
    - calc_news_window（タイムウィンドウ計算、JST→UTC の変換）を公開。
    - バッチサイズ、記事上限、文字数トリム、JSON mode のレスポンス検証、リトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
    - レスポンスパースとバリデーションを厳密化（未知コード無視、数値変換、有限性チェック、スコアの ±1 クリップ）。
    - score_news(conn, target_date, api_key=None) を公開（OpenAI APIキーは引数または OPENAI_API_KEY 環境変数で供給）。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する score_regime を実装。
    - マクロニュース取得ロジック（キーワードフィルタ）、OpenAI 呼び出し、再試行、フェイルセーフ（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避設計（datetime.today()/date.today() 不使用、target_date 未満のみ参照）。
    - テスト容易性のため _call_openai_api をモジュール内で独立実装（news_nlp と共有しない）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- フォールバックやエラーハンドリングを強化:
  - OpenAI API 呼び出しでの 5xx / ネットワークエラー / タイムアウト / RateLimit に対して適切にリトライ & ログ出力し、最終的に安全なデフォルト（0.0）にフォールバックする実装。
  - DuckDB の executemany に関する互換性問題（空リスト不可）を考慮して条件付きで executemany を実行。
  - market_calendar の NULL 値に対して警告を出し、曜日ベースのフォールバックを行うように修正。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは外部から注入する設計（環境変数 / 関数引数）でハードコーディングを回避。
- .env 読み込み時に OS 環境変数を上書きしないデフォルト動作、上書き可否は .env.local と protected キーで制御。

### 既知の注意点 / 使用上の補足
- 必須環境変数:
  - OPENAI_API_KEY（score_news / score_regime 実行時に必要。関数に api_key を渡すことでも可能）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DuckDB を使った内部クエリ設計のため、DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を各関数に渡して使用します。
- 時間計算はローカルタイム（JST）→ DB に保存されている UTC 前提での比較などを行うため、target_date に対するウィンドウは関数で明示的に計算されます（ルックアヘッド禁止の設計）。
- news_nlp / regime_detector の OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用し、レスポンスのパースとバリデーションを厳密に行います。外部モデル仕様の変更に備えてパース失敗時は安全にスキップまたは 0.0 にフォールバックします。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を利用します。API のレスポンス例外はログに残して処理を中止します。

---

今後の予定（想定）
- strategy / execution / monitoring モジュールの具現化（注文発注ロジック、リアルタイム監視、Slack 通知等）
- テストカバレッジ拡充、CI 導入、ドキュメント追加（使用例・API リファレンス）
- パフォーマンスチューニングとバッチ並列化

もし CHANGELOG に含めたい追加の観点（例: 重要な設計決定や互換性に関する詳細、内部 API の安定化ポリシー）があれば指示ください。