# Changelog

すべての注目すべき変更をこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を採用します。

<!-- 今後のリリース履歴は上から古いものへ向かって追記してください -->

## [Unreleased]

### Added
- （今後の変更をここに記載）

---

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買／研究プラットフォームのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - kabusys パッケージの基本公開 API を追加（data, strategy, execution, monitoring）。バージョンは 0.1.0 に設定。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルート探索は __file__ ベースで .git または pyproject.toml を探索し、CWD に依存しない実装。
  - .env パーサー実装:
    - export キーワード対応、クォーテーション内のバックスラッシュエスケープ、インラインコメントルール（クォートあり/なしでの挙動差異）をサポート。
    - 無効な行をスキップ。
  - Settings クラスを提供（settings インスタンスで利用可能）。
    - J-Quants / kabuステーション / LINE / DB パス 等のプロパティを用意。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。PAPER_FILL_MODE の有効値チェックを実施。
    - 監視関連（PID ファイル, kill flag, CPU/Memory/Disk 閾値）を提供。
    - KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL のバリデーション。
    - is_live / is_paper / is_dev ユーティリティ。

- AI ニュース解析（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集約して銘柄毎に LLM（gpt-4o-mini）でセンチメント評価を行い、ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して処理）。
    - 1 銘柄あたりのトークン膨張対策（記事数上限・文字数トリム）。
    - バッチ処理（最大 20 銘柄/コール）と JSON Mode を用いた厳密なレスポンス期待。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフ。
    - レスポンス検証: JSON パース、"results" の存在、code の検証、スコア数値化、±1.0 でクリップ。
    - DuckDB への冪等書き込み（部分失敗に備え、対象 code のみ DELETE → INSERT）。
    - API キー注入可能（api_key 引数または OPENAI_API_KEY 環境変数）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、market_regime テーブルへ保存。
    - ETF データが不足する場合のフェイルセーフ（中立値 1.0 を採用）。
    - マクロニュース抽出はキーワードベース（日本＆米国系マクロ語彙）でタイトルを取得。
    - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment = 0.0 にフォールバック。
    - レトライ・バックオフと 5xx 判定を含む堅牢なエラーハンドリング。
    - 結果はクリップしてラベル（bull/neutral/bear）を決定、冪等に DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データ ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
  - ETLResult データクラスを公開（pipeline.ETLResult を etl モジュールから再エクスポート）。
  - ETL の設計方針を反映したフィールド（取得数、保存数、品質チェック、エラー集約等）を持つ。
  - 返却や監査用に to_dict() を提供（quality_issues を dict 化）。

- カレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを扱うユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得の場合の曜日ベースフォールバック（週末は非営業日）。
    - 最大探索範囲を設定して無限ループを防止。
  - 夜間更新ジョブ calendar_update_job(conn, lookahead_days) を実装。
    - J-Quants から差分取得し、バックフィル（直近数日間の再取得）と健全性チェックを実施。
    - 取得→保存（jquants_client の save_market_calendar）を行い、結果件数を返却。

- Research / ファクター群（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）。
    - calc_volatility: 20日 ATR / 相対 ATR / 20日平均売買代金 / 出来高比。
    - calc_value: latest raw_financials と株価を組み合わせた PER / ROE。
    - DuckDB を用いた SQL ベース実装、外部 API に依存しない。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）における将来リターン取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）計算。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー機能。
  - zscore_normalize を data.stats から再エクスポート（kabusys.research.__init__ で公開）。

- データモジュールの再エクスポート
  - ETLResult を kabusys.data.etl で公開して外部から参照可能に。

### Changed
- （初回リリースのため過去の変更はありません）

### Fixed
- （初回リリースのため修正はありません）

### Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から注入する設計。自動でログにキーを出力しないよう配慮。

### Notes / 設計上の重要点
- ルックアヘッドバイアスの防止:
  - AI スコア計算・レジーム判定・ETL の各処理は datetime.today()/date.today() を直接参照しない。必ず target_date を引数として与える設計。
  - DB クエリでは target_date 未満／未満等の排他条件を明示し、未来データを使用しない。
- DuckDB を一貫して利用:
  - 集計・ウィンドウ関数・executemany の制約（空リスト不可）等、DuckDB の挙動を考慮した実装。
- OpenAI 呼び出し:
  - gpt-4o-mini を想定、JSON Mode（response_format={"type":"json_object"}）で厳密な JSON を期待。
  - レスポンスパース失敗や API エラーはフェイルセーフ（スコアはスキップまたは 0 にフォールバック）として扱い、処理全体の継続性を重視。
- DB 書き込みは冪等性を重視:
  - market_regime / ai_scores 等は対象日・銘柄を絞った DELETE→INSERT で置換することで部分失敗時の既存データ保護を実現。

---

過不足や補足を反映して CHANGELOG を更新したい場合は、追記や日付修正を指示してください。