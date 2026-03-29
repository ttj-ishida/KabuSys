Keep a Changelog準拠

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは初回リリースとして v0.1.0 を公開しました。

予定されるセクション: Added, Changed, Fixed, Security。初回リリースのため主に Added を記載します。

[Unreleased]

[0.1.0] - 2026-03-29
Added
- パッケージ基礎
  - 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を設定。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を指定。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数読み込み機能を実装。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env の行パースで以下に対応:
      - 空行・コメント行（#）を無視
      - export KEY=val 形式を許容
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなし値のインラインコメント（#）処理（直前が空白またはタブの場合のみ）
  - 環境変数保護・上書き挙動:
    - OS 環境変数を protected として .env.local による上書きを制御
    - _load_env_file に override/protected オプションを実装
  - Settings クラスでアプリ設定をプロパティとして提供:
    - J-Quants / kabuステーション / Slack / DB パスなど（必須項目は _require で ValueError を送出）
    - KABUSYS_ENV のバリデーション（development, paper_trading, live）
    - LOG_LEVEL のバリデーション（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - duckdb/sqlite のデフォルトパス提供と Path 化
    - is_live / is_paper / is_dev 補助プロパティ

- AI モジュール (kabusys.ai)
  - ニュースセンチメント（銘柄ごと）スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとに記事を結合し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - チャンク処理（デフォルト最大 20 銘柄/リクエスト）、1銘柄あたりの記事数や文字数に上限を設ける（過剰膨張対策）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、各要素の code/score、スコア数値・有限性チェック）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数を設定）。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして他チャンクは継続。最終的に取得できた銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）。部分失敗による既存データ破壊を回避。
    - テスト容易性: _call_openai_api を patch して差し替え可能。
    - 時間ウィンドウ: target_date に対する JST ベース（前日 15:00 ～ 当日 08:30）を UTC に換算して DB クエリに利用（ルックアヘッドを防止）。
    - score_news は成功書き込み件数を返却。
  - マクロレジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成し、日次でレジーム（bull/neutral/bear）を判定して market_regime テーブルに冪等書き込み。
    - ma200_ratio は prices_daily から target_date 未満のデータのみを用いて計算（ルックアヘッドバイアス対策）。データ不足時は中立（1.0）を返す。
    - マクロニュースは news_nlp.calc_news_window に基づくウィンドウから抽出し、OpenAI（gpt-4o-mini）で -1.0～1.0 のスコアを JSON で取得。
    - API 呼び出しでのリトライ・エラー処理・JSON パース失敗時のフォールバック（macro_sentiment=0.0）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等フロー。失敗時に ROLLBACK を試行して例外を再送出。

- データ基盤モジュール (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - カレンダーデータがない場合は曜日ベース（土日非営業）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫した結果を返す。
    - calendar_update_job を実装し J-Quants API から差分取得→保存（バックフィル・健全性チェック・例外処理）を行う。
    - 最大探索日数やバックフィル日数などの安全パラメータを定義（_MAX_SEARCH_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS 等）。
    - jquants_client（外部モジュール想定）経由でデータ取得/保存を行う設計。
  - ETL パイプライン (kabusys.data.pipeline / etl)
    - ETLResult データクラスを公開（差分取得・保存数・品質問題・エラーの集約）。
    - 差分更新のためのユーティリティ（最終取得日の取得、テーブル存在チェックなど）を実装。
    - J-Quants 差分取得、idempotent な保存（ON CONFLICT DO UPDATE 想定）、品質チェック集約を想定した設計。
    - エラーと品質問題の分離（致命的エラーは errors、品質は quality_issues として保持）。
    - kabusys.data.etl から ETLResult を再エクスポート。

- リサーチ（研究）モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - モメンタム (1M/3M/6M)、MA200 乖離、ATR20（ボラティリティ）、20日平均売買代金/出来高比などを DuckDB SQL で計算する関数群を実装:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB のウィンドウ関数を利用し、データ不足時は None を返す挙動。
    - 外部 API や発注ロジックには依存しない（純粋に分析用）。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算（calc_forward_returns）：任意ホライズン（デフォルト [1,5,21]）のリターンを LEAD を使って一括取得。
    - IC (Information Coefficient) 計算（calc_ic）：ランク変換を行い Spearman 相関（ランクの Pearson）を計算。データ不足時は None を返す。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、丸めにより ties 検出漏れを防止。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を計算（None 値は除外）。
  - kabusys.research パッケージは一部ユーティリティ（zscore_normalize）を kabusys.data.stats から再エクスポート。

Other notes / Design decisions
- ルックアヘッドバイアス防止: 全ての AI / リサーチ / ETL モジュールで date.today()/datetime.today() を直接参照しない設計。target_date の外部注入を基本とする。
- テスト容易性: OpenAI 呼び出しや時刻依存処理は置き換え可能（patch）としてあり、ユニットテストでモックしやすい設計。
- DuckDB を主要なローカル分析 DB として想定。executemany の空リスト制約など DuckDB の互換性考慮が組み込まれている。
- OpenAI モデル: gpt-4o-mini を JSON Mode（response_format={"type": "json_object"}）で利用する想定。レスポンスの冗長テキスト混入を吸収する復元ロジックを備える。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

導入 / マイグレーションメモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score系を使用する場合）
- 開発時に .env/.env.local をルートに配置すると自動読込されます。自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のデフォルトパスは settings.duckdb_path / settings.sqlite_path でそれぞれ data/kabusys.duckdb, data/monitoring.db。必要に応じて環境変数で上書きしてください。

もし差分の粒度（例えば内部関数の追加や特定モジュールのみを強調）を細かく出したい場合は、該当モジュール名を指定してください。