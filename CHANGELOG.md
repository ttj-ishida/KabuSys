# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  

最新バージョン: 0.1.0（初回リリース）

※日付はパッケージの __version__ とリポジトリ初期公開を想定した日付です。

Unreleased
----------
（なし）

0.1.0 - 2026-03-28
-----------------
Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンを __version__ = "0.1.0" として公開。
  - __all__ に data / strategy / execution / monitoring をエクスポート。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定をロードする自動ローダーを実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=true）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサーは export KEY=val 形式、クォート内のエスケープ、行末コメント処理等に対応。
    - 既存の OS 環境変数を保護するため protected セットをサポート。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト local URL）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数取得時に未設定だと ValueError を投げる _require 実装。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し、ai_scores テーブルへ書き込む処理を実装。
    - JST のニュースウィンドウ（前日 15:00 ～ 当日 08:30）を UTC に変換して対象記事を抽出。
    - 1 銘柄あたり最大記事数・文字数でトリム(_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK)。
    - 1 回の API コールで最大 20 銘柄（チャンク処理）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - JSON Mode 出力を検証して score を ±1.0 にクリップ、部分失敗時は既存スコアを保護しつつ成功分のみ DELETE→INSERT で置換。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector.score_regime: ETF 1321（日経225連動型）の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - ma200_ratio の計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを防止。
    - マクロキーワードで raw_news をフィルタし、OpenAI に渡して JSON でマクロセンチメントを取得。
    - LLM 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ。
    - DuckDB へ冪等的（BEGIN/DELETE/INSERT/COMMIT）に書き込む実装。
    - OpenAI 呼び出しは独立実装とし、モジュール結合を避けテスト可能に設計。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）用ユーティリティを追加。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - DB にカレンダー情報がある場合はそれを優先、未登録日は曜日（平日）ベースでフォールバックする一貫したロジック。
    - next/prev で探索上限日数を設けて無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等に更新する夜間バッチジョブを実装（バックフィル・健全性チェックあり）。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - ETL パイプラインの設計（差分更新、保存、品質チェックの方針）を実装。
    - _get_max_date 等の内部ユーティリティを実装し、テーブルの最大日付取得やテーブル存在チェックを提供。
    - デフォルトバックフィル日数、最小データ日付等の定数化。
  - quality / jquants_client へ接続するための呼び口（実API 呼び出しは jquants_client 側に委譲）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB クエリで計算。
    - calc_volatility: 20 日 ATR / 相対 ATR / 20 日平均売買代金 / 出来高比率を計算。
    - calc_value: raw_financials と価格を組み合わせて PER / ROE を算出（EPS = 0 の場合は None）。
    - 計算はすべて prices_daily / raw_financials のみを参照し本番 API にはアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得する汎用クエリ実装（ホライズン検証あり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算するユーティリティ。
    - rank: 同順位は平均ランクとなるランク化ユーティリティ（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算するユーティリティ。
  - いずれも外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- その他
  - OpenAI 呼び出しに関する共通設計方針:
    - JSON モードのレスポンスパースの堅牢化（前後余計なテキストが混ざるケースの復元ロジック含む）。
    - 429/ネットワーク断/タイムアウト/5xx のリトライロジック（指数バックオフ）。
    - テスト容易性のため _call_openai_api を patch 可能にしている箇所がある（news_nlp, regime_detector）。
  - DuckDB を主要なローカル分析ストアとして採用（SQL ベース処理、executemany の空リスト制約への対処などを考慮）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 注意事項
- ルックアヘッドバイアス防止のため、各モジュール（news scoring, regime 判定, ファクター計算等）は datetime.today()/date.today() を内部で直接参照せず、呼び出し側から target_date を渡す設計になっています。バッチ処理や検証での再現性が確保されています。
- OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を送出します。
- .env の自動ロードはデフォルトで有効。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB のバージョン差異（executemany の空リスト等）に配慮した実装がなされています。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装および統合テスト。
- ETL パイプラインの具体実装（jquants_client と quality モジュールの結合）。
- モデルの評価パイプライン・バックテスト機能の追加。

--- 
以上。必要であれば、CHANGELOG に日付修正やリリースノートの分割（AI / Data / Research）などの調整を行います。