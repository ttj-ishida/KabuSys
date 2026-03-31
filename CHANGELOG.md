# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。

## [Unreleased]
- 現在の開発ブランチの変更は特になし（初期リリース v0.1.0 を参照してください）。

## [0.1.0] - 2026-03-31
初期リリース。日本株自動売買システムのコアライブラリを公開。

### Added
- パッケージ初期化
  - パッケージ名: kabusys
  - __version__ = 0.1.0
  - パッケージの公開モジュール一覧に data, strategy, execution, monitoring を含む（将来のサブパッケージ設計を示唆）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル（.env, .env.local）をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - シンプルな .env パーサを実装（コメント、export プレフィックス、クォート・エスケープに対応）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須（未設定時は ValueError）。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV にはデフォルト値とバリデーションを実装。
    - is_live / is_paper / is_dev ヘルパーを提供。

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを LLM（gpt-4o-mini）へバッチで送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）計算機能を提供（calc_news_window）。
    - API 呼び出しのリトライ（429, ネットワーク断, タイムアウト, 5xx）や指数バックオフ処理を実装。
    - レスポンスの厳密なバリデーションを実装（JSON 抽出、results 構造・型検証、未知コード無視、スコアを ±1.0 にクリップ）。
    - DuckDB へ冪等的に書き込むロジック（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定。
    - news_nlp の calc_news_window を利用してニュースウィンドウを算出。
    - OpenAI クライアントを使ったマクロセンチメント算出（_score_macro）にリトライ、5xx の扱い、API エラー時のフェイルセーフ（macro_sentiment=0.0）。
    - 計算結果を market_regime テーブルへ冪等的に保存（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - momentum（1m/3m/6m リターン、ma200 乖離）、volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、value（PER、ROE）の計算機能を実装。
    - DuckDB を使った SQL ベースの計算で、結果は (date, code) 単位の辞書リストで返却。
    - データ不足時の None 処理、ログ出力を実装。

  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズンの fwd_#d を一度のクエリで取得。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）を自前実装し、同順位は平均ランクで処理。
    - ランク変換ユーティリティ（rank）：丸め対策（round(v,12)）による ties の扱いを実装。
    - ファクター統計サマリ（factor_summary）：count/mean/std/min/max/median を計算。
    - 外部ライブラリ（pandas 等）に依存せず、標準ライブラリおよび DuckDB のみで実装。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日ベース（土日を非営業日）でフォールバック。
    - JPX カレンダーを J-Quants から差分取得して market_calendar を更新する夜間ジョブ（calendar_update_job）を実装。バックフィル・健全性チェックを含む。
    - DuckDB からの date 型取り扱いや NULL の扱いについて注意喚起ログを出力。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETL 実行結果を表すデータクラス ETLResult を公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（jquants_client 経由の冪等保存）、品質チェック（quality モジュール）を想定した設計。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティを実装。

### Changed
- （初期リリースのため変更履歴はありません）

### Deprecated
- なし

### Removed
- なし

### Fixed
- （初期リリースのため修正履歴はありません）

### Security
- API キーの取り扱いに注意:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して安全に停止。
  - 設定管理は OS 環境変数を保護するため .env 読み込み時に既存 OS 環境変数を上書きしない（.env.local は上書き可だが OS 環境変数は protected）。

### Notes / Implementation details / Limitations
- ルックアヘッドバイアス対策:
  - 多くの関数（score_news, score_regime, factor計算等）は内部で datetime.today()/date.today() を参照せず、caller が target_date を渡す設計になっている。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定（JSON Mode）。結果のパースやエラーハンドリング、リトライ挙動を厳密に実装。
  - テスト容易性のため _call_openai_api をパッチ差し替え可能。
- DuckDB 互換性:
  - DuckDB の executemany に空リストを渡せない制約への対処（空のときは呼ばない）。
  - テーブル存在チェックや date 型の取り扱いに注意。
- 冪等性:
  - DB 書き込みは基本的に冪等（DELETE→INSERT、ON CONFLICT 想定）で設計されている。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等は必須。
  - DUCKDB_PATH, SQLITE_PATH はデフォルトを提供（data/kabusys.duckdb, data/monitoring.db）。
- 未実装 / 想定:
  - strategy, execution, monitoring サブパッケージへの具体的実装は本リリースでは含まれていない（パッケージ __init__ で公開予定を示唆）。

---

作成した CHANGELOG はコードベースの設計・実装内容から推測して記載しています。追加のリリース日あるいは過去のバージョン履歴があれば、それに合わせて日付や項目を更新してください。