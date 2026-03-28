# Changelog

すべての重要な変更を記録します。This project adheres to Keep a Changelog の形式で管理します。  
初回公開: 0.1.0

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - ルートパッケージのバージョンを __version__ = "0.1.0" として公開。
  - パッケージの公開インターフェースとして data, strategy, execution, monitoring を __all__ に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダー実装。
    - 読み込み優先度: OS環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
    - .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。
  - .env パース実装の追加:
    - export PREFIX=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に。
    - 必須環境変数は _require() により未設定時に ValueError を送出。
    - サポートされる環境: development / paper_trading / live（KABUSYS_ENV）。
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - デフォルトの DB パス（DUCKDB_PATH: data/kabusys.duckdb、SQLITE_PATH: data/monitoring.db）を提供。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント (news_nlp.score_news)
    - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) に JSON mode で送信し、銘柄ごとのセンチメント(ai_scores) を算出して書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST 相当（UTC に変換）。
    - バッチ処理: 1 API 呼び出しで最大 20 銘柄（_BATCH_SIZE=20）。
    - 1 銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他はスキップして続行。
    - レスポンス検証: JSON パース、"results" の存在、code と score の型検証、未知コードは無視、スコアは ±1.0 にクリップ。
    - 部分成功を想定した DB 書き込み: 成功したコードのみ DELETE → INSERT（部分失敗時に既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出し関数をパッチ差し替え可能（unittest.mock.patch 対応）。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出・保存。
    - MA200 の算出は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロセンチメントは news_nlp の窓計算を利用して取得したタイトル群を LLM で評価（gpt-4o-mini、JSON mode）。
    - API 失敗やパース失敗時は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
    - 返却・保存は冪等 (BEGIN / DELETE / INSERT / COMMIT)。
    - テスト用に OpenAI 呼び出しを差し替え可能。

- データプラットフォーム (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar テーブルの夜間更新ジョブ calendar_update_job を実装（J-Quants API 経由で差分取得 → 保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB がまばらな場合の曜日ベースフォールバック、最大探索日数制限による安全策を導入。
    - 保存や取得に対する健全性チェック（backfill, sanity checks）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（kabusys.data.etl は ETLResult を再エクスポート）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）を想定した設計。
    - 市場データ開始日定義、デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティを実装。
    - ETLResult.to_dict() で品質問題をシリアライズ可能。

- 研究モジュール (kabusys.research)
  - factor_research:
    - モメンタム (1M/3M/6M)、200 日移動平均乖離 (ma200_dev) を計算する calc_momentum。
    - ボラティリティ/流動性 (ATR20, 相対ATR, 平均売買代金, 出来高比率) を計算する calc_volatility。
    - バリュー (PER, ROE) を raw_financials と prices_daily を組み合わせて算出する calc_value。
    - DuckDB を用いた SQL ベースの実装で、外部 API にはアクセスしない設計。
  - feature_exploration:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）。
    - IC 計算 calc_ic（Spearman 的ランク相関）。
    - ランク関数 rank（同順位は平均ランク）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。

### Changed
- 設計方針の明文化
  - ルックアヘッドバイアスを避けるため、各 AI/研究関数は内部で datetime.today()/date.today() を直接参照せず、target_date を外部から受け取る設計。
  - OpenAI 呼び出しはモジュールごとに private 関数として定義し、モジュール間で内部関数を共有しない（結合を低減）。
  - DuckDB の互換性考慮:
    - executemany へ空リストを渡さないガードを挿入（DuckDB 0.10 の制約回避）。
    - list 型バインドの不安定さ回避のため DELETE/INSERT を executemany で個別実行。

- エラーハンドリング改善
  - OpenAI API の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対してリトライ・バックオフ戦略を導入。
  - API の 5xx とそれ以外を区別してリトライ可否を判定。
  - JSON パース失敗時にレスポンス文字列から最外の {} を抽出して再パースするフォールバックロジックを追加。

### Fixed
- 部分失敗時のデータ損失回避
  - news_nlp.score_news と regime_detector.score_regime の DB 書き込みで、部分失敗があっても既存データを不必要に削除しないように DELETE 範囲を最小化／個別実行する実装に修正。
  - トランザクション失敗時の ROLLBACK を試行し、ROLLBACK 自体の失敗を警告ログで記録。

### Security
- 環境変数の保護
  - .env 読み込み時に OS 環境変数を protected set として扱い、意図せぬ上書きを防止。

### Notes / Usage
- OpenAI API キーは api_key 引数で注入可能。未指定の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。
- 必須の環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パスや挙動、各種定数はソース内の定義を参照してください。
- テスト容易性のため、OpenAI 呼び出しや sleep 等をモック/パッチ可能な設計になっています。

---

今後のリリースでは、strategy / execution / monitoring の各サブパッケージの実装や、より詳細な品質チェック、ユニットテスト・統合テストの充実、CI/CD 周りの改善を予定しています。