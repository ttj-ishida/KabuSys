# CHANGELOG

すべての重要な変更点は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: [バージョン] - リリース日（YYYY-MM-DD）

## [Unreleased]

（現在のリポジトリ状態は v0.1.0 として初回リリース済みの想定です。以降の変更はここに追記してください。）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム "KabuSys" のコアライブラリを公開しました。主な追加点・設計上の特徴は以下の通りです。

### Added
- パッケージとバージョン情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ実装（クォートやエスケープ、コメント処理、export 構文対応）。
  - 必須変数チェック（_require）と Settings クラスを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等の既定値あり。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング: score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメントを取得。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数トリム、レスポンスバリデーション、スコア ±1 にクリップ。
    - リトライポリシー（429/ネットワーク/タイムアウト/5xx）を実装、フェイルセーフでスキップ継続。
    - DuckDB への置換的書き込み（DELETE → INSERT）を行い、部分失敗時に既存スコアを保護。
    - テスト性を考慮して _call_openai_api を patch 可能に実装。
    - タイムウィンドウ計算ユーティリティ calc_news_window(target_date) を提供（JST 基準のウィンドウ）。

  - 市場レジーム判定: score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成。
    - LLM 呼び出しは gpt-4o-mini、最大リトライ回数・指数バックオフ。
    - レジームスコアを clip してラベル付与（bull / neutral / bear）。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - _call_openai_api は news_nlp と意図的に独立した実装（モジュール結合を避ける）。

- Research（因子・特徴量解析）（src/kabusys/research）
  - factor_research.py:
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離などを計算。
    - calc_volatility(conn, target_date): 20 日 ATR、ATR 比率、平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials から PER（EPS を利用）と ROE を計算。
    - DuckDB 内の SQL を用いた実装で、外部 API にはアクセスしない安全設計。
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（指定ホライズン）の一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を計算。
    - rank(values): 同順位は平均ランクとするランク化ユーティリティ。
    - factor_summary(records, columns): 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
  - zscore_normalize は kabusys.data.stats から再エクスポート（research/__init__ にて）。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して冪等保存。バックフィルや健全性チェックを実装。
  - pipeline.py:
    - ETLResult データクラス（src/kabusys/data/pipeline.py）を提供。ETL の取得件数、保存件数、品質問題、エラー等を集約。
    - _get_max_date / _table_exists 等の内部ユーティリティを実装。
    - ETL 実装方針: 差分更新、backfill、品質チェック（quality モジュール利用）を想定。
  - etl.py:
    - ETLResult を公開インターフェースとして再エクスポート。

- jquants_client 経由でのカレンダー取得・保存を想定する設計（kabusys.data.jquants_client を参照）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Design / Safety / Testing Notes
- ルックアヘッド防止: 各種処理（score_news, score_regime, factor/forward 計算等）は datetime.today()/date.today() を内部で参照せず、必ず外部から target_date を受け取る設計。
- DB 書き込みの冪等性: market_regime / ai_scores などは書き込み前に既存行を削除してから INSERT することで冪等性を確保。
- フェイルセーフ: LLM 呼び出しや外部 API が失敗しても例外を上位に投げず（ただし致命的な設定ミスや DB 書込失敗は例外送出）処理継続する箇所を明示的に実装。
- リトライポリシー: OpenAI 呼び出しに対して429/ネットワーク/タイムアウト/5xx の場合に指数的バックオフでリトライを実装（最大試行回数に上限）。
- テスト容易性:
  - news_nlp._call_openai_api / regime_detector._call_openai_api はテスト時に patch 可能。
  - OpenAI API キーは関数引数で注入可能（api_key）で、None の場合は環境変数 OPENAI_API_KEY を参照。
- DuckDB 互換性考慮: executemany に空リストを渡さない等、DuckDB 実装の注意点に配慮。
- ロギング: 各主要処理で情報ログ／警告ログを出力。例: データ不足、API パース失敗、ROLLBACK 失敗など。

---

今後のリリースで予定している改善点（例）
- monitor / execution / strategy 等の具体的な注文実行・監視ロジックの実装・公開
- ai モデル評価・キャッシュ強化、レスポンスパースの堅牢化
- ETL の具体的ワークフロー（ジョブスケジューリング、監査ログ等）の追加
- 単体テスト・統合テストの拡充と CI 設定

もし CHANGELOG に追加してほしい詳細（例えば各関数の戻り値の例やログメッセージ抜粋など）があれば教えてください。