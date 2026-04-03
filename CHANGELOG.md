CHANGELOG
=========

このプロジェクトは Keep a Changelog の書式に準拠しています。
※コードベースから推測して作成しています。実際のコミット履歴や変更履歴がある場合は適宜追記してください。

Unreleased
----------
（なし）

0.1.0 - 2026-04-03
-----------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開用の __version__ と __all__ を設定。
- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 読み込みを実現。
  - .env パーサーは export 形式、クォート、エスケープ、インラインコメント等に対応する堅牢な実装。
  - .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、主要設定値（J-Quants トークン、kabu API パスワード、LINE トークン、DB パス、監視設定、ログレベル等）をプロパティで取得。
  - env 値のバリデーション: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
  - デフォルトのデータベースパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
- AI ニュース/レジーム判定（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を取得して ai_scores テーブルへ書き込む。
    - チャンクバッチ処理（1 API 呼び出しあたり最大 20 銘柄）・記事数/文字数制限・指数バックオフによる再試行・レスポンス検証・スコアのクリップなどの堅牢性を確保。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。
    - API 失敗時は該当チャンクをスキップして処理を続行するフェイルセーフ設計。
  - regime_detector.score_regime
    - ETF 1321（日経225連動）に対する 200 日移動平均乖離（重み 70%）と、マクロニュースに対する LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily と raw_news を参照し、market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しにはリトライ、5xx の扱い、JSON パース失敗時のフォールバック（macro_sentiment = 0.0）を実装。
    - API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定。未指定時は ValueError。
  - 両モジュールとも OpenAI の呼び出しは内部関数でラップしており、テスト時に差し替え可能（unittest.mock.patch を想定）。
- データ ETL / パイプライン（kabusys.data.pipeline / etl）
  - ETLResult データクラスを公開（etl モジュールで再エクスポート）。ETL 実行の集計（取得数・保存数・品質問題・エラー）を表現。
  - 差分取得・バックフィル・品質検査を想定した設計。J-Quants クライアント（jquants_client）を用いて安全に保存する方針を実装。
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - market_calendar テーブルを元に営業日判定ロジックを提供:
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
  - DB にカレンダーが無い/該当日の登録が無い場合は曜日（土日）ベースのフォールバックを使用。
  - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル、健全性チェック、例外ハンドリング）。
- リサーチ / ファクター計算（kabusys.research）
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損なら None）、ROE（最新財務データの取得ロジック）。
  - feature_exploration: calc_forward_returns, calc_ic（Spearman ランク相関）, factor_summary, rank。
    - calc_forward_returns は可変ホライズン（デフォルト [1,5,21]）に対応し、単一クエリで取得。
    - calc_ic は結合後にランク相関を計算し、データ不足（有効レコード < 3）時は None を返す。
    - factor_summary は count/mean/std/min/max/median を標準ライブラリのみで算出。
  - すべて DuckDB 接続を受け取り、外部 API を呼ばない設計（研究環境での安全性）。
- その他
  - data モジュールの公開インターフェース整備（pipeline.ETLResult を etl から再エクスポート）。
  - 各所で DuckDB を用いた SQL 実行ロジック、トランザクション処理、ログ出力を充実。

Changed
- 該当なし（初回リリース想定）

Fixed
- 該当なし（初回リリース想定）

Security
- 該当なし（初回リリース想定）

Notes / 既知の挙動と設計上の決定事項
- 時刻参照の扱い
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を内部ロジックで直接参照しない（外部から target_date を与える設計）。
- OpenAI / 外部 API の失敗ハンドリング
  - 429, ネットワーク切断, タイムアウト, 5xx に対しては指数バックオフでリトライ。最終的に失敗した場合はスコアを 0.0 にフォールバックするか該当チャンクをスキップする。
- DB 書き込みの冪等性
  - ai_scores / market_regime などは既存レコードの削除→挿入で置換する方式を採用し、部分失敗時に他銘柄の既存データを保持する工夫がある（DELETE を対象コードに限定）。
- .env 自動ロード
  - プロジェクトルート検出に失敗した場合は自動ロードをスキップする。必要時は明示的にロード制御可能。
- 設定バリデーション
  - KABUSYS_ENV および LOG_LEVEL は許容値以外だと ValueError を送出するため、起動前に環境変数値を確認してください。

移行／利用メモ
- OpenAI API を使用する機能（news_nlp / regime_detector）を利用する場合は環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key を渡してください。
- J-Quants 関連は環境変数 JQUANTS_REFRESH_TOKEN を用いる設計。kabu ステーション API には KABU_API_PASSWORD を使用。
- 自動 .env ロードを無効化したいテスト・開発環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続（duckdb.connect(...)）を引数に渡して各関数を呼ぶ設計です。データスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が前提となります。

今後の予定（コードから推測）
- execution / monitoring モジュール（__all__ にあるが今回差分でコード未提示）への実装追加。
- ETL と品質チェック（kabusys.data.quality）間の統合テスト強化。
- OpenAI レスポンス検証やプロンプト改善によるスコア精度向上。
- API クライアント抽象化によるテスト容易性向上。

補足
- この CHANGELOG は提供されたコードから推測して作成しています。実際のリリース日やコミット分割・細かな変更履歴が存在する場合は、該当情報で差し替えてください。