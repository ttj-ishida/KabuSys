# Changelog

すべての注目すべき変更点をここに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従います。

# 変更履歴

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を設定。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を安全にロードする自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パーサは export 形式やクォート／エスケープ、インラインコメントの扱いに対応。
    - .env 読み込み時に OS 環境変数を保護するための protected キーセットを採用。
  - Settings クラスを提供し、必須キー取得（_require）や既定値、型変換、バリデーションを実装。
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - DB パスの既定値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（Path.expanduser 対応）。
    - KABUSYS_ENV の許容値チェック（development / paper_trading / live）とログレベルの検証。

- AI（自然言語処理）機能（kabusys.ai）
  - ニュースセンチメント（銘柄単位）スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに記事を統合して OpenAI（gpt-4o-mini）へバッチ送信。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換してクエリ）。
    - バッチサイズ、最大記事数・文字数などのトークン過膨張対策を実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、code/score の検証、未知コードは無視）。
    - スコアは ±1.0 にクリップ。取得済みコードのみを DELETE → INSERT で冪等的に更新。
    - DuckDB（互換性）考慮: executemany に空リストを渡さない実装で部分失敗時に既存スコアを保護。
    - テストしやすさのため、OpenAI 呼び出し関数（_call_openai_api）をパッチ可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、
      日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み。
    - マクロキーワードで raw_news をフィルタして記事タイトルを抽出し、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - API エラー時のフェイルセーフ: macro_sentiment = 0.0 として継続。
    - レジーム計算はクリップ・閾値設定（_BULL_THRESHOLD, _BEAR_THRESHOLD）付き。
    - DuckDB トランザクション（BEGIN / DELETE / INSERT / COMMIT）による冪等保存。ROLLBACK の失敗時にログ出力。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理のロジックを実装（market_calendar 参照・フォールバック）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバックする一貫した振る舞いを実装。
    - 夜間バッチ calendar_update_job を実装し、J-Quants から差分取得して保存（バックフィル・健全性チェック付き）。
    - 最大探索日数やバックフィル日数等の定数で無限ループや極端値を回避。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧など）を一元管理。
    - 差分更新・バックフィル・品質チェックの設計方針に従ったユーティリティを実装。
    - jquants_client と quality モジュールを組み合わせた差分取得 → 保存 → 品質チェックの基本フローを提供。
    - デフォルトのバックフィル日数やカレンダー先読み設定等を定義。
    - etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、ma200_dev）、Value（PER、ROE）、Volatility（20日 ATR）などの定量ファクターを実装。
    - DuckDB 上で SQL を用いた効率的な集約計算を実装。データ不足時の None ハンドリング。
    - 各関数は prices_daily / raw_financials テーブルのみを参照（発注 API 等にはアクセスしない）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）までのリターンを一括取得する SQL 実装。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を自前実装で算出、サンプル不足時は None を返す。
    - ランク関数（rank）: 同順位（ties）を平均ランクで処理。丸めによる ties 検出の安定化処理あり。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出するユーティリティ。
  - research パッケージの __all__ に主要関数を公開。

### Design / Notes
- ルックアヘッドバイアス防止
  - AI モジュールやリサーチモジュールの主要関数は内部で datetime.today() / date.today() を参照しない設計。すべて target_date を明示的に受け取り、DB クエリにも target_date 未満 / 以前の条件を適用して先見バイアスを排除。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）呼び出しが失敗した場合にも、致命的例外をその場で投げずにフェイルセーフ動作や警告ログで継続する設計を多くの箇所で採用。
- テスト容易性
  - OpenAI 呼び出し等はモジュール内の関数を介して行うため、unit test で簡単に patch / mock 可能。
- DuckDB 互換性
  - executemany に空リストを渡すと問題になる DuckDB の挙動を考慮して空パラメータ時の処理分岐を実装。

### Fixed
- （初版のため該当なし）

### Changed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

---

注: 上記はコードベースの実装内容から推測して記載しています。外部 API モジュール（例: kabusys.data.jquants_client）や strategy / execution / monitoring の具体実装は本断片には含まれていないため、CHANGELOG では主要な実装ファイルと設計方針を中心に記載しました。