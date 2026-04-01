# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は「Keep a Changelog」に準拠します。  

なお、本ファイルはコードベースから推測して生成した初期の変更履歴です。実際のリリース履歴や日付は実運用に合わせて更新してください。

## [Unreleased]

## [0.1.0] - 2026-04-01
最初の公開リリース。日本株自動売買／データ基盤・リサーチ向けのコア機能群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージを導入。__version__ = 0.1.0。
  - __all__ で主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定管理
  - kabusys.config: .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - 自動ロード: プロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env の解析は export 形式、クォート、エスケープ、インラインコメント等に対応。
    - OS 環境変数を保護する protected 機構と override の挙動を提供。
    - 必須設定取得用の _require を実装（未設定時 ValueError を発生）。
    - 代表的な設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, データベースパス, 監視閾値, 環境/ログレベル判定など）。

- データ / ETL / カレンダー
  - kabusys.data.pipeline: ETL パイプラインの骨組みと ETLResult データクラスを実装。
    - ETLResult は取得/保存件数、品質問題、エラー一覧を保持し、辞書化メソッドを提供。
  - kabusys.data.etl: ETLResult を公開インターフェースとして再エクスポート。
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダーの管理ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar の有無に応じた DB 優先ロジックと曜日ベースのフォールバックを採用。
    - calendar_update_job: J-Quants API から差分取得して冪等に保存する夜間バッチ処理を実装（バックフィル、健全性チェックを含む）。
    - 最大探索日数保護（_MAX_SEARCH_DAYS）やバックフィル、先読み日数等の運用パラメータを定義。

- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores に保存する score_news を実装。
    - 処理上の特徴:
      - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30）に基づく記事抽出（calc_news_window）。
      - 1チャンク当たり最大銘柄数（_BATCH_SIZE=20）、1銘柄当たりの最大記事数/文字数制限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
      - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code と score の検証、スコアクリップ）。
      - 部分失敗に備え、取得できたコードのみ DELETE→INSERT で置換（既存スコアの保護）。
      - テスト容易性のため _call_openai_api を patch 可能に実装。
  - kabusys.ai.regime_detector:
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - ma200_ratio の計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）と、マクロ記事抽出・OpenAI 呼び出し・リトライ処理の実装。
    - 合成スコアのクリップ、しきい値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment = 0.0 とするフェイルセーフ。

- Research（ファクター計算 / 特徴量解析）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算（データ不足ハンドリング）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/欠損時は None）。
    - 設計上 DuckDB の SQL ウィンドウ関数を活用し、外部API呼び出しは行わない。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定日からの将来リターンを任意ホライズン（デフォルト [1,5,21]）で計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（3件未満は None）。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸めで ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。

### Changed
- （初期リリースのため過去変更なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Notes / Design decisions
- ルックアヘッドバイアス回避:
  - AI・リサーチ処理は内部で datetime.today() / date.today() を参照しない。全て外部から渡される target_date に基づいて処理を行う設計。
- DuckDB 互換性:
  - executemany の空リスト制約（DuckDB 0.10 等）に配慮した実装が行われている（空チェックを事前に行う等）。
- OpenAI 呼び出し:
  - JSON Mode を使用し、API レスポンスのパース失敗や API エラー時はフェイルセーフ（スコア 0.0 やスキップ）で継続する実装。
  - 再試行ロジック（429/ネットワーク断/タイムアウト/5xx）を組み込み、5xx 以外の APIError はリトライ対象外。
- .env 読み込み:
  - プロジェクトルート探索は __file__ ベースで行うため、CWD に依存しない挙動を実現。
  - .env.local は .env 上書き（override=True）で扱う。OS 環境変数は protected として上書きを防止。
- テスト支援:
  - OpenAI 呼び出し部分は内部関数をモック／パッチ可能に設計（例: unittest.mock.patch）。

### Requirements / 環境変数（主なもの）
- OPENAI_API_KEY: OpenAI 呼び出しに必須（score_news, score_regime は未指定時 ValueError を送出）。
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 各種機能で必須。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化可能。
- デフォルトの DB パスや監視閾値等は Settings クラスのプロパティに設定（例: DUCKDB_PATH, SQLITE_PATH, CPU_THRESHOLD_PCT 等）。

---

今後の項目（例）
- strategy / execution / monitoring の実装と発注ロジックの追加
- CI 用のテスト、型チェック、ドキュメント整備
- ETL の完全実装（pipeline の続き実装と品質チェックルールの追加）

もし実際のリリース日や既存の変更履歴がある場合は、ここに反映する内容（日付・変更種別）を教えてください。これを元に CHANGELOG.md を更新します。