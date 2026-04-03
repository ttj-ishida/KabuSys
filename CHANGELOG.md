# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルは、ソースコードの内容から推測した初回リリースの変更点・設計意図を日本語でまとめたものです。

フォーマット:
- Added: 新機能や公開 API
- Changed: 実装上の重要な設計・振る舞い
- Fixed: 修正（コードベースから推測される問題対策）
- Notes: 実装上の注意点・設計方針

## [Unreleased]

## [0.1.0] - 2026-04-03
### Added
- 基本パッケージ初期公開
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data / strategy / execution / monitoring を公開（将来的な拡張ポイント）
- 環境設定管理 (kabusys.config)
  - .env ファイルと OS 環境変数の自動読み込み機能を実装
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索
    - 読み込み優先順: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - OS 環境変数の保護（protected keys）をサポート
  - .env 解析実装: export 文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いを考慮
  - 必須環境変数取得ヘルパー _require を提供（未設定時は ValueError）
  - Settings クラスを公開（settings インスタンス）
    - J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティ
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を提供
    - KABUSYS_ENV および LOG_LEVEL の検証（許容値チェック）
    - is_live / is_paper / is_dev のユーティリティ属性
- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し OpenAI (gpt-4o-mini) によるセンチメント評価を実行
    - バッチ処理（最大 20 銘柄 / コール）、1銘柄あたり最大記事数・文字数制限を実装
    - JSON Mode を想定したレスポンス検証とパース、スコアの ±1.0 クリップ
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ
    - スコア取得結果を ai_scores テーブルへ冪等に（DELETE → INSERT）書き込み
    - テスト用に _call_openai_api のモック差し替えを想定
    - 公開関数: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 (日経225連動) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - OpenAI (gpt-4o-mini) を使用、JSON 出力を期待
    - LLM 呼び出しのリトライ・フォールバック実装（API 失敗時は macro_sentiment=0.0）
    - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 公開関数: score_regime(conn, target_date, api_key=None)
- Research モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から EPS/ROE を参照して PER/ROE を計算
    - DuckDB 上での SQL+ウィンドウ関数を利用した実装（prices_daily / raw_financials を参照）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21]）
    - calc_ic: スピアマンランク相関（IC）計算
    - rank: 同順位は平均ランクとするランク関数（round を用いた ties 対策）
    - factor_summary: count/mean/std/min/max/median の集計
  - research パッケージ __all__ に主要関数を公開（zscore_normalize は data.stats から再公開）
- Data モジュール (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装
    - market_calendar がない場合は曜日ベース（週末除外）でフォールバック
    - calendar_update_job により J-Quants からの差分取得 → 保存（バックフィル・健全性チェックを含む）
    - DB 登録値優先、未登録日は曜日ベースの補完で一貫性を確保
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラーの収集）
    - 差分取得・保存・品質チェックの設計を反映（jquants_client, quality モジュールと連携想定）
    - data.etl は ETLResult を再エクスポート
  - jquants_client 関連（モジュール参照あり。外部 API クライアントと連携する設計）
- 監視・実行・ストラテジー領域のためのパッケージ構成（プレースホルダとして __all__ に含む）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / 実装上の重要な設計・挙動
- ルックアヘッドバイアス回避
  - AI モジュール、Research モジュール、ニュースタイムウィンドウ等、すべて target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計を採用
  - DB クエリでは date < target_date や半開区間 [start, end) を使い将来データ参照を防止
- OpenAI 呼び出し
  - gpt-4o-mini を想定（JSON Mode を利用）
  - レスポンスの堅牢なパースと検証（余分な前後テキストのトリミング、型チェック、未知コード無視）
  - テスト容易性のため _call_openai_api をモジュール内で分離しモック可能にしている
- フェイルセーフ
  - LLM の失敗や API エラーは基本的にスキップしてゼロ値（中立）にフォールバックし、パイプライン全体を停止させない設計
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で整合性を保つ
- DuckDB 互換性
  - executemany に空リストを渡さない等、DuckDB のバージョン差を考慮した実装
- タイムゾーン扱い
  - news のウィンドウ計算は JST ベースで定義し DB 比較は UTC naive datetime を用いる仕様（DB 側の日時は UTC 前提）
- 環境変数の取り扱い
  - 主要な環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - OPENAI_API_KEY（各 AI 関数で必須、未設定時は ValueError）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
    - KABUSYS_ENV, LOG_LEVEL（許容値検証あり）
  - .env のパースは比較的寛容だが、キーが空の場合や不正な行は無視する
- ログ出力
  - 各主要処理で情報・警告・例外ログを出力。失敗発生時は stacktrace を残す箇所あり（logger.exception 等）

---

今後の予定（推測）
- strategy / execution / monitoring パッケージの具体実装（発注ロジック・監視・ライン通知等）
- jquants_client / quality / その他データ保存周りの統合テスト・運用向け改良
- セキュリティ向け機能（シークレット管理、より厳格な API エラー分類）
- ドキュメント補完（API 使用例、DB スキーマの明記など）

もし CHANGELOG に特に反映してほしい点（追加の日付、リリースノートの粒度、将来の変更履歴テンプレート等）があれば教えてください。現状のコードから推測できない変更点・コミット単位の履歴は含めていません。