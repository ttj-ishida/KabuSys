# Changelog

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングに基づいて記載しています。  
このファイルはコードベースの実装内容から推測して作成しています（実装上の設計意図・既知の制約を含む）。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-02
初期リリース。日本株向けの自動売買・データ基盤・研究用ユーティリティ群を実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。モジュール公開: data, strategy, execution, monitoring。
- 設定管理
  - 環境変数・.env 読み込みユーティリティ（kabusys.config）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動 .env ロード。
    - .env / .env.local の読み込み順序をサポート。既存 OS 環境変数を保護する protected 機構。
    - export KEY=val、クォート、エスケープ、行内コメント等に対応した堅牢なパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
  - Settings クラスによるアプリケーション設定公開（J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境検証等）。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - env/log_level のバリデーション（許容値セットの検証）。
    - デフォルト値（KABUSYS_ENV=development, ログレベル INFO、DBパスのデフォルト等）。
- AI（自然言語処理）機能
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて指定ウィンドウ内のニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを算出。
    - タイムウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（DB 比較は UTC naive datetime に変換）。
    - 銘柄あたり記事数・文字数の上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトリム。
    - バッチ化（最大 20 銘柄/リクエスト）、JSON Mode の利用、レスポンスバリデーションとスコアクリッピング（±1.0）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）。API 失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB への idempotent な書き込み（対象コードの DELETE → INSERT）。部分失敗時に既存スコアを保護する実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - マクロセンチメントはニュースタイトルをフィルタして OpenAI で評価（JSON 出力期待、フェイルセーフで macro_sentiment=0.0）。
    - ルックアヘッドバイアス回避の設計：target_date 未満のみを参照、datetime.today() を参照しない。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を元に営業日判定 / next/prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル、健全性チェックを実装）。
  - ETL パイプライン基盤（pipeline, etl）
    - ETLResult データクラスによる ETL 実行結果の集約（品質問題・エラーメッセージの列挙、has_errors 判定等）。
    - 差分取得/バックフィル/品質チェック/保存の設計方針を盛り込んだパイプライン実装（jquants_client と quality モジュールを利用）。
- リサーチ（kabusys.research）
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算（prices_daily / raw_financials を参照）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None を返す）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（不足時は None）。
    - calc_value: raw_financials から最新財務データを参照し PER / ROE を算出。
    - 計算は DuckDB 上の SQL ウィンドウ関数を活用して効率的に実装。
  - feature_exploration: 将来リターン計算 / IC（スピアマン）計算 / ランク変換 / ファクター要約統計を提供。
    - calc_forward_returns: 指定 horizon の将来リターンを一度のクエリで取得（horizons の検証あり）。
    - calc_ic: factor と forward を code で結合してスピアマン ρ を算出（有効レコード数が少ない場合 None を返す）。
    - rank: 同順位は平均ランクを返す（丸め処理で ties の扱いを安定化）。
    - factor_summary: count/mean/std/min/max/median を standard-library のみで算出。
- ロギング・堅牢性
  - 各モジュールで詳細な logger を利用し、警告・情報を出力。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）と ROLLBACK 失敗時の警告処理。
  - OpenAI 呼び出しの例外ハンドリングと再試行、及びレスポンスの堅牢なパース。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Known limitations / Notes
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を利用する。未設定時は ValueError を送出する実装（呼び出し側で設定必須）。
- news_nlp と regime_detector はそれぞれ独自の _call_openai_api 実装を持ち、モジュール間で private 関数を共有しない設計。
- DuckDB のバージョン依存（executemany に空リスト不可等）を考慮した実装が含まれるため、DuckDB の古い/将来バージョンでの挙動確認が必要。
- calendar_update_job や ETL 実行は外部 J-Quants クライアントに依存するため、実行環境での API 認証情報と接続確認が必要。
- News 時間ウィンドウは JST ベースで定義され、DB 比較は UTC naive datetime を前提としている（タイムゾーン混在に注意）。

---

参考: パッケージの主な必須環境変数
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能）  
デフォルトの DB パス等は Settings クラスのプロパティを参照してください（duckdb: data/kabusys.duckdb, sqlite: data/monitoring.db など）。