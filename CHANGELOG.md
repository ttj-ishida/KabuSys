# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
初回リリース（0.1.0）はパッケージのコア機能群を実装したものです。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: KabuSys 日本株自動売買システムの基本モジュール群を提供。
  - パッケージメタ情報
    - kabusys.__version__ = "0.1.0"
    - public API: data, strategy, execution, monitoring を __all__ にエクスポート
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（優先順: OS 環境変数 > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
  - .env パーサ実装（export 形式、クォート、エスケープ、インラインコメント対応）
  - 必須環境変数取得ユーティリティ（_require）と Settings クラスを提供
    - サポートされる設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（呼び出し時引数でも可）
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の有効値チェック）
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメントを算出
    - タイムウィンドウ（JST: 前日 15:00 ～ 当日 08:30）計算ユーティリティ calc_news_window
    - チャンク処理（最大 20 銘柄 / リクエスト）、1 銘柄あたり記事数・文字数の上限 (_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK)
    - 再試行ロジック（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）
    - レスポンスバリデーション（JSON パース、構造確認、未知コード無視、スコア数値化・±1.0 クリップ）
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）
    - テスト用フック: _call_openai_api を patch して差し替え可能
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースベースのマクロセンチメント（重み 30%）の合成による日次レジーム判定（bull/neutral/bear）
    - prices_daily / raw_news を参照して ma200_ratio とマクロ記事タイトルを取得
    - OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を取得（記事がない場合は LLM 呼び出しを行わず 0.0）
    - 再試行・フェイルセーフ: API 失敗時は macro_sentiment = 0.0 で継続
    - 結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）し、失敗時は ROLLBACK を試行
    - テスト用フック: _call_openai_api を patch 可能
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの利用による営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録値優先、未登録日は曜日ベースのフォールバック（weekend 判定）
    - カレンダー夜間更新ジョブ calendar_update_job（J-Quants API を想定した差分取得 / バックフィル / 健全性チェック）
    - 最大探索日数制限 (_MAX_SEARCH_DAYS)、バックフィル日数、先読み日数等の安全策を実装
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）
      - ETL 実行結果の収集（取得件数、保存件数、品質チェック結果、エラーリスト等）
      - has_errors / has_quality_errors プロパティ、to_dict によるデバッグ向け変換
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計ドキュメントに準拠
    - DuckDB に対する互換性配慮（executemany の空リスト制約への対応など）
  - jquants_client との連携を前提とした保存/取得ワークフローに対応（実装ファイルはクライアント側）
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）
    - ボラティリティ / 流動性（20 日 ATR、相対ATR、20日平均売買代金、出来高比）
    - バリュー（PER、ROE。raw_financials での最新財務取得）
    - DuckDB SQL による実装、データ不足時の None 扱い
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Information Coefficient、Spearman ρ）計算
    - ランク変換ユーティリティ（同順位は平均ランク、丸めによる ties 対応）
    - ファクター統計サマリー（count/mean/std/min/max/median）
  - 主要ユーティリティの再エクスポート: zscore_normalize など

### Changed
- N/A（初回リリースのため既存機能の変更はありません）

### Fixed
- N/A（初回リリース）

### Security
- 外部 API キーは環境変数（OPENAI_API_KEY 等）または関数引数で注入する設計。コード中にハードコードされた API キーは含まれない。

### Notes / 設計上の重要なポイント
- ルックアヘッドバイアス回避:
  - 各 AI / データ処理モジュールは date.today() / datetime.today() を使用せず、明示的に target_date を受け取る設計。
  - DB クエリでは target_date 未満／以上などの条件を使って未来データ参照を防止。
- フェイルセーフ:
  - OpenAI 呼び出しの失敗は致命的エラーにしない（マクロスコアは 0.0、ニューススコアは該当チャンクをスキップ）ことでパイプライン継続を優先。
- 冪等性:
  - DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 想定、トランザクションおよび ROLLBACK 処理）。
- テスト容易性:
  - OpenAI 呼び出し部分はモジュール内のプライベート関数（_call_openai_api）を patch して差し替え可能。
- DuckDB 互換性:
  - DuckDB のバージョン差異に起因する挙動（executemany の空リストなど）に対処するコード記述がある。
- OpenAI モデル:
  - 現時点では gpt-4o-mini を利用（JSON Mode を利用した厳密な JSON 出力を期待）。

---

開発・利用にあたっては README / 各モジュールの docstring を参照してください。必要に応じて各機能を個別にバージョン管理していきます。