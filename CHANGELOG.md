CHANGELOG
=========

すべての重要な変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。  

[未リリース]
------------

- 現在なし。

[0.1.0] - 2026-03-28
-------------------

初回リリース — KabuSys: 日本株自動売買システムの基本コンポーネントを実装しました。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ によるバージョン管理（0.1.0）と公開モジュール指定。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local からの自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装（export 形式／クォート・エスケープ・インラインコメント対応）。
  - Settings クラスを提供し、以下の設定プロパティを公開:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live; デフォルト: development）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL; デフォルト: INFO）
  - 必須変数未設定時は ValueError を発生させる _require() を提供。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX カレンダー取得＆管理の基盤実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックあり）。
    - DB 未取得時は曜日ベースのフォールバック（土日休業）を使用。
    - 最大探索日数やバックフィル、先読み日数などの安全パラメータを導入（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _CALENDAR_LOOKAHEAD_DAYS 等）。
  - pipeline / ETL:
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分取得・保存・品質チェックの設計方針を実装（backfill や品質チェックの集約・報告を想定）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・200日MA乖離計算。
    - calc_volatility: ATR20、相対ATR、20日平均売買代金、出来高比率。
    - calc_value: PER, ROE を raw_financials と prices_daily から計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた SQL + Python 実装。結果は (date, code) をキーとする dict のリストで返す。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを取得（デフォルト: [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位に平均ランクを割り当てるランク関数（丸めで ties 対策）。
    - factor_summary: カウント・平均・標準偏差・最小・最大・中央値を計算。
  - zscore_normalize は kabusys.data.stats から再利用して公開。

- AI / NLP 機能（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols を用い、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価し ai_scores テーブルへ書き込み。
    - ニュース時間ウィンドウ（JST）計算（前日 15:00 JST ～ 当日 08:30 JST を対象）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄 / API コール）、1 銘柄あたりの最大記事数・文字数トリム、JSON Mode を使用した厳密なレスポンス検証を実装。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx に対して指数バックオフ）とフェイルセーフ（API 失敗時は該当チャンクをスキップして続行）。
    - レスポンス検証: JSON パース、"results" 構造、コード検証、数値チェック、スコアの ±1.0 クリップ。
    - DuckDB executemany の互換性考慮（空リスト未対応への対処）。
    - テスト容易性: _call_openai_api をモック可能。
  - regime_detector:
    - score_regime: ETF 1321（Nikkei225連動ETF）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードリスト）と OpenAI を用いたマクロセンチメント評価（JSON 出力期待）。
    - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
    - API 呼出しのリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。

- その他
  - 内部実装の安全策／設計方針を明示（ルックアヘッドバイアス防止、冪等性、DuckDB 互換性、テスト容易性など）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーおよび各種トークンは環境変数で管理（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。必須未設定時は明示的に ValueError を送出。
- .env の自動読み込みはデフォルトで有効。テスト時に競合する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

Notes / 既知の制限
- news_nlp の出力は JSON Mode を前提とするが、LLM の出力に余計な前後テキストが混入する可能性を考慮してパーサの復元処理を実装している。
- ai_scores テーブルへの書き込みは「取得成功したコードのみ」を対象に DELETE → INSERT を行い、部分失敗時に既存データを保護する形にしている。
- calc_value では現時点で PBR・配当利回りは未実装。
- DuckDB バージョン互換性により executemany に空リストを渡せない問題に対処済み。
- jquants_client（実際の API クライアント）の実装は別モジュール（kabusys.data.jquants_client）を参照する設計。実際の環境では該当クライアントの接続情報・トークン設定が必要。
- OpenAI モデルはデフォルトで gpt-4o-mini を使用。将来的なモデル更新に伴う調整が必要になる可能性あり。

Migration / Usage notes
- 環境変数を .env.example を参考に用意してください。
- デフォルトの DuckDB/SQLite パスは data/ 以下を想定しています。必要に応じて DUCKDB_PATH / SQLITE_PATH を設定してください。
- KABUSYS_ENV を正しく設定すると is_live / is_paper / is_dev 等の挙動切替に影響します。
- OpenAI 呼び出し箇所はユニットテストのために _call_openai_api を patch して差し替えできます。

Acknowledgements
- 本リリースはデータ取得・前処理、研究用ファクター計算、LLM を使ったニュース・レジーム判定までの基本的なワークフローをカバーします。今後は発注・実行モジュール、監視・アラート周りの実装、さらに細かな品質チェック拡充や運用改善を予定しています。