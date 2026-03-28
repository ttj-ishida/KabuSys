CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。
https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリースを公開。
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - パブリック API のエクスポート: data, strategy, execution, monitoring を __all__ に設定。
- 環境設定管理
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（src/kabusys/config.py）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索するため、CWD非依存でパッケージ配布後も動作。
    - 読み込み順序: OS 環境変数 > .env.local > .env（既存の OS 環境変数は protected として上書き回避）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを抑止可能（テスト用途）。
    - 高度な行パース: export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、コメント処理のルールを実装。
  - Settings クラスを提供（settings インスタンスをエクスポート）。主要プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - duckdb/sqlite ファイルパスのデフォルト（data/kabusys.duckdb, data/monitoring.db）
    - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証
    - is_live / is_paper / is_dev の便利プロパティ
- AI（自然言語処理）機能
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - score_news(conn, target_date, api_key=None): raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ問い合わせし、銘柄ごとの ai_score を ai_scores テーブルへ保存。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換した半開区間で比較）。
    - バッチ処理（最大 20 コード / チャンク）、記事トリム（最大記事数・文字数制限）、レスポンス検証、スコア ±1.0 クリップ。
    - 再試行ポリシー（429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ）とフォールバック動作（失敗時はそのチャンクをスキップして継続）。
    - テスト容易性: _call_openai_api をモックで差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出は news_nlp.calc_news_window を利用。API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ。
    - OpenAI 呼出しは専用関数で実装しモジュール間の結合を避ける。リトライ・エラーハンドリングを実装。
- データ基盤（Data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーを扱うユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルがない場合は曜日ベース（土日休）でフォールバック。DB 登録値を優先する一貫した振る舞い。
    - 夜間バッチ job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを実行。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult dataclass を導入（target_date, fetched/saved カウント、quality_issues, errors 等を保持）。to_dict によるシリアライズを提供。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - _get_max_date 等のユーティリティでテーブル存在有無や最大日付を取得。
    - etl モジュールは ETLResult を再エクスポート。
  - jquants_client との連携を前提とした設計（データ取得・保存は jquants_client の実装に委譲）。
- 研究（Research）
  - factor_research（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離を計算（不足時は None）。DuckDB SQL ベース。
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value(conn, target_date): raw_financials の最新財務情報を取得して PER/ROE を計算（EPS = 0/欠損は None）。
    - 全関数とも prices_daily/raw_financials のみ参照し、本番発注 API へアクセスしない設計。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズンの将来リターンを LEAD を使って一括取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（有効レコード < 3 の場合 None）。
    - rank(values): 同順位は平均ランクで処理（丸めで ties 判定の安定化）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
- モジュール公開整理
  - ai, research パッケージで主要関数を __all__ にて公開（例: kabusys.ai.score_news / score_regime、kabusys.research.calc_* 等）。

Changed
- 設計原則の明示
  - 主要な分析/スコアリング関数は datetime.today()/date.today() を直接参照せず、必ず target_date を受け取ることでルックアヘッドバイアスを回避。
  - DB 書き込みは冪等（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理）となるよう統一した実装に。
  - API 呼び出し失敗時は可能な限り例外を上位に伝播させずフォールバック（スコア 0.0 やチャンクスキップ）することで処理継続性を優先。

Fixed
- 明示的なログ出力と警告を追加して、データ不足・JSON パース失敗・ROLLBACK 失敗などの診断を容易に。

Security
- 環境変数の扱いに注意:
  - OPENAI_API_KEY を必須とする関数では、引数で API キーを注入可能（テスト容易性および秘匿管理）。
  - .env 自動ロードはテスト時に無効化できる（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Migration
- 実行前に必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）を設定してください。未設定時は Settings のプロパティが ValueError を投げます。
- .env のサンプルを .env.example から作成して利用してください。
- DuckDB 側では以下テーブル等が前提:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials
  - ETL / カレンダー更新などを利用する場合、jquants_client の実装（fetch/save 関数）を環境に合わせて提供してください。
- OpenAI 関連: デフォルトモデルは gpt-4o-mini。API レスポンスの JSON mode を前提としたパース実装があるため、互換性のある SDK/モデルを使用してください。
- テスト向けフック:
  - AI 呼び出しを行う内部関数（news_nlp._call_openai_api / regime_detector._call_openai_api）を unittest.mock.patch で差し替え可能です。
  - 自動 .env 読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

今後の予定（短期）
- strategy / execution / monitoring モジュールの実装・公開（現状 __all__ に名称を用意）。
- より詳細な品質チェックモジュール（kabusys.data.quality）の統合と ETL ワークフローの CLI/ジョブ化。
- AI モデルのパラメータ（モデル名・温度・バッチサイズ等）の外部設定化。

---