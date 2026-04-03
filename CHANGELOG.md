CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-03
-------------------

初期リリース — KabuSys 日本株自動売買システムのコアコンポーネントを公開しました。

Added
- パッケージ基盤
  - パッケージ情報を定義（kabusys.__version__ = 0.1.0）。公開モジュール: data, research, ai, execution, monitoring, strategy 等を想定した __all__ を提供。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダー機能を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - プロジェクトルートの判定は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env の高度なパーサ実装: export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - 環境変数取得ユーティリティ Settings を提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY 想定、各種パス設定や監視閾値、環境種別/ログレベル検証など）。
  - 必須変数未設定時は ValueError を送出する _require を用意。

- AI / ニュースNLP（kabusys.ai.news_nlp）
  - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）へ JSON Mode で問合せしてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（前日15:00 JST〜当日08:30 JST 相当）を calc_news_window で提供（UTC naive datetime を返す）。
  - バッチ処理: 1 回あたり最大 20 銘柄（_BATCH_SIZE=20）、1 銘柄あたり最大記事数/文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
  - API エラー処理: 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ（最大回数 _MAX_RETRIES）、それ以外はスキップして継続するフェイルセーフ設計。
  - レスポンス検証を強化: JSON 抽出/パース、"results" リスト・要素形式・スコアの数値性・既知コードチェックなど。無効応答は無害にスキップ。
  - DuckDB への書き込みは冪等（DELETE（対象コード）→ INSERT）で実行。部分失敗時に既存スコアを保護する設計。
  - テスト容易性: _call_openai_api などをモック差し替え可能に実装。

- AI / 市場レジーム判定（kabusys.ai.regime_detector）
  - score_regime(conn, target_date, api_key=None): ETF 1321（Nikkei 225 連動ETF）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で regime_score と regime_label（'bull'/'neutral'/'bear'）を算出し market_regime テーブルへ冪等書き込みを行う。
  - ma200_ratio 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。データ不足時は中立 (1.0) を採用。
  - マクロニュースは news_nlp.calc_news_window に基づくウィンドウで抽出し、OpenAI（gpt-4o-mini）に JSON 出力を要求してスコア化。API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
  - 合成後のクリッピングとしきい値（BULL/BEAR）でラベリング。
  - DB 書込は BEGIN/DELETE/INSERT/COMMIT を用いた冪等処理。失敗時はロールバックを試行。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - ジョブ calendar_update_job により J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS を再フェッチ）し market_calendar を更新する機能を実装。
    - 異常値検出（未来日が極端に大きい等）や最大探索日数制限で安全に動作するよう設計。

  - ETL パイプライン（pipeline.py / etl エクスポート）
    - ETLResult dataclass を定義し、ETL 実行メトリクス（取得/保存件数、品質問題、エラー等）を構造化して返却可能。
    - 差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - DuckDB 存在チェック・最大日付取得ユーティリティを実装。

- 研究（research）
  - ファクター計算（research.factor_research）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): atr_20（20日 ATR）、atr_pct、avg_turnover、volume_ratio を計算。必要な期間が満たない場合は None。
    - calc_value(conn, target_date): raw_financials から最新の財務データ（EPS/ROE）を参照し PER/ROE を算出（EPS=0/欠損時は None）。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（デフォルト [1,5,21] 営業日）を一括取得。horizons バリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算。3 レコード未満は None。
    - rank(values): 同順位は平均ランクで扱うランク関数（丸めによる ties 対策あり）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する統計サマリー。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で与える設計。キー未指定時は ValueError を送出して誤動作を防止。
- .env 自動ロード時、既存の OS 環境変数は保護（protected set）され、.env.local による上書きのみ許可。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

注意事項・既知の制約
- 全モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を前提としており、DuckDB が必須です。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode を利用するプロンプト設計になっています。API レスポンス形式の変化やモデルの仕様変更があった場合はパース処理の調整が必要です。
- ETL / データ更新処理は J-Quants API クライアント（kabusys.data.jquants_client）へ依存します。実行時には適切な API トークン（JQUANTS_REFRESH_TOKEN 等）を設定してください。
- 日時関連処理はルックアヘッドバイアス防止のため date/timestamp の現在時刻参照を行わない設計です（関数引数で target_date を与える方式）。
- テスト容易性のため、OpenAI 呼び出しを行う内部関数（_call_openai_api 等）はモック差し替え可能になっています。

アップグレード手順（初回導入メモ）
- 環境変数を .env に設定する場合、プロジェクトルートに .env/.env.local を配置してください（.git または pyproject.toml をルート判定に使用）。
- 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（用途に応じて）、OPENAI_API_KEY（AI 機能を使用する場合）。
- デフォルトのデータベースパス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 自動 .env ロードを無効にするテストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

問い合わせ・貢献
- バグ報告や機能提案は issue を作成してください。設計意図（ルックアヘッドバイアス回避、冪等性、フェイルセーフ）に沿った変更を歓迎します。