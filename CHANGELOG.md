# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースから推測される初回リリースの変更点・機能一覧を日本語でまとめたものです。

全体方針
- バックテスト・研究用途と実運用（発注）を分離した設計。
- ルックアヘッドバイアス防止のため、内部処理は datetime.today()/date.today() を直接参照せず、すべて target_date 等の明示的引数で日付を扱う。
- DuckDB を主要なローカルデータストアとして使用し、SQL と Python を組み合わせて計算・集計を実装。
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメント評価を実装。API の堅牢性のためリトライ・バックオフ・フェイルセーフを備える。
- .env 自動読み込み、環境変数設定のユーティリティを実装しテスト容易性に配慮。

Unreleased
- （なし）

[0.1.0] - 2026-03-26
Added
- パッケージ初期リリース（kabusys v0.1.0）。
- パブリック API の入口を定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local ファイルをプロジェクトルート（.git または pyproject.toml を探索）から自動ロードする仕組みを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パース機能は export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ対応、インラインコメントの取り扱いなどに対応。
  - OS 環境変数は protected として上書き防止（.env.local による上書きは許可しつつも OS 変数は保護）。
  - Settings クラスを提供（settings インスタンスをエクスポート）。必須環境変数取得用の _require、ログレベルや KABUSYS_ENV の検証ロジックを装備。
  - 既定の DB パス（DUCKDB_PATH / SQLITE_PATH）や kabu/Slack/J-Quants 関連設定をプロパティとして提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols を集約して銘柄単位に記事をまとめ、OpenAI にバッチで送ってセンチメント（ai_score）を算出。
  - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を実装（calc_news_window）。
  - 入力文字数・記事数のトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）や、1回あたりのバッチ処理サイズ（_BATCH_SIZE）を導入。
  - OpenAI 呼び出しは JSON Mode（response_format）を使用。429/ネットワーク断/タイムアウト/5xx に対するリトライ（指数バックオフ）を実装。
  - レスポンスの厳格なバリデーション処理を実装（_validate_and_extract）。不正レスポンスはログを残してスキップし、例外を上げないフェイルセーフに設計。
  - ai_scores テーブルへの冪等的書き込み（該当コードのみ DELETE → INSERT）を採用し、部分失敗時に既存データを保護。
  - score_news(conn, target_date, api_key=None) をパブリックに提供（OpenAI API キー必須：引数または環境変数 OPENAI_API_KEY）。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み70%）と、マクロニュース LLM センチメント（重み30%）を合成し日次で市場レジーム（bull / neutral / bear）を算出。
  - DuckDB（prices_daily / raw_news / market_regime）を参照。ma200 の算出は target_date 未満のデータのみを使用しルックアヘッドを防止。
  - マクロニュース抽出（マクロキーワードベース）→ OpenAI で JSON を返すようにプロンプト指定 → スコア合成のフローを実装。
  - OpenAI 呼び出しはリトライ・バックオフを実装。API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフを採用。
  - market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT。失敗時は ROLLBACK を試行し上位へ例外伝播）。
  - score_regime(conn, target_date, api_key=None) を提供（OpenAI API キー必須）。

- 研究モジュール（src/kabusys/research/）
  - factor_research.py
    - モメンタム（1m/3m/6m）、200日移動平均乖離、20日 ATR、20日平均売買代金・出来高比率、PER/ROE（raw_financials ベース）などファクター算出関数を実装。
    - calc_momentum(conn, target_date), calc_volatility(conn, target_date), calc_value(conn, target_date) を提供。DuckDB SQL ウィンドウ関数を多用し効率的に計算。
    - データ不足時は None を返す設計。
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（horizons のバリデーションあり）。
    - IC（Spearman ρ）計算 calc_ic(factor_records, forward_records, factor_col, return_col) を実装（同順位は平均ランク）。
    - ランク化ユーティリティ rank(values) と統計サマリー factor_summary(records, columns) を提供。
  - research パッケージは kabusys.data.stats の zscore_normalize（再利用）と上記関数群を再エクスポート。

- データプラットフォーム（src/kabusys/data/）
  - calendar_management.py
    - market_calendar テーブルに基づく営業日判定/探索ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（平日を営業日とする）を採用。
    - calendar_update_job(conn, lookahead_days=90) により J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックを実装）。
  - pipeline.py / etl.py
    - ETLResult データクラスを定義（target_date, fetched/saved counts, quality_issues, errors 等）。
    - 差分更新、backfill、品質チェック（quality モジュール）を想定した ETL パイプライン骨格を実装。
    - _get_max_date / _table_exists 等のユーティリティを提供。
    - etl.py は ETLResult を再エクスポート。

Changed
- 初回リリースのため「変更」はなし。

Fixed
- 初回リリースのため「修正」はなし。

Deprecated
- 初回リリースのため「非推奨」項目はなし。

Removed
- 初回リリースのため「削除」項目はなし。

Security
- OpenAI API キーや外部 API トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）は Settings 経由で必須チェックを行う。未設定時は ValueError を投げ処理を止める旨を明示。
- .env 自動ロードはデフォルトで有効。テスト等で無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。

Notes / Limitations
- OpenAI（gpt-4o-mini）依存：API キーが必須。API 呼び出し回りはテスト時に差し替え可能（各モジュールの _call_openai_api をパッチ可能）。
- DuckDB のバージョン差異に対する互換性考慮（executemany の空リスト制約等）をコード側で扱っているが、実行環境の DuckDB バージョンに依存する可能性あり。
- ai モジュールは JSON Mode を期待するが、LLM の挙動によっては前後に余計なテキストが混入する場合があるため、パーサーは最外の {} を抽出するなどの復元ロジックを備える。
- 実際の発注・実運用（kabu ステーション API 等）との統合箇所はパッケージ構成上存在する（execution 等）が、本リリースでは主にデータ取得・分析・スコアリング機能に注力。

開発者向けヒント
- unit テストから OpenAI 呼び出しを抑制するには、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてください。
- .env の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

今後の予定（想定）
- PBR・配当利回り等のバリューファクター追加
- モデル・戦略層（strategy パッケージ）と実際の発注（execution）との接続強化・テスト充実
- パフォーマンス改善（大型銘柄集合に対するバッチ処理最適化）
- DuckDB スキーマ初期化ユーティリティやマイグレーションサポートの追加

--- 
（この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する前に内容を確認・補正してください。）