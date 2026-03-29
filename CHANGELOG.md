# CHANGELOG

すべての主要な変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-29
初期リリース。以下の主要機能群と実装方針を含みます。

### Added
- 基本パッケージ
  - パッケージ版情報: kabusys.__version__ = "0.1.0"。
  - パッケージ API のエクスポート設定 (__all__) を追加（data, strategy, execution, monitoring）。
- 環境設定 / ローダー（kabusys.config）
  - .env ファイルおよび OS 環境変数から設定値を自動読み込み。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート処理、インラインコメントの取り扱い）。
  - .env ロードの上書きルールを実装（OS 環境変数保護、.env と .env.local の優先度）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー _require と Settings クラスを実装し、J-Quants / kabu / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）を実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントスコアを取得する score_news を実装。
    - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を calc_news_window として提供。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたりの記事数上限・文字数トリム、スコア ±1.0 のクリップを実装。
    - API 呼び出しに対して 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでのリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、コード照合、数値検証）と不正レスポンス時のフェイルセーフ（スキップ）ロジック。
    - DuckDB の executemany の制約を考慮した安全な DELETE/INSERT ロジック（空パラメータへの対応）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - prices_daily からの MA200 比率計算、raw_news からのマクロキーワードフィルタ、OpenAI（gpt-4o-mini）呼出しおよびレスポンスパース、スコア合成を実装。
    - API エラー時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを採用。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と失敗時の ROLLBACK 対応を実装。
    - LLM 呼び出しを専用内部関数化してテスト差替え（mock）を容易に。
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar にデータがある場合は DB 値優先、未登録日は曜日ベースのフォールバック（週末除外）で一貫性のある振る舞いを実現。
    - カレンダー差分取得ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得し idempotent に保存）。バックフィル・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開し、ETL の取得数・保存数・品質問題・エラー情報を集約。
    - 差分取得、バックフィル、品質チェック方針を実装するための基盤を提供。
  - jquants_client との連携用の抽象（実装は別モジュール想定）。
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum：1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility：20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。データ不足時は None を扱う。
    - calc_value：最新の raw_financials を参照して PER / ROE を計算。EPS が 0/欠損の場合は None。
    - DuckDB の SQL ウィンドウ関数を活用した効率的実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns：指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンをまとめて取得する汎用クエリを実装。
    - calc_ic：ファクター値と将来リターンのスピアマンランク相関（Information Coefficient）を計算（有効レコード 3 件未満は None）。
    - rank：同順位は平均ランクとするランク化ユーティリティ（丸めで ties 検出漏れ防止）。
    - factor_summary：複数カラムの基本統計量（count, mean, std, min, max, median）を算出。
- テスト/運用のための設計上の配慮
  - 多くの箇所で外部 API 呼び出し部分を内部関数に分離して mock で差し替えやすく設計（例: _call_openai_api）。
  - datetime.today() / date.today() に依存する処理を避け、明示的な target_date を使用してルックアヘッドバイアスを防止。
  - DB 書き込みは冪等化（DELETE→INSERT、ON CONFLICT などの想定）とトランザクション処理を採用。

### Changed
- （初期リリースにつき履歴なし）

### Fixed
- （初期リリースにつき履歴なし）

### Breaking Changes
- なし（初期リリース）

### Security
- OpenAI API キーは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用。未設定時は明確な ValueError を返す設計で誤設定を検出しやすくしています。

---

注記:
- 実装は DuckDB を前提とした SQL 実行を多用します。DuckDB のバージョン差異に起因する挙動（例: executemany に空リストが不可など）をコード内で考慮しています。
- OpenAI の呼び出しは gpt-4o-mini を想定し、JSON Mode を利用することでレスポンスの構造化と堅牢なパースを目指しています。API の仕様変更に備え、ステータスコード判定や例外処理を慎重に設計しています。