# Changelog

すべての重要な変更は Keep a Changelog に準拠して記載します。  
このプロジェクトはセマンティックバージョニング（MAJOR.MINOR.PATCH）を採用します。

※ 初回リリースはコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-03
初回リリース

### Added
- パッケージ基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）
  - 自動読み込みを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーの実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープに対応）
  - 環境変数保護（OS環境変数を protected として上書きを制御）
  - Settings クラスを提供（プロパティ経由で設定取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL などの主要設定
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値等
    - 実行環境 / ログレベル検証: KABUSYS_ENV（development/paper_trading/live）, LOG_LEVEL（DEBUG/INFO/...）
    - 便利プロパティ: is_live, is_paper, is_dev
  - 必須環境変数未設定時は明示的な ValueError を送出

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いて銘柄単位にニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得
    - バッチ処理（最大 20 銘柄／チャンク）、記事トリム（最大記事数／文字数）を実装
    - リトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装
    - レスポンスの厳密バリデーション（JSON 抽出、results 配列、コード整合性、数値チェック）
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、DuckDB executemany の空リスト対策あり）
    - calc_news_window ユーティリティ（JST 基準のニュースウィンドウ計算）を提供
    - API キー解決：api_key 引数または環境変数 OPENAI_API_KEY。未設定時は ValueError を送出
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei 225 連動ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news を DuckDB から参照し、結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - OpenAI 呼び出しは独立実装（news_nlp とは関数を共有しない設計）
    - API エラー時は macro_sentiment = 0.0 のフェイルセーフ、最大リトライ回数やリトライ時のログ出力あり
    - LLM 呼び出しで JSON のみを期待するプロンプト設計

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を扱うユーティリティ群:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末は非営業日）
    - 最大探索日数制限（_MAX_SEARCH_DAYS）および健全性チェック、バックフィルの実装
    - calendar_update_job: J-Quants API から差分取得して market_calendar に冪等保存（バックフィル、健全性チェック、例外ハンドリング）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETL の設計概念に基づくユーティリティ群および ETLResult データクラスを提供
    - ETLResult: target_date, 各データの取得・保存件数、品質チェック結果、エラー一覧、to_dict 等
    - 差分取得、バックフィル、品質チェック（quality モジュール経由）、idempotent 保存（jquants_client の save_* を利用）を想定した設計
    - DuckDB テーブル存在チェック・最大日付取得等の内部ユーティリティを実装
  - ETLResult は kabusys.data.etl から再エクスポート

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム: calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - ボラティリティ/流動性: calc_volatility（ATR20、atr_pct、avg_turnover、volume_ratio）
    - バリュー: calc_value（PER、ROE。raw_financials から最新財務を結合）
    - 全関数は DuckDB（prices_daily / raw_financials）を参照し、(date, code) 単位の辞書リストを返す
    - データ不足時の None ハンドリング・ログ出力あり
  - feature_exploration
    - 将来リターン計算: calc_forward_returns（任意ホライズン、入力検証、単一クエリで取得）
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関）
    - ランク変換: rank（同順位は平均ランクで処理、丸めによる tie 対策）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - すべて外部ライブラリに依存せずに標準ライブラリ + DuckDB で実装

### Security
- OpenAI API キーは明示的に要求され、未設定時は ValueError を返す仕様（API キー漏洩のためのログ出力を行わない想定）

### Notes / 設計上の注意点
- ルックアヘッドバイアス回避:
  - date.today(), datetime.today() を直接参照しない設計（関数に target_date を与える方式）
  - prices_daily クエリでは date < target_date や半開区間を採用
- データベース操作:
  - 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT を想定）、トランザクションを使用し例外時は ROLLBACK を試行
  - DuckDB の executemany に対する空リスト制約に留意した実装
- フェイルセーフ:
  - OpenAI 呼び出し失敗時は例外を投げずにフェイルセーフ値（例: macro_sentiment=0.0、スコア取得失敗はスキップ）で継続する設計
- ロギング:
  - 各モジュールで詳細なログ（INFO/WARNING/DEBUG）を出力する実装（障害調査やモニタリングに有用）
- 環境変数パース:
  - .env のパースは Bash 形式の多くのケース（export、クォート、エスケープ、インラインコメント）に対応

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

---

開発・運用者向けの補足:
- 主要な環境変数例:
  - OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
  - DUCKDB_PATH, SQLITE_PATH
  - KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL
  - KABUSYS_DISABLE_AUTO_ENV_LOAD
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提としています。初期導入時はスキーマ整備が必要です。