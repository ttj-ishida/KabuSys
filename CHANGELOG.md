CHANGELOG
=========
すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン
----------------
0.1.0 - 2026-03-31

Added
-----
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルート: src/kabusys/__init__.py により公開モジュールを定義（data, research, ai, monitoring 等のサブパッケージを想定）。
- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス、クォートとエスケープ、インラインコメント処理、無効行スキップなどに対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / システム環境（KABUSYS_ENV）などのプロパティ経由で取得可能。
  - 必須環境変数未設定時は ValueError を送出する _require() を実装。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（development / paper_trading / live、DEBUG..CRITICAL）。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを取得して ai_scores テーブルへ書き込む score_news(conn, target_date, api_key=None) を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で算出。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン対策（記事最大文字数トリム）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の安全な DB 更新（DELETE→INSERT）をサポート。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ）を実装し、失敗時は該当チャンクをスキップして他チャンクは継続。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api のパッチが可能）。
  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定する score_regime(conn, target_date, api_key=None) を実装。
    - マクロニュース抽出（マクロキーワードによるタイトルフィルタ）、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を計算、MA 比率との加重合成、閾値に基づくラベル（bull/neutral/bear）決定を実装。
    - API 失敗時は macro_sentiment=0.0 でフォールバックする安全設計、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を備える。
- データプラットフォームユーティリティ (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を利用した営業日判定や next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を実装。
    - DB 未取得時は曜日ベース（土日休み）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS 日）・健全性チェック・冪等保存を可能にする設計。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質検査結果・エラー）を構造化して返却可能に。
    - パイプライン設計方針とユーティリティ関数（テーブル存在確認や最大日付取得など）を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - jquants_client / quality などの外部クライアントを利用する想定（fetch/save 関数呼び出し部分は依存注入や例外ハンドリングで保護）。
- リサーチ・ファクター分析 (kabusys.research)
  - factor_research モジュール
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER、ROE）を計算する SQL ベース実装（DuckDB）。
    - データ不足時は None を返す仕様。
  - feature_exploration モジュール
    - calc_forward_returns（任意ホライズンの将来リターンをまとめて取得）、calc_ic（スピアマンのランク相関 / IC）、rank（同順位は平均ランクの実装）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を使わず標準ライブラリ + DuckDB SQL で実装。
- ロギング・エラーハンドリング
  - 各モジュールは詳細ログ（logger）を出力し、API 呼び出し失敗やパース失敗時は警告ログを出してフォールバックする設計になっている。
- テスト支援
  - OpenAI 呼び出しや時間依存処理を差し替え／モック可能な実装（関数分離）にしてユニットテストしやすくしている。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Removed
-------
- （初回リリースのため該当なし）

Security
--------
- OpenAI API キーや各種秘密情報は Settings を通じて環境変数で提供する設計。必須キー未設定時は明示的にエラーを返す。
- .env 自動ロード時に既存 OS 環境変数は保護される（.env.local は override 可能だが OS 環境変数は上書きされない）。

注意事項 / 既知の制約
--------------------
- OpenAI（gpt-4o-mini）への依存: 実行には OPENAI_API_KEY が必要。api_key 引数で明示的に渡すことも可能。
- DuckDB を想定した SQL を多用しており、prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等のテーブル構造が前提。
- 一部の DB バインド（DuckDB の executemany の空パラメータ制約など）に配慮した実装になっているため、他 DB へ移植する場合は注意が必要。
- すべての関数は「ルックアヘッドバイアス防止」のため datetime.today()/date.today() を内部で直接参照しない方針（target_date を明示的に与える設計）。
- LLM レスポンスの不確実性（JSON の前後余計なテキスト等）に対し復元ロジックやフォールバックを実装しているが、レスポンス仕様の大幅な変更は影響を与える可能性あり。

今後の予定（例）
----------------
- ドキュメントの拡充（API 使用例、DB スキーマ仕様、ETL ワークフロー）
- 追加のファクタ（PBR、配当利回り等）やモジュールの性能改善
- 外部サービス呼び出しのリトライ・監視を更に強化

--- 
（この CHANGELOG はソースコードの実装内容から推測して作成しています。詳細な変更履歴はコミット履歴やリリースノートと照合してください。）