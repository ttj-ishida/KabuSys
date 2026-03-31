CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

[0.1.0] - 2026-03-31
--------------------

Added
- 新規公開: KabuSys 日本株自動売買システムの初回リリース (0.1.0)。
  - パッケージ構成:
    - kabusys.config: 環境変数/設定管理（Settings クラス、.env 自動読み込み機構）
    - kabusys.ai: ニュース NLP と市場レジーム判定（news_nlp, regime_detector）
    - kabusys.data: データ関連ユーティリティ（ETL パイプライン、カレンダー管理 等）
    - kabusys.research: ファクター計算・特徴量探索ユーティリティ
    - public __all__ に data, strategy, execution, monitoring を提供（トップレベル公開）
- 環境設定 (kabusys.config)
  - Settings クラスを通じて各種必須環境変数を取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - データベース既定パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - システム環境: KABUSYS_ENV (development / paper_trading / live)、LOG_LEVEL（DEBUG/INFO/…）の検証。
  - .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）を探索し、OS環境 > .env.local > .env の優先順で読み込み。既存 OS 環境は保護（上書き不可）。自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式、クォート／エスケープ、インラインコメント処理に対応。無効行は無視。

- ニュース NLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約し OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む。
  - バッチ処理: 最大 20 銘柄/コール、銘柄毎に最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 再試行とフォールバック: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ、失敗時は該当チャンクをスキップ。レスポンス検証に失敗した銘柄は無視。
  - レスポンス検証: JSON パース、"results" 配列、各要素の code/score 型チェック、未知コード無視、スコアは ±1.0 にクリップ。
  - テスト用フック: _call_openai_api を unittest.mock.patch で差し替え可能。
  - ルックアヘッドバイアス対策: 内部で datetime.today() を参照せず、必ず target_date を使用。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
  - マクロニュース抽出: raw_news からマクロキーワードでフィルタ。記事が空の場合は LLM 呼び出しをスキップし macro_sentiment=0 とする。
  - OpenAI 呼び出しは専用の内部実装を使用（news_nlp とは独立）。
  - API 失敗やパース失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
  - レジームスコアはクリップされ、閾値により 'bull' / 'neutral' / 'bear' を判定。
  - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作。失敗時は ROLLBACK を試行し例外を上位に伝播。

- データプラットフォーム（kabusys.data）
  - pipeline.ETLResult: ETL 実行結果を表す dataclass（取得数・保存数・quality_issues・errors 等）と to_dict シリアライゼーション。
  - pipeline モジュール: ETL の差分更新・保存（jquants_client 経由、Idempotent 保存想定）・品質チェック（quality モジュールとの連携）を想定した実装骨格。
  - calendar_management:
    - JPX カレンダー管理、営業日判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・健全性チェック含む）。
    - market_calendar が未取得の際は曜日ベースでフォールバック（週末を休場扱い）。
    - 最大探索範囲やバックフィル等の安全装置あり（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value: DuckDB の prices_daily / raw_financials を用いてモメンタム / ボラティリティ / バリュー系ファクターを計算。結果は (date, code) ベースの dict リストで返す。データ不足時は None を返す設計。
    - 計算窓や定数は定義済み（例: MA200=200, ATR=20 等）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（1〜252）を実施。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効レコード 3 未満で None）。
    - rank: 同順位は平均ランクで処理（float の丸め誤差考慮）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - kabusys.research パッケージは kabusys.data.stats.zscore_normalize を再エクスポート。

Other notable implementation details
- DuckDB を主要なデータストアとして想定（接続は関数に注入して使用）。
- SQL 実行結果を直接使用する設計（複雑な外部ライブラリには依存しない）。
- トランザクション制御とエラーハンドリングを重視（ROLLBACK, WARN ログ）。
- 実運用を想定したログ・検証・フェイルセーフの設計（APIエラー、データ不足、部分失敗保護）。
- DuckDB の executemany に対する互換性対策（空リスト送信不可の回避）。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Security
- 外部 API キー（OpenAI など）は引数経由で注入可能。環境変数に依存する場合は明示的にエラーを出す。

Notes for users / migration
- OpenAI API キー: score_news / score_regime を呼ぶ際は api_key 引数にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定の場合は ValueError を送出します。
- 必須環境変数の未設定時は Settings のプロパティアクセスで ValueError が発生します。.env.example を参考に .env を用意してください。
- DB テーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を事前に用意することが想定されています。
- LLM の出力は厳密な JSON を期待するため、カスタムプロンプトやモデル差分によりパースエラーが発生する可能性があります。テスト時は _call_openai_api をモックしてください。

今後の予定（未実装 / 検討事項）
- strategy / execution / monitoring の詳細実装（パッケージ公開トップに __all__ はあるが、今回のスナップショットではコード断片が主に data/research/ai 側に集中）。
- ai モジュールの評価・コスト最適化（バッチ・トークン制御等）。
- より詳細な品質チェックルールと自動モニタリング・アラート連携。

--- 
この CHANGELOG はコードベースの記述・設計コメントから推測して作成しています。実際のリリースノートはリポジトリのコミット履歴やリリース方針に合わせて調整してください。