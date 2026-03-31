Keep a Changelog
=================

すべての可視的な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠しています。
規約: https://keepachangelog.com/（日本語意訳）

Unreleased
---------

（現時点の開発中の変更点はここに記載します）

0.1.0 - 2026-03-31
-----------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ公開インターフェースを定義:
  - kabusys.__all__ = ["data", "strategy", "execution", "monitoring"]（サブパッケージ公開予定を示す）。
- 環境設定管理:
  - kabusys.config: .env / .env.local の自動読み込み機能を実装。
    - プロジェクトルートは __file__ の親ディレクトリから .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .env のパースは export 形式、クォートやエスケープ、行内コメントなどに対応。
    - .env.local は override=True で OS 環境変数を保護しつつ上書きが可能（既存 OS 環境変数は protected）。
  - Settings クラスを提供し、主要な設定値をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（API 呼び出し側で参照する設計）
    - KABUSYS_ENV の許容値は "development","paper_trading","live"。
    - LOG_LEVEL の許容値は "DEBUG","INFO","WARNING","ERROR","CRITICAL"。
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
    - 必須環境変数未設定時は ValueError を送出する明示的 API。
- AI（自然言語処理）関連:
  - kabusys.ai.news_nlp:
    - ニュース記事（raw_news / news_symbols）を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - チャンクサイズ・トリム（最大記事数・最大文字数）・バッチ処理で効率化。
    - リトライ戦略（429、ネットワーク断、タイムアウト、5xx）と指数バックオフを実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列チェック、スコア型チェック、既知コード検証、±1.0 クリップ）。
    - ai_scores テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）ことで部分失敗時の保護。
    - calc_news_window(target_date) を公開（JST→UTC 変換ロジック、前日 15:00 JST ～ 当日 08:30 JST を UTC 半開区間で表現）。
  - kabusys.ai.regime_detector:
    - ETF 1321（Nikkei 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュース由来の LLM センチメント（重み 30%）を合成し日次の市場レジーム（bull/neutral/bear）を算出。
    - _calc_ma200_ratio による look-ahead を防ぐデータ選択（target_date 未満のデータのみ使用）とデータ不足時のフォールバック（中立 1.0）。
    - マクロニュース抽出はキーワードベースでフィルタ（最大件数制限）。
    - OpenAI 呼び出しは独立実装、フェイルセーフ: API 失敗時は macro_sentiment=0.0。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT、エラー時は ROLLBACK を行う）。
- Research（リサーチ）機能:
  - kabusys.research.factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB を用いた SQL 中心の高速処理。結果は (date, code) キーの dict リストで返す。
    - データ不足時の None 返却やログ出力など堅牢な設計。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（任意ホライズン最大 252 営業日まで）、IC（Spearman rank correlation）、ファクター統計サマリを提供。
    - ランク付け・同順位処理、統計量（count/mean/std/min/max/median）実装。外部依存を避け標準ライブラリのみで実装。
  - kabusys.research.__init__ で主要ユーティリティを再エクスポート（zscore_normalize は data.stats から）。
- Data（データ取得・ETL）:
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。
  - kabusys.data.pipeline:
    - ETLResult dataclass: ETL の取得数・保存数・品質問題・エラー一覧を保持。has_errors / has_quality_errors / to_dict を提供。
    - 差分取得・バックフィル・品質チェックを行うためのユーティリティ（テーブル存在チェック、最大日付取得、取込日調整など）。
    - J-Quants clients（jquants_client）を利用する設計を想定（差分取得・保存の責務は jquants_client 側）。
  - kabusys.data.calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - calendar_update_job による夜間バッチでの差分取得と冪等保存（バックフィル、健全性チェックあり）。
    - market_calendar 未取得時は曜日ベース（週末非営業日）でフォールバックする一貫した動作。
- テストとモックを想定した設計:
  - OpenAI 呼び出しを行う内部関数（各モジュール内 _call_openai_api）をテスト時に patch 可能にし、ユニットテストで差し替えが容易。
- ロギングとフォールバック:
  - 多数の箇所で警告ログ・情報ログを出し、外部 API の失敗時は例外を上位へ伝播しない（フェイルセーフ）設計の箇所があるため運用継続性を重視。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- .env 読み込み時に OS 環境変数を保護する設計（.env.local は override だが既存 OS 環境変数は protected）。
- OpenAI API キー等の必須機密情報は Settings._require により未設定で ValueError を発生させる（明示的なエラーで誤設定を検出）。

Notes / Known limitations
- OpenAI SDK の応答形式や status_code の変化に備えた保護ロジックを備えるが、将来 SDK の破壊的変更があれば追加対応が必要。
- DuckDB のバージョン差異（例: list 型のバインド制約）を考慮して健全なワークアラウンドを実装しているが、環境依存の挙動に注意が必要。
- raw_financials による Value 系指標は報告日ベースの最新レコード取得に依存。財務データの整備状況によっては None が多くなる可能性あり。
- AI モジュールは gpt-4o-mini をデフォルトで使用する設定だが、コストや利用制限に応じてモデル差し替えを検討する必要がある。
- package 内に参照される jquants_client、monitoring、strategy、execution の具体実装はこのリリースではサンプル／参照に留まる場合がある（実行環境での接続先実装が必要）。

Authors
- 開発チーム（コードベースの docstring と構成から推測して記載）

ライセンス
- リポジトリに同梱されている LICENSE を参照してください（本 CHANGELOG はコードからの推測に基づく記述です）。