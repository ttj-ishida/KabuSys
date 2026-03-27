# Changelog

すべての変更は Keep a Changelog の仕様に従って記載します。  
このファイルはコードベースから推測して自動生成しています。

全般的な注意
- 本リリースはパッケージの初期版に相当します（バージョン: 0.1.0）。
- 多くの処理は DuckDB 接続と特定テーブル（例: prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）を前提としています。
- OpenAI（gpt-4o-mini）や J-Quants、kabuステーション などの外部 API を利用する機能が含まれます。必要な環境変数は下記参照。

[0.1.0] - 2026-03-27
Added
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開されたサブパッケージ: data, research, ai, config, monitoring, strategy, execution（__all__ に記載。実装は順次提供）
- 環境設定管理 (kabusys.config)
  - Settings クラスを提供し、環境変数から設定値を取得するプロパティを実装。
  - 必須環境変数の取得時に未設定だと ValueError を投げる _require を実装。
  - サポートされる主要設定:
    - JQUANTS_REFRESH_TOKEN（J-Quants）
    - KABU_API_PASSWORD, KABU_API_BASE_URL（kabuステーション API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Slack 通知）
    - DUCKDB_PATH, SQLITE_PATH（ローカル DB パス）
    - KABUSYS_ENV（development / paper_trading / live）, LOG_LEVEL
  - .env 自動読み込み機構を実装
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env と .env.local を自動ロード（OS 環境変数優先）。
    - .env.local は .env の上書き（override）として読み込む。OS 側の既存環境変数は保護。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env の行パースは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI によるセンチメント分析で ai_scores テーブルへ書き込み。
    - 特徴:
      - JST ベースのニュースウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を提供。
      - 1銘柄あたり最大記事数・文字数でトリムする制御（トークン肥大化対策）。
      - 最大 20 銘柄ずつのバッチ送信（_BATCH_SIZE=20）。
      - OpenAI 呼び出しは JSON Mode を利用し、レスポンスを厳密にバリデートしてスコアを ±1.0 にクリップ。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。非リトライエラーはスキップして継続（フェイルセーフ）。
      - 部分成功時に既存スコアを消さないよう、書込前に該当コードのみ DELETE → INSERT を行う（冪等性と部分失敗耐性）。
      - テスト容易性のため _call_openai_api を patch で差し替え可能。
  - レジーム検出 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを重み付け合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存。
    - 特徴:
      - ma200Ratio の計算（最新終値 / 200日単純移動平均）。データ不足時は中立（1.0）としてフォールバックし警告ログ。
      - マクロニュース抽出はマクロキーワードリストでフィルタして最大 20 記事を取得。
      - OpenAI 呼び出しは retry/backoff を行い、API 失敗・パース失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
      - 結果は冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、書込失敗時は ROLLBACK を試行して例外を伝播。
- データ処理 (kabusys.data)
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX カレンダー（market_calendar）を前提とした営業日判定ユーティリティを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB にカレンダー情報がない場合は曜日ベース（平日が営業日）でフォールバックし一貫した挙動を維持。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分でカレンダーを取得し market_calendar を更新するジョブを実装。バックフィル日数や健全性チェックを備える。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult dataclass を実装し、ETL 実行結果（取得/保存件数、品質問題、エラー等）を構造化して返す。
    - 差分更新・バックフィル・品質チェックの方針をコードコメントで明記（jquants_client と quality モジュールを利用する想定）。
    - _get_max_date / _table_exists 等のユーティリティを提供。
    - kabusys.data.etl で ETLResult を再エクスポート。
- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev を計算（営業日ベースのラグ）。データ不足時は None を返す。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio などボラティリティ／流動性指標を計算。必要行数未満は None を返す。
    - calc_value(conn, target_date): raw_financials と prices_daily を結合して PER / ROE を算出（EPS が 0 または欠損の場合は None）。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 指定ホライズン先のリターンをまとめて取得。ホライズンは 1〜252 の正整数のみ許容。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装。利用可能レコードが 3 件未満のときは None を返す。
    - rank(values): 同順位は平均ランクとするランク変換実装（round による丸めで ties の問題に対処）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。
- ロギング
  - 各モジュールで適切な情報ログ／警告ログを出力するように設計（ETL/AI/APIリトライ/データ不足等の理由を明示）。

Changed
- 初公開のため該当なし（新規実装中心）。

Fixed
- 初公開のため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数（API キー等）は Settings 経由で参照・必須化。自動的に .env を読み込むが OS 環境変数を保護する仕組みを導入。

Migration / 注意事項（ユーザ向け）
- 必須環境変数の設定:
  - OPENAI_API_KEY: AI 機能（score_news, score_regime）に必要。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等も使用箇所あり。
- DB スキーマ: 各機能は特定のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）構造を前提としています。これらのテーブルが存在しない場合、関数は None/空結果やエラーを返す可能性があります。
- DuckDB と OpenAI Python SDK が依存関係として必要です。
- テストの容易性:
  - OpenAI 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api / news_nlp._score_chunk など）を unittest.mock.patch で差し替え可能に実装してあり、外部 API 呼び出しをモックできます。
- フェイルセーフの設計:
  - LLM の失敗や一時的なネットワーク障害が発生しても、スコアリング処理は例外で停止させずフォールバック値（0.0 等）で継続する設計です。ただし DB 書込失敗時は例外が伝播します。
- .env パースの互換性:
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応していますが、特殊な .env フォーマットでは差異が発生する可能性があります。

今後の検討（コードからの示唆）
- ai スコアのモデル切替や温度調整を設定から変更可能にする拡張。
- ETL の実働パイプライン実装（差分計算 → jquants_client の呼び出し → quality チェックの実装詳細）。
- strategy / execution / monitoring の公開インターフェース実装（現時点では __all__ に名前のみ存在）。

参考
- 本ファイルはリポジトリ内の docstring とコード（関数名・定数・コメント）を元に自動的に推測して作成しています。実際の変更履歴やリリースノートはリポジトリの git コミットログやパッケージのリリースタグを参照してください。