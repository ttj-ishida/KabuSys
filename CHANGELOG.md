# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。  

## [Unreleased]

（現時点の変更はすべて 0.1.0 に含まれるため未リリース項目はありません）

## [0.1.0] - 2026-04-03

初期リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装しました。  
主な追加点・設計上の特徴は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`（__version__ = 0.1.0）
  - 公開サブパッケージ候補: data, strategy, execution, monitoring（__all__ に列挙）

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定
    - 読み込み順序: OS 環境変数 > .env.local（上書き）> .env（未設定時に設定）
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意
  - `.env` パーサーは export 構文、クォート（エスケープ含む）、インラインコメント等に対応
  - 必須環境変数未設定時は `_require()` により明確な ValueError を送出
  - Settings クラスに各種設定プロパティを提供
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB / SQLite）/ 監視関連（PID ファイル等）/ リソース閾値
    - 環境 (`KABUSYS_ENV`) の検証（development / paper_trading / live）
    - ログレベル検証（DEBUG, INFO, WARNING, ERROR, CRITICAL）

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成
    - OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出
    - バッチサイズ、記事数上限、文字数トリムなどトークン肥大対策を実装
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ＋リトライ実装
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）
    - ai_scores テーブルへの冪等書き込み（該当コードの DELETE → INSERT、部分失敗時に既存スコアを保護）
    - 公開関数: score_news(conn, target_date, api_key=None)
    - 時間ウィンドウ計算ユーティリティ: calc_news_window(target_date)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して
      日次で market_regime テーブルにレジーム（bull / neutral / bear）を書き込む
    - マクロ記事抽出時のキーワード集合（日本・米国など）を定義
    - API 呼び出しは gpt-4o-mini，JSON 出力を期待
    - API のリトライ（exponential backoff）とフェイルセーフ（失敗時 macro_sentiment=0.0）
    - look-ahead バイアス対策: 内部で date.today()/datetime.today() を参照せず、prices_daily のクエリは target_date 未満のデータのみ使用
    - 公開関数: score_regime(conn, target_date, api_key=None)

- データ関連（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, is_sq_day）
    - 翌営業日 / 前営業日検索（next_trading_day, prev_trading_day）および期間内の営業日列挙（get_trading_days）
    - DB データがない場合は曜日ベース（土日除外）でフォールバックする設計
    - calendar_update_job による J-Quants からの差分取得＆冪等保存（バックフィル、サニティチェック含む）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを公開（kabusys.data.etl に再エクスポート）
    - 差分取得、保存（jquants_client による IDempotent 保存）、品質チェック（quality モジュール）を組み合わせる設計
    - ETL 実行結果の集約（取得件数、保存件数、品質問題、エラー一覧）
    - テーブル存在チェック、最大日付取得等のユーティリティを実装（DuckDB を利用）

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール
    - Momentum: 1M/3M/6M リターン計算、200日 MA 乖離（ma200_dev）
    - Volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比
    - Value: PER（EPS に基づく）、ROE（raw_financials より）
    - DuckDB ベースの SQL 実装でデータ不足時は None を返す等の堅牢性を考慮
    - 公開関数: calc_momentum, calc_volatility, calc_value
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）
    - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median
    - ランキングユーティリティ（rank）: 同順位は平均ランクで処理
    - エクスポート済みユーティリティ群を research.__init__ 経由で公開

- 共通設計上の特徴
  - DuckDB を中心にテーブル設計（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とした実装
  - ルックアヘッドバイアス防止（target_date 未満や明示的なウィンドウを使用）
  - API 呼び出しのリトライ / フェイルセーフ設計（例: OpenAI 呼び出し失敗時は 0.0 を返す等）
  - DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT を想定）に。トランザクションを用いた例外時の ROLLBACK 処理あり
  - ロギングを広範に追加（INFO/DEBUG/WARNING/exception）

### Changed
- 該当なし（初期リリースのため）

### Fixed
- 該当なし（初期リリースのため）

### Security
- 該当なし（初期リリースのため）

---

注意:
- 実装は DuckDB と OpenAI（OpenAI SDK）の利用を前提としています。実稼働での設定（APIキー、DBパス等）は Settings 経由で環境変数にて管理してください。
- OpenAI API の呼び出し点はテスト容易性を考慮して内部関数をモック可能（例: unittest.mock.patch で _call_openai_api を差し替え）にしています。
- 本リリースは初期機能群の提供に焦点を当てており、運用・監視・発注ロジック（execution / monitoring / strategy の詳細）は今後のリリースで拡張予定です。