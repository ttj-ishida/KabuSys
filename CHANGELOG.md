# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

## [0.1.0] - 2026-04-04

初回公開リリース。本リポジトリの主要機能を実装しています。主にデータ取得・ETL、マーケットカレンダー管理、研究用ファクター算出、ニュースNLP/市場レジーム判定、および環境設定ユーティリティを提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化（version = 0.1.0）。公開 API として data / research / ai 相等のサブパッケージをエクスポートする想定（__all__ に "data", "strategy", "execution", "monitoring" を設定）。

- 環境設定 / .env ローダー（kabusys.config）
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
  - .env / .env.local の自動読み込み（優先順位: OS環境変数 > .env.local > .env）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしの行でのコメント処理（# の直前が空白/タブの場合のみコメントと判定）
    - 無効行（空行やコメント等）はスキップ
  - 読み込み時の上書き制御: override フラグと protected（OS環境変数保護）をサポート。
  - Settings クラスを提供し、主要設定値をプロパティで公開:
    - J-Quants / kabu / LINE API のキーやエンドポイント
    - DBパス（DUCKDB_PATH、SQLITE_PATH）のデフォルト（data/ 以下）
    - 監視用ファイルパス・閾値（PID ファイル、KILL フラグ、CPU/MEM/DISK の閾値）
    - 環境（KABUSYS_ENV: development / paper_trading / live）とログレベル検証
    - is_live / is_paper / is_dev のヘルパー

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウを計算する calc_news_window を実装（UTC naive datetime 出力）。
    - raw_news と news_symbols を結合して、銘柄ごとに最新記事を集約（最大記事数・最大文字数でトリム）。
    - OpenAI（gpt-4o-mini、JSON mode）へ最大 20 銘柄ずつバッチ送信（_BATCH_SIZE=20）。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフリトライ（最大 _MAX_RETRIES）。
    - レスポンスの堅牢なバリデーションと extraction（JSON 抽出・results 検証・コード整合性確認・スコア数値化、±1 にクリップ）。
    - 成功した銘柄のみ ai_scores テーブルへ冪等的に置換（対象コードのみ DELETE → INSERT）し、部分失敗時でも既存スコアを保護。
    - API キー解決は引数優先、なければ環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。
    - テスト容易性のため _call_openai_api は patch で差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321（日本225連動）の直近 200 日終値から MA200 乖離を算出（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - raw_news からマクロキーワードでフィルタした記事タイトルを抽出（最大 _MAX_MACRO_ARTICLES）。
    - OpenAI によるマクロセンチメント評価（gpt-4o-mini, JSON mode）。API 失敗時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - MA の重み 70%、マクロセンチメント 30% でスコア合成し clip(-1,1)。
    - スコアに基づき regime_label を bull / neutral / bear に分類（閾値設定あり）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT の構成）を行う。
    - API 呼び出しは _call_openai_api を内部実装し、news_nlp と共有しない（モジュール結合抑制）。
    - API キー解決は引数優先、なければ環境変数 OPENAI_API_KEY。未設定時は ValueError を送出。

- 研究用ファクター計算（kabusys.research）
  - factor_research モジュール:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev)。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを算出。データ不足は None を返す。
    - calc_value(conn, target_date): raw_financials から最新財務を参照して PER・ROE を計算（EPS が 0・欠損時は None）。
    - いずれも DuckDB の prices_daily / raw_financials を参照する実装で、外部 API にはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（デフォルト [1,5,21]）を計算。horizons に対する入力検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク相関）による IC を計算。有効レコード < 3 の場合は None。
    - rank(values): 同順位は平均ランクにするランク関数（浮動小数点丸め対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - すべて標準ライブラリのみで実装（pandas 等非依存）。

- データ関連（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダーに基づく営業日判定 API を提供:
      - is_trading_day(conn, d), next_trading_day(conn, d), prev_trading_day(conn, d), get_trading_days(conn, s, e), is_sq_day(conn, d)
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末を非営業日）を提供し、一貫した結果を保証。
    - _MAX_SEARCH_DAYS による探索上限で無限ループを防止。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS): J-Quants クライアントを介して差分取得・バックフィル（直近 _BACKFILL_DAYS）し、market_calendar を冪等的に更新。健全性チェック（将来日付が過度に遠い場合はスキップ）。
    - jquants_client 経由の fetch/save を利用（jq.fetch_market_calendar / jq.save_market_calendar）。
  - pipeline / ETL（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン設計:
      - 差分更新、idempotent 保存（jquants_client.save_* を使用）
      - 品質チェック（quality モジュール）を実行し、結果を ETLResult に格納（致命的エラーがあっても全件収集の設計）
      - デフォルトのバックフィル日数や最小データ日付等の定数を定義
    - _table_exists, _get_max_date 等のユーティリティ実装（DuckDB 前提）

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の制限 / 注意事項
- OpenAI 連携機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要。api_key 引数で明示的に注入可能。
- DuckDB を前提とする実装であり、prices_daily / raw_news / ai_scores / market_regime / raw_financials 等のテーブルスキーマに依存する。
- AI 呼び出しは外部 API に依存するためネットワーク障害やレート制限が発生する可能性がある。設計上、該当箇所はフェイルセーフ（多くのケースでスコア=0 やスキップ）となるが、呼び出し元での取り扱いに注意が必要。
- .env パーサは多くの一般的ケースに対応するが、特殊な .env 構文や複雑なエスケープに対しては想定外動作をする可能性あり。
- 一部関数（内部の _call_openai_api 等）はテストのため patch 可能に設計。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。API キー等の機密情報は環境変数または引数で安全に渡す設計を想定。

---
（今後のリリースでは機能追加・改善・バグ修正をカテゴリ別に記録します。）