CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
主にコードベースから推測できる追加・仕様・設計方針、既知の制約・フェイルセーフ動作を記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-28
-------------------

初回リリース。以下の主要機能と設計方針を実装しています。

Added
- パッケージ基盤
  - kabusys パッケージの公開開始（__version__ = "0.1.0"）。
  - パッケージの public API に data, strategy, execution, monitoring を設定。

- 環境設定管理（kabusys.config）
  - .env/.env.local および OS 環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - 無効行・コメント行を無視。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - 必須設定で未定義の場合は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の値検証。
    - データベースパスのデフォルト（DUCKDB_PATH: data/kabusys.duckdb, SQLITE_PATH: data/monitoring.db）。
    - is_live / is_paper / is_dev の便利プロパティ。

- AI (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None):
      - 前日 15:00 JST ～ 当日 08:30 JST の時間ウィンドウに相当するUTC時刻範囲を計算（calc_news_window）。
      - raw_news と news_symbols を結合して銘柄ごとに記事を集約（1銘柄あたり最大 _MAX_ARTICLES_PER_STOCK 記事、文字数トリムあり）。
      - 最大 _BATCH_SIZE（20）銘柄ずつ OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。その他のエラーはスキップして継続（フェイルセーフ）。
      - レスポンス検証（JSONパース、"results" 配列、code と score の存在、既知の code のみ採用、数値チェック）、スコアは ±1.0 にクリップ。
      - 成功分のみ ai_scores テーブルへ置換（BEGIN → 個別 DELETE executemany → INSERT executemany → COMMIT）。DuckDB executemany の空リスト制約を回避するためのガードあり。
    - OpenAI 呼び出しは内部関数 _call_openai_api を通すことで unittest.mock.patch による差し替えを容易化。
    - JSON mode でも前後に余計なテキストが混入する可能性を考慮し、最外の {} を抽出して復元するフォールバック処理あり。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None):
      - ETF 1321 の直近 200 日終値から MA200 乖離比率を計算（_calc_ma200_ratio）。データ不足時は中立（1.0）を返す。
      - マクロ関連キーワードで raw_news をフィルタしてタイトルを取得（最大 _MAX_MACRO_ARTICLES）。
      - OpenAI（gpt-4o-mini）でマクロセンチメントを評価（記事がない場合は LLM 呼び出しなし、API 失敗時は macro_sentiment=0.0 として継続）。
      - MA（重み 70%）とマクロセンチメント（重み 30%）を合成してスコアをクリップ。閾値により "bull"/"neutral"/"bear" を判定。
      - market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - OpenAI API 呼び出し失敗に対するリトライとログ出力の実装。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダーに基づく営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB（market_calendar）が未取得・不完全な場合は曜日ベース（土日除外）でフォールバックする一貫した設計。
    - next/prev/get_trading_days は最大探索日数の制限（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job(conn, lookahead_days=90):
      - market_calendar の最終日を確認して J-Quants API から差分取得（jquants_client 経由）、ON CONFLICT に相当する冪等保存を行う。
      - バックフィル（直近 _BACKFILL_DAYS を再取得）と健全性チェック（last_date が過剰に未来の場合はスキップ）を実装。
  - ETL パイプライン（kabusys.data.pipeline と etl エクスポート）
    - ETLResult dataclass を定義し、取得件数・保存件数・品質チェック結果・エラー一覧を保持。
    - 差分更新ロジック、デフォルト backfill、品質チェック（quality モジュール連携）を想定した設計。
    - 内部に DuckDB 用ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - kabusys.data.etl は ETLResult を再エクスポート。

- 研究用（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum(conn, target_date): 1M/3M/6M リターンと MA200 乖離（ma200_dev）。データ不足時は None。
    - calc_volatility(conn, target_date): ATR20、相対ATR、20日平均売買代金、出来高比率等を計算。必要行数未満は None を返す。
    - calc_value(conn, target_date): raw_financials（最新財務）と当日の株価を組み合わせて PER, ROE を算出。EPS が 0/欠損の場合は per を None。
    - 実装は DuckDB の SQL ウィンドウ関数を多用し、外部 API 呼び出しはなし。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン先の将来リターンを LEAD を用いて一度のクエリで取得。horizons の妥当性チェックあり（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン（ランク相関）による IC 計算を提供。使用上のフィルタリング（None 排除、最小レコード数 3）あり。
    - rank(values): 同順位は平均ランクにする実装（丸め誤差対策で round を導入）。
    - factor_summary(records, columns): count/mean/std/min/max/median の基本統計を算出。None を除外。

Changed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取得に関する仕様を明確化:
  - api_key 引数が優先。None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗する。

Notes / Known limitations
- 一部未実装の指摘:
  - calc_value では PBR や配当利回りはまだ実装されていない（ドキュメントに明記）。
- ルックアヘッドバイアス対策:
  - すべてのスコアリング・ファクター・ETL の日付処理で datetime.today()/date.today() を直接参照しないよう設計（外部から target_date を与える方式）。
- フェイルセーフ設計:
  - OpenAI 等外部依存が失敗した場合は可能な限り処理を継続（スコア値を 0.0 にフォールバック、部分的な書き込みに留める等）し、致命的な障害のみ例外を上位へ伝播。
- DuckDB 互換性:
  - executemany に空リストを与えるとエラーになるバージョンへの配慮（空チェックを行う実装）。
- テスト容易性:
  - OpenAI 呼び出しは内部の薄いラッパー関数（_call_openai_api）を用いているため、テストで簡単に patch/モック可能。

文書化・設計資料参照
- ソース内ドキュメンテーション（モジュール冒頭の docstring）に DataPlatform.md / StrategyModel.md セクション参照が散見され、実装はそれらの外部設計書に沿っていることを示唆します。

今後の改善案（推奨）
- score_news / score_regime の API 呼び出しロギングやメトリクス（成功率・レイテンシ等）を充実化する。
- calc_value に PBR や配当利回りを追加。
- ETL の品質チェックに基づく自動アラート（Slack 通知等）を実装。
- OpenAI 呼び出しの並列化やレート制限コントロールの高度化（現在はシンプルなチャンク＆リトライ）。

--- 

（この CHANGELOG はソースコードの実装から推測して作成しています。実際のリリースノートやリリース日・仕様はプロジェクトの正式な記録を参照してください。）