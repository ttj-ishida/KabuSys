# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース v0.1.0 を記録します。

なお、日付はパッケージの __version__ とコード内容に基づいて推定しています。

## [Unreleased]

## [0.1.0] - 2026-03-27

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロードの探索はパッケージファイル位置から .git または pyproject.toml を起点にプロジェクトルートを特定するため、カレントディレクトリに依存しない挙動。
  - .env パース機能を実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理を考慮）。
  - 自動ロードの挙動を抑止する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途想定）。
  - Settings クラスを提供し、以下の設定プロパティをサポート：
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN、SLACK_CHANNEL_ID
    - DUCKDB_PATH、SQLITE_PATH（デフォルトパスを指定）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live, is_paper, is_dev の便利プロパティ
  - 必須キー未設定時は明確な ValueError を発生させる挙動。

- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄単位のセンチメントスコアを算出。
    - 時間ウィンドウは JST 前日 15:00 ～ 当日 08:30 を基に UTC に変換して処理。
    - バッチ処理: 最大 20 銘柄／回、1銘柄あたり最大 10 記事・3000 文字でトリム。
    - API 呼び出しに対するリトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score の検証、スコアの有限性検査）。
    - スコアは ±1.0 にクリップ。取得したコードのみ ai_scores テーブルへ置換（DELETE → INSERT）して部分失敗時に既存データを保護。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
    - ログ出力により処理状況を通知。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）とマクロニュースの LLM センチメントを重み付け（MA 70%、マクロ 30%）して日次で market_regime を判定。
    - マクロニュースのフィルタリングに複数キーワードを使用（日本／米国・グローバルの主要キーワード群）。
    - OpenAI 呼び出し（gpt-4o-mini）を行い、失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - レジームスコアをクリップし閾値により "bull" / "neutral" / "bear" を決定。
    - market_regime テーブルへの冪等的な書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を実装。
    - API キーは引数から注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定だと ValueError を投げる。

- データプラットフォーム / カレンダー（src/kabusys/data/calendar_management.py）
  - JPX カレンダー取り扱い機能:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar テーブルがある場合は DB 値を優先し、未登録日は曜日（土日）ベースでフォールバックする一貫したロジック。
    - 最長探索日数の上限を設けて無限ループを防止。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得・バックフィル（直近 _BACKFILL_DAYS 再取得）して market_calendar を更新する処理を提供。健全性チェック（未来日が極端にある場合のスキップ）を実装。
    - market_calendar が存在しない / データがない場合のフォールバック動作を明記。

- ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
  - ETL 実行結果を表す ETLResult dataclass を実装（取得件数、保存件数、品質チェック結果、エラーリスト等）。
  - 差分更新のためのユーティリティ関数（テーブル存在確認、最大日付取得等）を提供。
  - jquants_client と quality モジュールを用いた差分フェッチ・保存・品質チェック設計に沿ったインターフェースを用意。
  - etl.py で ETLResult を再エクスポート。

- Research（src/kabusys/research）
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターンおよび ma200_dev（200日移動平均乖離）を算出。
    - calc_volatility: 20日 ATR、ATR/価格（atr_pct）、20日平均売買代金、出来高比率など。
    - calc_value: raw_financials と当日価格から PER / ROE を算出（EPS=0/欠損は None）。
    - DuckDB の SQL ウィンドウ関数を活用した実装。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク化ユーティリティ。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。
  - いずれも外部ライブラリ（pandas 等）に依存せず標準ライブラリ＆DuckDB で実装。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 設定値のバリデーションを導入（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。不正な値は ValueError で明示的に拒否。

### Notes / 設計上の重要事項
- LLM 呼び出しは外部サービス依存部分として扱い、API エラーやパース失敗時に例外を投げずフェイルセーフ（スコア0や処理スキップ）で継続する設計を採用。これにより一部の API 障害が全体バッチを停止させないよう配慮。
- DB 書き込みは冪等性を重視（対象 date / code 切り替えの DELETE → INSERT 方式）し、部分失敗時に既存データを保護するロジックを採用。
- ルックアヘッドバイアス防止のため、いずれのモジュールも内部で datetime.today() / date.today() に依存しない設計（関数引数として target_date を受け取る）。
- テスト容易性を考慮し、OpenAI 呼び出し部分は内部関数をモックできるようにしている。

--- 

初期リリースのため「追加」事項を中心に記録しています。次回以降の変更では「Changed」「Fixed」「Deprecated」「Removed」「Security」などのカテゴリを適宜使用して詳細に記録してください。