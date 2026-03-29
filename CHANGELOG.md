Keep a Changelog に準拠した変更履歴

すべての注目すべき変更をこのファイルに記録します。  
フォーマットやセクションは https://keepachangelog.com/ja/ に従っています。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-29
-----------------
Added
- 初回公開: Kabusys パッケージ v0.1.0
  - パッケージ構成（公開サブパッケージ・モジュール）
    - kabusys.config: 環境変数 / .env 管理（自動読み込み機能含む）
      - .env / .env.local の自動読み込み（優先度: OS 環境変数 > .env.local > .env）
      - 自動読み込みの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1
      - .env パーサ実装: export プレフィックス対応、クォート内のエスケープ処理、インラインコメントルール等を考慮
      - Settings クラスを公開（settings インスタンス）
        - 必須設定を検査する _require を使ったプロパティ:
          - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
        - DB パスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
        - 環境 / ログレベル検証: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）
        - ユーティリティプロパティ: is_live/is_paper/is_dev
    - kabusys.ai
      - news_nlp:
        - score_news(conn, target_date, api_key=None)
          - 前日 15:00 JST ～ 当日 08:30 JST のニュースを対象に銘柄ごとにテキストを集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して ai_scores テーブルへ書き込む。
          - バッチサイズ、記事上限、文字数トリムなどのトークン肥大対策を実装。
          - リトライ戦略: 429・接続断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数制御）。
          - レスポンス検証: JSON 抽出・results 配列・code/score の型チェック・未知コード無視・スコア ±1.0 クリップ。
          - DB 書き込みは部分置換 (DELETE → INSERT) を行い、部分失敗時に他銘柄スコアを保護。
          - テスト用フック: _call_openai_api はモック差し替え可能。
          - 返却値: 書き込んだ銘柄数。
      - regime_detector:
        - score_regime(conn, target_date, api_key=None)
          - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込みする。
          - マクロニュースは news_nlp.calc_news_window で定義されたウィンドウから抽出。LLM による JSON 出力から macro_sentiment を取得。
          - OpenAI 呼び出しのリトライ / フェイルセーフ: 失敗時は macro_sentiment=0.0 にフォールバックし処理継続。
          - DB トランザクションは BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK（失敗ログあり）。
          - 返却値: 成功時 1。
    - kabusys.data
      - calendar_management:
        - 市場カレンダーの取り扱い (market_calendar) と夜間更新ジョブ calendar_update_job(conn, lookahead_days=...)
        - 営業日判定 API:
          - is_trading_day(conn, d)
          - next_trading_day(conn, d)
          - prev_trading_day(conn, d)
          - get_trading_days(conn, start, end)
          - is_sq_day(conn, d)
        - 設計: DB 登録値優先、未登録日は曜日ベースでフォールバック。探索は _MAX_SEARCH_DAYS に制限。日付は date オブジェクトで統一。
        - calendar_update_job は J-Quants クライアントから差分取得し冪等保存、バックフィル・健全性チェックを実装。
      - pipeline (ETL)
        - ETLResult データクラスを公開（kabusys.data.ETLResult として再エクスポート）
          - target_date, prices_fetched/saved, financials_fetched/saved, calendar_fetched/saved, quality_issues, errors 等を保持
          - has_errors / has_quality_errors / to_dict を提供
        - ETL の差分取得、バックフィル、品質チェックの設計方針を実装
        - DuckDB の互換性注意（executemany に空リストを渡さない等）
      - jquants_client インターフェース（参照するが実装ファイルは別）：fetch/save の想定フローに合わせた設計
    - kabusys.research
      - factor_research:
        - calc_momentum(conn, target_date)
          - mom_1m/mom_3m/mom_6m, ma200_dev を DuckDB SQL で計算。データ不足時は None を返す。
        - calc_volatility(conn, target_date)
          - 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。NULL 伝搬制御に注意。
        - calc_value(conn, target_date)
          - raw_financials から直近財務を結合して PER/ROE を算出。EPS=0/欠損時は None。
      - feature_exploration:
        - calc_forward_returns(conn, target_date, horizons=None)
          - デフォルト horizons=[1,5,21]。LEAD を使った一括取得。
        - calc_ic(factor_records, forward_records, factor_col, return_col)
          - スピアマン（ランク）相関を純粋 Python 実装で算出。有効レコード < 3 の場合は None。
        - rank(values) / factor_summary(records, columns)
          - ランク（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を提供。
      - 研究用ユーティリティ: kabusys.data.stats.zscore_normalize を再利用するインターフェースをエクスポート
  - パッケージレベルの __all__ による主要モジュールの公開（data, strategy, execution, monitoring 等の名前空間を準備）

Notable design decisions / 実装上の注意点
- ルックアヘッドバイアス対策:
  - 各 AI / 研究処理は内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date に基づいて処理する設計。
  - prices_daily などのクエリは target_date 未満 / 以前などの排他条件を守る。
- OpenAI 統合:
  - gpt-4o-mini を使用、JSON Mode（response_format={"type": "json_object"}）を使用して厳密な JSON 出力を期待。
  - リトライ対象としないエラーは速やかにスキップし、フェイルセーフ（デフォルトスコア 0.0 など）で継続する設計。
  - テスト容易性のため _call_openai_api をモック差し替え可能にしている。
- DB トランザクション・冪等性:
  - market_regime / ai_scores 等への書き込みは冪等化（DELETE→INSERT / ON CONFLICT を想定）している。
  - DuckDB 実行時の互換性問題（executemany に空リスト不可）を回避するガードを実装。
- タイムゾーン:
  - ニュースウィンドウは JST を起点に計算し、DuckDB 内の raw_news.datetime は UTC（naive）で扱う想定。
- 依存を最小化:
  - 研究モジュールは pandas 等の外部ライブラリに依存せず、標準ライブラリ + DuckDB SQL で実装。
- ロギング:
  - 各モジュールは詳細な logger.debug/info/warning/exception を出力し、運用時のトラブルシューティングを容易にする。

Configuration / 移行ノート
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須とされる（未設定時は ValueError）。
  - OpenAI を使う機能（score_news / score_regime）は OPENAI_API_KEY を引数または環境変数で与える必要がある。
- 自動 .env ロード:
  - パッケージはインポート時にプロジェクトルート（.git または pyproject.toml 見つける）を探索し .env/.env.local を自動読み込みする。テスト環境等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Fixed
- 初回リリースのため該当なし

Changed
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Public API（主要な関数/クラスの一覧）
- settings: kabusys.config.settings (Settings インスタンス)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.ai.news_nlp.calc_news_window(target_date)
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
- kabusys.data.pipeline.ETLResult
- kabusys.research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- その他内部ユーティリティやテストフック（_call_openai_api 等）

今後の予定（短期）
- strategy / execution / monitoring サブパッケージの実装拡充（発注ロジック・モニタリング）
- テストカバレッジの拡充と CI 統合
- jquants_client の具体的実装・認証ハンドリングの整備

問い合わせ / 貢献
- バグ報告・提案は Issue を作成してください。PR は歓迎します。