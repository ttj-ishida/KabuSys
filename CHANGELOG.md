CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-31
--------------------
Added
- 初回公開リリース。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - メイン公開モジュール: data, research, ai, （strategy, execution, monitoring を __all__ に準備）
- 環境/設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどに対応した .env パーサ実装。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等のプロパティを定義）。
  - 環境・ログレベルの妥当性チェック（KABUSYS_ENV, LOG_LEVEL）。
- AI モジュール (kabusys.ai)
  - ニュースセンチメント集計: score_news
    - raw_news と news_symbols を用いて、前日15:00 JST〜当日08:30 JST のニュースを銘柄別に集約。
    - OpenAI（gpt-4o-mini）へ銘柄をチャンク（デフォルト最大20銘柄）で送信し、JSON Mode によるレスポンスをバリデーションして ai_scores テーブルへ書き込み。
    - スコアは ±1.0 にクリップ。チャンク単位で失敗しても他銘柄の結果は保持するため部分失敗に強い実装。
    - ネットワーク/429/タイムアウト/5xx を対象に指数バックオフでリトライ。JSON パースや想定外のレスポンスはロギングしてスキップ。
    - テスト容易性を考慮し、API 呼び出し関数は差し替え可能（unittest.mock.patch でモック可能）。
  - 市場レジーム判定: score_regime (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し日次でレジーム（bull/neutral/bear）を算出して market_regime テーブルへ冪等書き込み。
    - マクロニュースはキーワードフィルタで抽出、記事がある場合のみ LLM を呼び出す。API 失敗時は macro_sentiment=0.0 として処理継続。
    - OpenAI 呼び出しは独立実装として提供（news_nlp の内部関数を共有しない設計）。
- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値を優先し、未登録日は曜日ベースのフォールバックを採用。探索は最大 _MAX_SEARCH_DAYS で安全に打ち切り。
    - JPX カレンダー夜間バッチ更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル・健全性チェック含む）。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開し、取得数・保存数・品質チェック結果・エラー集約を構造化。
    - 差分更新、バックフィル、品質チェック（quality モジュールとの連携）を想定した ETL 基盤。
    - DuckDB を前提としたテーブル存在チェック、最大日付取得ユーティリティを提供。
  - jquants_client 用のラッパー呼び出し箇所を想定したインターフェースを用意（詳細は jquants_client 実装依存）。
- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を算出。
    - 共通設計方針として DuckDB の prices_daily / raw_financials のみ参照し外部操作を行わない。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（存在しない場合は None）。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効データが3件未満の場合 None を返す）。
    - factor_summary, rank: ファクター列の統計サマリー、ランク付けユーティリティを提供。
  - zscore_normalize を kabusys.data.stats から再エクスポート。
- 実装上の設計方針・品質配慮
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を内部処理で直接参照しない（API呼び出し側が target_date を渡す設計）。
  - DB 書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK を適切に使用）。
  - API 依存処理はフォールバックを持ち、致命的でない障害時は継続（例: LLM 失敗時に 0.0 を使用）。
  - DuckDB の実装差異（executemany の空リスト制約など）へ配慮した実装。
  - ロギングを豊富に出力し、失敗箇所の診断を容易にする設計。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし。

Removed
- 該当なし。

Security
- 該当なし。

Notes / 既知の制約
- OpenAI API を利用する機能（score_news, score_regime）は OPENAI_API_KEY が未設定の場合 ValueError を送出する。CI/本番実行時は環境変数を設定してください。
- DuckDB を用いるため、ローカル環境での動作には DuckDB と対象テーブル（prices_daily, raw_news, ai_scores, market_calendar, raw_financials, news_symbols 等）の準備が必要です。
- news_nlp と regime_detector は gpt-4o-mini を前提にプロンプトを組んでおり、JSON Mode 出力を前提としたパースロジックを持ちます。モデル・API の挙動が変わるとパース/バリデーションの更新が必要です。
- strategy / execution / monitoring は __all__ に含まれているが、本リリースのソースには未実装または別モジュールで実装されることを想定しています。

Contact
-------
- バグ報告や提案はリポジトリの issue にお願いします。