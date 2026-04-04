# Changelog

すべての注目すべき変更履歴を記録します。フォーマットは Keep a Changelog に準拠しています。

継続的インテグレーションやリリース作業のために、このファイルは日本語で要約を提供します。

## [0.1.0] - 2026-04-04

初回リリース。本バージョンでは、データプラットフォーム、リサーチ、AI（ニュース NLP / レジーム検出）、設定管理、ETL ユーティリティ、カレンダー管理など、自動売買システム KabuSys のコア機能群を提供します。

### 追加 (Added)
- パッケージ基本情報
  - pakage version: 0.1.0 (src/kabusys/__init__.py)

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルート（.git / pyproject.toml を探索して決定）から自動読み込みする仕組みを実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - OS 環境変数を保護する protected 機能、ファイル読み込み失敗時の警告通知。
  - .env の解析は export KEY=val、クォート内のエスケープ、インラインコメント等に対応する堅牢なパーサを実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを導入し、下記プロパティを提供（主なもの）
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password, kabu_api_base_url
    - line_channel_access_token, line_user_id
    - duckdb_path, sqlite_path
    - pid_file_path, kill_flag_path, kill_flag_clear_on_start
    - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
    - env, log_level, is_live/is_paper/is_dev
  - 環境変数の必須チェックで未設定時に ValueError を送出するユーティリティを実装。

- AI モジュール: ニュース NLP と市場レジーム判定 (src/kabusys/ai/)
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI (gpt-4o-mini, JSON Mode) に送信して銘柄ごとのセンチメント（ai_score）を算出。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理: 最大 20 銘柄ずつ送信、1 銘柄あたり記事数上限・文字数トリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)。
    - 再試行戦略: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンス検証: JSON パース、results リスト・code/score 構造チェック、未知コードの無視、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは冪等（対象コードのみ DELETE → INSERT）で部分失敗時の既存データ保護。
    - テスト容易性のため _call_openai_api を patch して差し替え可能。
    - パブリック API: score_news(conn, target_date, api_key=None) -> 書込銘柄数
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）。
    - マクロニュースはニュースタイトルをマクロキーワードでフィルタして取得、LLM（gpt-4o-mini）へ送信して -1.0〜1.0 の macro_sentiment を取得。
    - LLM 呼び出しは最大リトライ、API エラーやパース失敗時は macro_sentiment=0.0 でフェイルセーフ。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。API キーは引数または環境変数 OPENAI_API_KEY から解決。
    - パブリック API: score_regime(conn, target_date, api_key=None) -> 1（成功）

- データモジュール (src/kabusys/data/)
  - calendar_management.py
    - JPX カレンダーの管理、営業日判定ロジック、next/prev/get_trading_days/is_sq_day を提供。
    - market_calendar がない場合の曜日ベースフォールバック（週末は非営業日）を実装。
    - カレンダー更新ジョブ calendar_update_job(conn, lookahead_days=90) を実装。J-Quants から差分取得して冪等保存。
    - バックフィル、健全性チェック（大幅に将来日付が登録されている場合はスキップ）等に対応。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを導入（取得/保存件数、品質問題、エラー情報を格納）。
    - 差分取得・保存・品質チェックを想定した設計。jquants_client と quality モジュールと連携する想定の実装。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究用モジュール (src/kabusys/research/)
  - factor_research.py
    - モメンタム（mom_1m/mom_3m/mom_6m、ma200_dev）、ボラティリティ（atr_20/atr_pct）、バリュー（per/roe）等のファクター計算を実装。DuckDB の SQL ウィンドウ関数を活用。
    - 各関数は prices_daily / raw_financials を参照し、(date, code) キーの dict リストを返す。
    - 欠損やデータ不足時の挙動（None を返す）を明確化。
  - feature_exploration.py
    - 将来リターン calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）、IC（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - スピアマンIC はランク変換（同順位は平均ランク）に基づき計算。
  - research パッケージの __init__.py で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 設計上の留意点（ドキュメント的追記）
- ルックアヘッドバイアス対策: すべての AI / リサーチ / ETL の日付ロジックは内部で datetime.today() / date.today() を直接参照しないよう設計。target_date を明示的引数として与えることで検証可能性を確保。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）障害時は例外を上位へ投げずに安全なデフォルト（例: macro_sentiment=0.0、スコア未取得扱い）で継続する設計を多用。
- DuckDB 互換性: executemany の空リストに対する制約や配列バインドの互換性を回避する実装（個別 DELETE → INSERT パターン等）を採用。
- テストの容易性: 各 AI 呼び出しの内部関数（_call_openai_api 等）は patch して差し替え可能にしてあり、単体テストで外部ネットワーク依存を排除可能。

### 既知の制限 / 今後の改善候補
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を前提としているため、OpenAI SDK の将来の API 変更に対しては互換性対応が必要になる可能性がある。
- 一部の挙動（例: score_news の出力スキーマ期待、news_nlp のトリム方針）は運用でチューニングが必要。
- raw_financials 由来の PBR・配当利回り等は未実装（将来追加予定）。

---

貢献・バグ報告・機能要望はリポジトリの Issue にてお知らせください。