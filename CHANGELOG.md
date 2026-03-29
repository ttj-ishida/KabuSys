Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

v0.1.0 - 2026-03-29
-------------------

Added
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - public パッケージエクスポート: data, strategy, execution, monitoring（__all__ に宣言）
- 環境設定 / ロード機構（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml により探索して検出。
    - OS 環境変数 > .env.local > .env の優先順位で読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーは以下に対応:
    - コメント行、先頭に export を付けた行、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い。
  - 環境変数必須チェック（_require）と設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須プロパティを提供。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の値検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。
  - データベースのデフォルトパス設定（DUCKDB_PATH, SQLITE_PATH）。

- AI 関連（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いてニュースごとの銘柄センチメントを算出して ai_scores テーブルへ保存する機能を実装。
    - 処理の特徴:
      - JST 基準のニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で算出。
      - 銘柄ごとに最新の記事を最大 _MAX_ARTICLES_PER_STOCK 件、最大文字数でトリムしてプロンプト化。
      - バッチサイズ (_BATCH_SIZE=20) 毎に API 呼び出し。
      - JSON Mode を利用して厳密な JSON を期待（レスポンスの復元ロジックも実装）。
      - リトライ戦略（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
      - レスポンス検証（results 配列、code と score の存在、未知コード除外、数値チェック、±1.0 のクリップ）。
      - DuckDB の executemany の制約（空リスト不可）に配慮して安全に DELETE → INSERT を実行。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - 設計方針によりルックアヘッドバイアスを避ける（datetime.today() を参照しない）。
    - テスト容易性: _call_openai_api を patch で置き換え可能。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - 処理の特徴:
      - DuckDB から過去データを取得し、ルックアヘッドを防ぐため target_date 未満のデータのみを使用。
      - マクロニュースは news_nlp.calc_news_window と raw_news を利用して抽出、最大記事数制限あり。
      - OpenAI 呼び出しは独立実装（news_nlp と内部関数を共有しない設計）。
      - API 失敗時は macro_sentiment を 0.0 にフォールバック（例外を投げず継続）。
      - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。

- Data / ETL / カレンダー（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar テーブル）を前提とした営業日判定・探索ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない/未登録日の場合は曜日ベース（平日＝営業日）でフォールバックする一貫した挙動を実装。
    - next/prev_trading_day は最大探索日数の上限（_MAX_SEARCH_DAYS）を設け例外で無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得し market_calendar を更新する夜間バッチ処理を実装。バックフィル・健全性チェックあり。
  - pipeline モジュール（kabusys.data.pipeline）
    - ETL パイプライン向けのユーティリティ群と結果オブジェクトを実装。
    - ETLResult dataclass を提供（取得数・保存数・品質問題・エラー一覧などを格納）。
    - 差分更新・バックフィル・品質チェックの設計方針に基づく実装。
    - DuckDB 上の最大日付取得など内部ユーティリティを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research（kabusys.research）
  - factor_research モジュール
    - ファクター計算関数を提供:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA 乖離）を計算。
      - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（ATR 計算で prev_close の NULL 伝播を制御）。
      - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB SQL を多用し、外部 API へのアクセスは行わない仕様。
  - feature_exploration モジュール
    - calc_forward_returns: 指定 horizon（営業日数）に基づく将来リターンを一括で計算。
    - calc_ic: スピアマンランク相関（IC）を計算（結合・欠損排除・最小レコード数 3 のチェック）。
    - rank: 平均ランク（同順位は平均ランク）を計算（floating round による tie 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - data.stats の zscore_normalize を再エクスポート（research パッケージで利用可能）。

Changed
- 初期リリースのため過去からの変更はなし（新規追加パッケージ）。

Fixed
- 初期リリースのため過去バグ修正はなし。

Notes / Implementation details / 運用上の注意
- OpenAI（gpt-4o-mini）を用いる機能（news_nlp, regime_detector）は API キーの注入を受け付ける（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を投げる。
- LLM 呼び出しに対してはリトライ・フォールバックを厳密に実装しており、API 側問題時にシステム全体が停止しないようフェイルセーフ化している（多くのケースで 0.0 を返して継続）。
- ルックアヘッドバイアス防止のため、日付の取り扱いは target_date を明示的に渡す設計。内部で datetime.today()/date.today() を参照する処理は主要アルゴリズムでは避けられている（calendar_update_job など一部は date.today() を使用）。
- DuckDB のバージョン互換性（executemany の挙動など）に配慮した実装（空リスト回避など）。
- テスト容易性: OpenAI 呼び出しや内部ユーティリティは patch による差し替えが容易にできるよう設計されている（モジュール内 private 関数を直接モック可能）。
- 外部依存: openai SDK、duckdb、および jquants_client（data.jquants_client）が想定される。jquants_client の実装は本スナップショットには含まれないが、fetch/save API を利用する想定。

今後の予定（含める予定の改善項目）
- strategy / execution / monitoring パッケージの具体実装（__all__ に含まれるが今回のスナップショットで詳細は未提供）。
- 追加の品質チェックルールや監視アラートの充実化。
- テストカバレッジ拡充（特に外部 API 呼び出し周りのフェイルケース）。
- 型注釈・ドキュメントの更なる整備と API ドキュメント生成。

Contributing
- 変更やバグ修正の際は Keep a Changelog のフォーマットに従って CHANGELOG.md を更新してください。API 互換性を壊す変更はメジャーバージョンの変更にて扱ってください。