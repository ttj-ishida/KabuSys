# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。

なお、本リポジトリの初期バージョンとして以下を記録します。

-----------------------------------------------------------------------
[0.1.0] - 2026-03-31
-----------------------------------------------------------------------

Added
- パッケージ初期リリースを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは .git または pyproject.toml を基準に自動検出（CWD 非依存）
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - .env のパースは export 文・クォート・エスケープ・インラインコメント等に対応
    - 保護された OS 環境変数は上書きされない仕組みを実装
  - Settings クラスを提供（settings インスタンスを公開）
    - 必須取得メソッド（_require）：JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス設定: DUCKDB_PATH, SQLITE_PATH（デフォルトパスあり）
    - 環境判定: KABUSYS_ENV（development, paper_trading, live のいずれか）
    - ログレベル検証: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev プロパティ

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を利用して銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントを算出
    - タイムウィンドウ計算: 前日 15:00 JST ～ 当日 08:30 JST（UTC で変換）を calc_news_window で提供
    - バッチ処理: 1 API 呼び出しあたり最大 20 銘柄（_BATCH_SIZE）
    - 1 銘柄あたりの最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）
    - リトライ/バックオフ: 429/接続断/タイムアウト/5xx に対して指数バックオフでリトライ
    - レスポンスのバリデーション実装（JSON 抽出、results リスト・code/score 検証）
    - スコアは ±1.0 にクリップして ai_scores テーブルへ書き込み
    - 部分失敗時の既存データ保護のため、書き込みは対象 code のみ DELETE → INSERT（冪等処理）
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計
    - 公開 API: score_news(conn, target_date, api_key=None) — 書込件数を返す

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組合せて日次の市場レジーム（bull / neutral / bear）を判定
    - マクロキーワードで raw_news をフィルタし、最大 20 件のタイトルを LLM に投入
    - OpenAI は gpt-4o-mini を使用、JSON レスポンスを期待
    - フェイルセーフ: API 失敗時は macro_sentiment=0.0 で継続
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等的手順（失敗時は ROLLBACK）
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す
    - テスト容易性のため _call_openai_api をモジュール内で独立実装（news_nlp と共有しない）

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離）
    - Volatility / Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio（20 日ベース）
    - Value: PER（price / EPS）、ROE（raw_financials から取得）
    - DuckDB SQL を用いた実装。結果は (date, code) をキーとする dict のリストで返却
    - 不足データ時の None ハンドリング（例: MA200 行数不足）
    - 公開 API: calc_momentum, calc_volatility, calc_value

  - 特徴量探索 / 統計 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）
    - IC 計算（Spearman の ρ）: calc_ic（ランク変換、ties の平均ランク処理）
    - ランク変換ユーティリティ: rank (同順位は平均ランク)
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - 外部依存を持たず標準ライブラリ + DuckDB で実装

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジックを提供
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがある場合は DB 値優先、未登録日は曜日（平日=営業日）ベースでフォールバック
    - next/prev_trading_day は最大探索日数制限を設け ValueError で安全に失敗
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90)
      - J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS 日分再取得）して保存
      - 健全性チェック（未来日が過度に遠い場合はスキップ）
  - ETL パイプライン (src/kabusys/data/pipeline.py / src/kabusys/data/etl.py)
    - 差分更新・保存・品質チェックを行う ETLResult データクラスを提供（ETLResult を etl モジュールで再エクスポート）
    - デフォルトのバックフィル日数や最小データ日などの定義を含む
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティなどを実装
    - 品質チェックは呼び出し元が判断可能なようにエラー一覧・品質問題一覧を収集して返す設計

- 公開 API の整理
  - pkg レベルで主要モジュールを __all__ に設定: ["data", "strategy", "execution", "monitoring"]
  - research パッケージで一部ユーティリティをトップレベルで再エクスポート（zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
  - data.etl は ETLResult を再エクスポート

Design / Behavior Notes（設計上の重要点）
- ルックアヘッドバイアス防止
  - news_nlp.score_news / regime_detector.score_regime / research 関数等は datetime.today() / date.today() を直接参照しない設計。target_date を明示的に渡すことでルックアヘッドを防止。
  - prices_daily や raw_financials 等のクエリは target_date 未満／以下などの条件を適切に付与。
- フェイルセーフ
  - OpenAI API の失敗は即時例外にせず、0.0 を返す・対象銘柄をスキップする等の安全側フォールバックを多くの箇所で採用（ログ出力あり）。
- 冪等性と部分失敗の保護
  - DB への書き込みは冪等化（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK）を意識して実装。ai_scores の場合は書き込む code のみ対象に削除→挿入することで、部分失敗時に既存スコアを保護。
- テスト容易性
  - OpenAI 呼び出し部分はモジュール内で独立した _call_openai_api を実装しており、unittest.mock.patch によって差し替え可能。
- DuckDB 互換性に配慮
  - executemany に空リストを渡さない等、DuckDB のバージョン差異に備えた実装上の配慮あり。

Environment / External Requirements（実行に必要な主要環境変数）
- JQUANTS_REFRESH_TOKEN （Settings.jquants_refresh_token）
- KABU_API_PASSWORD, KABU_API_BASE_URL（Kabu ステーション API）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
- OPENAI_API_KEY（news_nlp / regime_detector のデフォルト API キー参照先）
- DUCKDB_PATH / SQLITE_PATH（データベースファイルのパス指定）

Security
- 特になし（初期リリース）

Breaking Changes
- 初期リリースのため該当なし

Migration notes
- なし（初回リリース）

-----------------------------------------------------------------------

今後は、テストカバレッジの強化、ドキュメント（使い方・API サンプル）、および運用時の監視/ロギング改善（バッチの監査ログ等）を予定しています。必要であれば、リリースノートを英語版でも作成します。