# Changelog

すべての非互換的な変更は Breaking Changes に、追加・修正はそれぞれ該当セクションに記載します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

現在日付: 2026-04-09

## [Unreleased]
- (なし)

## [0.1.0] - 2026-04-09
初回リリース。パッケージのコア機能（データ取得・ETL、マーケットカレンダー、ファクター計算、ニュースNLP・市場レジーム判定、設定管理など）を実装・公開。

### Added
- 基本パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名・バージョンを定義（__version__ = "0.1.0"）。
  - モジュール公開対象に data, strategy, execution, monitoring を含める。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
    - .env パーサー実装（コメント・export 形式・クォート／エスケープ対応）。
    - OS 環境変数を保護する protected オプション、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスで各種設定をプロパティ化（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_*、DB パス、Paper Trading 設定、監視しきい値、KABUSYS_ENV/LOG_LEVEL の検証など）。
    - 設定値検証（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL の許容値チェック）。

- ニュースNLP（AI）機能
  - src/kabusys/ai/news_nlp.py
    - OpenAI (gpt-4o-mini) を用いたニュースセンチメント解析（JSON Mode）実装。
    - タイムウィンドウ計算（JST ベースの前日 15:00～当日 08:30 を UTC に変換）。
    - raw_news と news_symbols から銘柄ごとに記事を集約（最大記事数・文字数を制限）。
    - バッチ処理（最大 20 銘柄/コール）、リトライ（429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ）。
    - レスポンス検証ロジック（JSON 抽出、results の形式検証、コード照合、スコア数値チェック、スコア ±1.0 クリップ）。
    - DuckDB の ai_scores テーブルへ冪等的に書き込む（該当コード群のみ DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
    - ロギングによる情報・警告出力。

  - src/kabusys/ai/__init__.py で score_news を公開。

- 市場レジーム判定（AI + テクニカル合成）
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news / market_regime を参照し、DuckDB へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出しは独立実装（news_nlp とプライベート関数を共有しない設計）。
    - API エラーやパースエラーに対するフォールバック（macro_sentiment = 0.0）とリトライ処理。
    - ルックアヘッドバイアス防止のため、target_date 未満のデータのみを使用。

- データプラットフォーム関連
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理（market_calendar テーブル）と営業日ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫性のある設計。
    - calendar_update_job: J-Quants クライアントを用いた差分取得・バックフィル（直近の日付を再取得）・保存処理。健全性チェック（将来日付の異常検出）を実装。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）などで無限ループ防止。

  - src/kabusys/data/pipeline.py
    - ETL パイプライン設計（差分更新、保存、品質チェックのフロー記述）。
    - ETLResult データクラス定義（取得件数・保存件数・品質問題・エラー一覧などを含む）。
    - ETLResult.to_dict() による品質問題の辞書化サポート。
    - 品質チェックでのエラー継続方針（Fail-Fast とせず呼び出し元に判断を委譲）。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。

  - jquants_client / quality 等外部モジュールとの連携を想定（DuckDB を主な永続層として利用）。

- リサーチ機能
  - src/kabusys/research/factor_research.py
    - ファクター計算: calc_momentum（1M/3M/6M リターン、200 日 MA 乖離）、calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金・出来高比率）、calc_value（PER, ROE の計算）。
    - DuckDB に対する SQL を主体とした実装（prices_daily / raw_financials のみ参照）。
    - データ不足時の None 扱いとログ出力、結果は (date, code) をキーとする dict リストで返却。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターン）、calc_ic（Spearman のランク相関 / IC）、factor_summary（基本統計量）、rank（同順位は平均ランク）を提供。
    - pandas 等に依存せず標準ライブラリと DuckDB を用いた実装。
    - 入力検証（horizons の範囲制約など）と数理的安定化（丸めや ties 対策）を実装。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats からの再利用）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数注入または環境変数 OPENAI_API_KEY を使用。キー未設定時は ValueError を投げて早期検出。

### Notes / Known limitations
- 外部依存: DuckDB と OpenAI Python SDK を前提としている（インストール・環境設定が必要）。
- news_nlp / regime_detector は OpenAI API のレスポンス依存のため、API 利用コストやレイテンシ・レート制限に注意が必要。
- 一部テーブル名（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等）を前提としている。DB スキーマ準備が必須。
- strategy / execution / monitoring モジュール群はパッケージ公開対象に含めているが、個別実装は本リリースで限定的または他ファイルに分割される想定。
- 将来的な改善候補：OpenAI 呼び出しの抽象化（より汎用的なインターフェース）、より詳細な品質チェックルール、テストカバレッジの追加。

---

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット単位や履歴と異なる場合があります。）