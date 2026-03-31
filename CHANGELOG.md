# Changelog

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

現在のバージョンは src/kabusys/__init__.py に合わせて 0.1.0 としています。

## [Unreleased]

（無し）

## [0.1.0] - 2026-03-31

初回リリース。本リリースでは日本株自動売買・データ基盤・リサーチ向けのコア機能をまとめて実装しています。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージのエントリポイント（__version__ = "0.1.0"）。
  - public API として data, strategy, execution, monitoring をエクスポート。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装（自動ロードの優先順位: OS 環境 > .env.local > .env）。
  - .env パーサを実装（コメント、export 形式、クォート内のエスケープ、行内コメントの扱い等に対応）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応。
  - Settings クラスを提供し、必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）および env / log_level のバリデーションを実装。
  - データベースパス用に duckdb_path / sqlite_path を Path 型で取得。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティを提供。
    - market_calendar が未取得時の曜日ベースのフォールバック、DB 登録値の優先、探索上限の設定など安全設計。
    - calendar_update_job: J-Quants API から差分取得→冪等保存（バックフィル・健全性チェックを含む）。
  - pipeline / ETL:
    - ETLResult データクラスで ETL 実行結果を集約（品質検査結果やエラー情報を含む）。
    - 差分更新・バックフィル・品質チェックを想定した ETL 基盤（jquants_client と quality モジュールと連携する設計）。
    - テーブル存在確認や最大日付取得等の内部ユーティリティを実装。
  - etl モジュールの公開インターフェース（ETLResult を再エクスポート）。

- AI 関連（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信しセンチメント（ai_score）を算出。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して扱う calc_news_window を実装。
    - バッチサイズ、記事数/文字数トリム、リトライ（429・ネットワーク・タイムアウト・5xx）等の堅牢な処理。
    - JSON Mode のレスポンス検証とスコアクリップ（±1.0）、部分失敗時に他銘柄スコアを保護する DB 書き込み戦略。
    - テスト用に _call_openai_api のパッチが可能。
  - regime_detector モジュール:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、冪等に market_regime テーブルへ書き込む実装。
    - マクロキーワードに基づく記事抽出、OpenAI 呼び出し（JSON レスポンス）とパース、リトライ・フェイルセーフ（API 失敗時は macro_sentiment=0）を実装。
    - テスト用に _call_openai_api の差し替えが可能。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB を用いた SQL ベースの実装で、価格・財務データのみ参照（取引 API に依存しない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を用いた効率的取得）。
    - calc_ic: スピアマンのランク相関（IC）計算（NULL や非有限値を排除、十分なデータが無ければ None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）・基本統計量計算（count/mean/std/min/max/median）を実装。
    - pandas 等外部依存無しの実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや機密値は Settings 経由で環境変数により管理する設計。自動 .env ロードは環境で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / 設計上の注意
- ルックアヘッドバイアス防止: AI モジュール・リサーチモジュールは datetime.today()/date.today() を内部で参照せず、必ず呼び出し元から target_date を受け取る設計。
- DuckDB をデータレイヤとして想定しており、SQL クエリの互換性や executemany の空リスト制約（DuckDB 0.10 等）に配慮した実装が行われている。
- OpenAI 呼び出しは JSON Mode を期待しつつも、レスポンスが整形されないケースに備えたパース/復元ロジックと堅牢な例外処理（リトライ・バックオフ・フォールバック）を備える。
- モジュール間の結合を減らすため、内部の API 呼び出しラッパーは各モジュールで独立して実装され、テスト時に差し替え可能（モックしやすい）。

---

今後のリリースでは、strategy / execution / monitoring の具体的な発注ロジック、より詳細な品質チェック・テストカバレッジ、パフォーマンス最適化やドキュメント追加などを想定しています。