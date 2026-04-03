# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、安定したリリースごとに要約を記載します。

現在のリリース方針:
- セマンティックバージョニングを採用します。
- この CHANGELOG はパッケージ初期リリースおよび実装済み主要機能の要約を含みます。

なお、本リポジトリのバージョンは src/kabusys/__init__.py にて `__version__ = "0.1.0"` として管理されています。

Unreleased
----------

- （次回リリースに向けた未確定の変更点をここに記載します）

0.1.0 - 2026-04-03
------------------

初回公開リリース。以下の主要機能・設計方針を実装しています。

Added
- パッケージ初期構成
  - kabusys パッケージの公開サブモジュール: data, research, ai, execution, monitoring, strategy（__all__ 宣言）。
- 設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（環境変数優先）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パースの堅牢化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - インラインコメントの取り扱い（クォートなしの場合は直前が空白/タブならコメント扱い）。
  - 環境変数取得ユーティリティ（Settings クラス）を提供:
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / システム環境（KABUSYS_ENV）等のプロパティ。
    - 値のバリデーション（env, log_level の有効値チェック）および is_live/is_paper/is_dev 簡易判定。
  - 必須環境変数チェック用ヘルパー `_require`（未設定時は ValueError）。

- AI モジュール (kabusys.ai)
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供する calc_news_window。
    - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの最大記事数と文字数でトリム。
    - JSON Mode での応答期待、厳密なレスポンス検証（results 配列、code/score チェック、数値化と ±1.0 クリップ）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライ実装。失敗時はスキップして継続（フェイルセーフ）。
    - 成果は ai_scores テーブルへ冪等的に保存（対象 code のみ DELETE → INSERT）。DuckDB の executemany 空リスト制約に配慮。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - マクロニュースはタイトルをマクロキーワードでフィルタして取得し、OpenAI により -1.0～1.0 で評価（JSON 出力期待）。
    - API 呼び出しの堅牢化（リトライ・バックオフ・5xx 判定等）、API 失敗時は macro_sentiment=0.0 として継続。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK して例外を伝播。

- 研究用機能 (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン）、200 日移動平均乖離（ma200_dev）を計算する calc_momentum。
    - ボラティリティ / 流動性（20日 ATR, ATR 比, 平均売買代金, 出来高比率）を計算する calc_volatility。
    - バリューファクター（PER, ROE）を raw_financials と prices_daily から取得する calc_value。
    - DuckDB を用いた SQL ベースの実装。欠損やデータ不足時は None を返す設計。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、引数検証、パフォーマンス配慮のスキャン範囲）。
    - IC（Spearman ランク相関）計算 calc_ic（None/finite/最小サンプル数チェック）。
    - rank ユーティリティ（同順位は平均ランク、丸めによる ties 対応）。
    - 統計サマリー factor_summary（count, mean, std, min, max, median）。

- データ基盤ユーティリティ (kabusys.data)
  - calendar_management
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベース（平日）でフォールバック。最大探索日数制限で無限ループ回避。
    - 夜間バッチ calendar_update_job：J-Quants API から差分取得し market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl
    - ETLResult データクラスを定義（ETL の取得数・保存数・品質問題・エラーを集約）。
    - 差分更新・backfill・品質チェックのための基本設計を実装。jquants_client と quality モジュールを利用する想定。
  - jquants_client と quality は別モジュールとして利用（本コード内で呼び出し）。

- テスト容易性 / 設計上の注意点
  - ルックアヘッドバイアス回避: 日時の決定は引数で渡す設計（datetime.today()/date.today() を直接参照しない箇所多数）。
  - 外部 API 呼び出しは可能な限り局所化し、テスト時に差し替えやすく実装（内部 _call_openai_api をパッチ可能）。
  - DB 書き込みは冪等に設計（DELETE→INSERT、ON CONFLICT 方針）。
  - 重大な API エラーや外部要因があっても、可能な限りフェイルセーフにして部分処理を保持。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Notes / Requirements / Caveats
- OpenAI API の利用:
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須です。未設定時は ValueError を送出します。
  - 使用モデル: gpt-4o-mini（response_format に JSON mode を利用）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（kabusys.config の Settings が参照）。
- データベース:
  - DuckDB を用いた実装。呼び出し側で DuckDB コネクション（DuckDBPyConnection）を準備して渡す必要があります。
- 自動 .env ロード:
  - プロジェクトルートを .git または pyproject.toml で判断します。配布後や特殊環境で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 互換性 / 安全制約:
  - DuckDB の executemany に対する空リスト処理や list バインドの挙動に注意して実装済み（空リストの場合は実行をスキップ）。

公開 API（代表）
- kabusys.settings (Settings インスタンス)
- kabusys.ai.score_news(conn, target_date, api_key=None) -> 書き込み件数
- kabusys.ai.score_regime(conn, target_date, api_key=None) -> 1（成功）
- kabusys.research.calc_momentum / calc_volatility / calc_value
- kabusys.research.calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job
- kabusys.data.ETLResult（kabusys.data.etl により再エクスポート）

今後の予定（例）
- 実運用に向けた監視・アラート機能（monitoring）および約定処理（execution）との統合強化。
- AI プロンプトの改良、モデル切替の柔軟化、テストカバレッジの拡充。
- ETL の部分失敗時のロールフォワード戦略や品質チェック自動修復の追加。

--- 

（この CHANGELOG はソースコードの実装内容から推測して作成しています。実際の変更履歴やリリース日等はプロジェクトの方針に従って調整してください。）