Keep a Changelog
================

すべての注目すべき変更をこのファイルに記録します。慣例に従い、変更は "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security" のカテゴリで分類します。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

初回リリース。日本株自動売買システム "KabuSys" の基礎機能をまとめて公開します。

Added
- パッケージ基盤
  - パッケージバージョン: 0.1.0 を定義（kabusys.__version__）。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に一部を定義）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出し、CWD 非依存で .env を読み込む。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - 単/重引用符内のエスケープ処理対応。
    - コメント処理（クォートあり/なしの挙動差別化）。
  - 自動ロードの制御: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - 環境変数保護: OS 環境変数は protected として .env の上書きを防止（.env.local は override）。
  - Settings クラスでアプリ設定をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルトの DB パスを設定（DUCKDB_PATH, SQLITE_PATH）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック。
- データモジュール（kabusys.data）
  - ETL パイプライン型 ETLResult を公開（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - market_calendar 管理（kabusys.data.calendar_management）
    - 営業日判定ユーティリティ: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB 登録値優先で未登録日は曜日ベースのフォールバック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存ロジック（バックフィル、健全性チェック含む）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存、品質チェックを想定した ETLResult データクラスとユーティリティ。
    - テーブルの最終日取得、存在チェック等の補助関数を実装。
- 研究モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン・200日MA乖離の計算。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: PER, ROE の計算（raw_financials を参照）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 複数ホライズンの将来リターン取得（デフォルト [1,5,21]）。
    - calc_ic: スピアマン順位相関（IC）計算。
    - rank: 同順位の平均ランク対応。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計ユーティリティ。
  - zscore_normalize は kabusys.data.stats から再利用（エクスポート）。
- AI / NLP モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄別に記事をまとめ、OpenAI（gpt-4o-mini）でセンチメント評価。
    - JSON Mode を使った厳密なレスポンス期待とレスポンス検証ロジックを実装（_validate_and_extract）。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事最大数・文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ。
    - スコアの ±1.0 クリップ、部分成功時に既存データを保護するため該当 code のみ DELETE→INSERT を実行（トランザクション）。
    - calc_news_window: JST を基準としたニュース集計ウィンドウ計算（前日15:00〜当日08:30 JST を UTC に変換）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。
  - マーケットレジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - マクロキーワードフィルタで raw_news から対象記事を抽出、LLM（gpt-4o-mini）で macro_sentiment を算出し、スコア合成。
    - API 失敗時は macro_sentiment=0.0 としてフェイルセーフ継続。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- 設計上の注意点（ドキュメント化）
  - ルックアヘッドバイアス防止: datetime.today() / date.today() を AI モジュールやファクター計算内部で参照しない設計（target_date 明示）。
  - DuckDB に対する互換性配慮（executemany の空リスト回避等）。
  - ID・APIキーは関数引数で注入可能（テスト容易性と安全性向上）。
  - ロギングの充実と警告・例外時のフェイルセーフ挙動。

Fixed
- .env 読み込み時のファイルオープン失敗を warnings.warn で報告（読み込みを継続可能に）。
- News / Regime モジュールの OpenAI 呼び出しでの各種 API エラー（RateLimit, Timeout, Connection, 5xx）に対するリトライ実装と安全なフォールバック。

Breaking Changes
- 初回リリースのため該当なし。

Known issues / Notes
- AI 機能の利用には OpenAI API キー（OPENAI_API_KEY）が必要。関数は api_key 引数または環境変数を参照し、未設定時は ValueError を送出する。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OPENAI_API_KEY は AI 処理時に必要
- DuckDB 側に期待するテーブル（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）は事前にスキーマ準備が必要。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を利用する想定。API 例外は catch され、0 を返す設計。
- JSON Mode（OpenAI の response_format）を前提としたパース実装のため、将来 SDK やモデルの仕様変更があった場合は対応が必要。
- 一部処理は DuckDB のバージョンや実行環境に依存する（例: list 型バインドの挙動など）。

ライセンス、貢献、問い合わせ等の情報はプロジェクトルートのドキュメントを参照してください。