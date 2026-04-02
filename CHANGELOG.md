# Keep a Changelog

すべての重要な変更を日付順に記録します。フォーマットは Keep a Changelog に準拠します。  
このファイルはリポジトリのコードベースから推測して生成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-02

初回リリース。日本株自動売買/データ基盤の基礎的なモジュール群を実装しました。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - パブリックモジュール: data, strategy, execution, monitoring（__all__ にて公開。strategy/execution/monitoring の実装は別途）

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない
    - 読み込み順序: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）
  - .env のパース実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープに対応
    - インラインコメント判定の細かなルール対応
  - _load_env_file による上書き制御（override）と保護キー（protected）機能
  - Settings クラスを提供（settings = Settings()）
    - J-Quants / kabuステーション / Slack / データベース / 監視 / システム関連のプロパティを定義
    - 必須環境変数は _require で明示的にチェック（未設定時は ValueError）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - パス類は Path 型で返却（expanduser 実施）

- データ基盤: ETL / パイプライン (kabusys.data.pipeline, kabusys.data.etl)
  - ETLResult データクラスを実装（ETL 実行結果の集約、品質問題・エラーの記録、辞書変換メソッド to_dict）
  - 差分取得 / バックフィル / 品質チェックの設計方針を反映（実装は pipeline モジュールのインターフェース）
  - DuckDB を前提にしたテーブル有無チェック・最大日付取得などユーティリティを実装（互換性考慮あり）

- マーケットカレンダー管理 (kabusys.data.calendar_management)
  - JPX カレンダー管理用ロジック（market_calendar テーブルに基づく）
  - 営業日判定 API:
    - is_trading_day(conn, d)
    - is_sq_day(conn, d)
    - next_trading_day(conn, d)
    - prev_trading_day(conn, d)
    - get_trading_days(conn, start, end)
  - calendar_update_job: J-Quants API から差分取得して market_calendar を idempotent に更新する夜間バッチジョブ
    - バックフィル、先読み、健全性チェック（将来日付上限）を実装
  - DB データが不十分な場合の曜日ベースのフォールバック実装（安全設計）
  - 最大探索範囲を設定して無限ループを防止

- リサーチ/因子計算 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200日 MA 乖離などを計算
    - calc_volatility(conn, target_date): 20日 ATR, 相対 ATR, 平均売買代金, 出来高比率 等を計算
    - calc_value(conn, target_date): PER, ROE（raw_financials を利用）
    - 設計上、prices_daily / raw_financials のみ参照し外部 API に依存しない
    - データ不足時は None を返す設計
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons): 翌日/翌週/翌月など将来リターンを計算（ホライズンの検証あり）
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算
    - rank(values): 同順位を平均ランクにするランク化実装（丸めを用いて tie 判定安定化）
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー
  - kabusys.research.__init__ にて zscore_normalize（kabusys.data.stats 由来）を再エクスポート

- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - score_news(conn, target_date, api_key=None): raw_news を集約して OpenAI (gpt-4o-mini, JSON mode) にバッチ送信し、銘柄別 ai_scores を更新
    - calc_news_window(target_date): JST 基準のニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）の計算
    - バッチ処理: 1回あたり最大 20 銘柄、1銘柄あたり最大記事数・最大文字数でトリム
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）
    - レスポンス検証: JSON の抽出/パース / results リスト / code の整合性 / スコア数値性を検証。問題時は該当チャンクをスキップ
    - DuckDB の executemany の仕様差異を考慮し、空リスト挿入を回避するガードを実装
    - テスト容易性のため _call_openai_api を patch 可能に設計
  - kabusys.ai.regime_detector:
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（LLM, 重み 30%）を合成して market_regime を書き込む
    - マクロニュース取得は kabusys.ai.news_nlp.calc_news_window を利用して raw_news のタイトルを抽出
    - LLM 呼び出しは独立実装（モジュール結合を避ける）
    - API エラー・パース失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実施
    - OpenAI クライアントには OpenAI(api_key=...) を利用し、JSON mode で結果を要求

- OpenAI 連携
  - 共通設計:
    - デフォルトモデル: gpt-4o-mini
    - JSON mode を利用して厳密な JSON 出力を期待
    - API キーは関数引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出
    - リトライ／バックオフの標準化（最大リトライ回数・指数バックオフ）
    - テスト用に _call_openai_api の差し替えを想定

- DuckDB 前提の設計
  - 多くのモジュールが DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、prices_daily / raw_news / raw_financials / market_calendar / ai_scores / news_symbols など既定テーブルを参照・更新するよう設計
  - DuckDB バージョンによる executemany の挙動差異に対する注意点（空リスト挿入回避）を実装

### Fixed
- なし（初回リリース）

### Changed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし（初回リリース）。ただし OpenAI API キー等の機密情報は環境変数管理を前提としており、.env をリポジトリに含めない運用を想定。

---

注意 / 既知の設計上の振る舞い（ユーザ向けメモ）
- OpenAI の呼び出しに失敗した場合でも処理を続行するフェイルセーフ設計が多くの箇所で採用されています（例: macro_sentiment=0.0、チャンクのスキップ）。運用時はログを確認してください。
- settings は必須環境変数を参照すると即座に ValueError を投げます。デプロイ前に .env/.env.local または OS 環境に必要なキーを設定してください。
- news_nlp / regime_detector は gpt-4o-mini の JSON mode を前提にパース処理を行っています。モデルやレスポンス形式が変わるとパースに失敗します。
- DuckDB のスキーマ（テーブル名・カラム）が期待通りであることが前提です。schema の変更は各モジュールのクエリを更新する必要があります。
- strategy / execution / monitoring 等のモジュールは __all__ に記載がありますが、本リリースに含まれる実装は上記のデータ・研究・AI 中心のモジュール群です。運用ロジックや実際の発注周りは別途実装／統合が必要です。

（この CHANGELOG はコードからの推測に基づいて生成しています。実際の変更履歴やリリースノートはリポジトリ運用者の記録を優先してください。）