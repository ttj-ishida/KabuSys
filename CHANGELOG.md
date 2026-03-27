CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングに従います。

未リリース
--------

（現在の開発中の変更はここに記載します）

0.1.0 - 2026-03-27
------------------

Added
- 基本パッケージ初回リリースを追加
  - パッケージ情報: kabusys v0.1.0
  - パッケージ公開用 __all__ に data/strategy/execution/monitoring を準備

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）
  - export KEY=val 形式、クォート・エスケープ、行末コメントなどを考慮した .env パーサを実装
  - 必須設定取得の _require() を提供（未設定時は ValueError）
  - 設定プロパティ（Settings）を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL の検証
    - is_live/is_paper/is_dev のヘルパー

- データ関連モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX カレンダー取得と夜間バッチ更新 job（calendar_update_job）
    - market_calendar に基づく営業日判定 API:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 未取得日の曜日ベースフォールバック、最大探索範囲制限、不整合検出とログ出力
  - ETL パイプライン関連（pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.ETLResult として再エクスポート）
    - 差分取得・バックフィルロジック、品質チェックインテグレーションの設計方針と基本実装
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティ

- AI（自然言語・レジーム判定）（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を統合して、銘柄ごとにニュースを集約
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチセンチメント評価（最大バッチ 20 銘柄）
    - タイムウィンドウ計算（JST 前日 15:00 〜 当日 08:30 を UTC に変換）
    - 各種耐障害設計:
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ
      - レスポンスの厳密バリデーション（results 配列、code/score の検証、数値判定）
      - スコアを ±1.0 にクリップ
      - 部分失敗時に既存データを保護するため、対象コードのみ DELETE→INSERT 置換
    - テスト用に _call_openai_api を patch できる設計
    - score_news(conn, target_date, api_key=None) により書き込んだ銘柄数を返す
  - 市場レジーム判定（regime_detector）
    - 日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）
    - 判定ロジック:
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
      - レジームスコア = clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
      - API 失敗時は macro_sentiment=0.0 のフェイルセーフ
    - DuckDB を用いた冪等な書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）
    - OpenAI 呼び出しは独立実装（news_nlp と結合しない設計）、テスト用に置き換え可能
    - score_regime(conn, target_date, api_key=None) は成功時に 1 を返す

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率 等
    - calc_value: PER / ROE（raw_financials からの最新財務データを使用。EPS が 0/欠損時は None）
    - DuckDB を使った SQL 中心の実装（本番口座・発注 API へアクセスしない）
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを返す
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（少数レコード時は None）
    - rank: 同順位は平均ランクにする実装（丸めで ties 判定を安定化）
    - factor_summary: count/mean/std/min/max/median を計算

Changed
- 初期設計段階における API 仕様と内部実装を整備
  - すべての時刻計算は lookahead バイアスを避けるため date/target_date ベースで実行し、datetime.today()/date.today() の乱用を避ける設計を採用
  - DuckDB を想定した SQL 実装で互換性とパフォーマンスを考慮

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI / 外部 API キーの取り扱い:
  - API キーが未設定の場合、score_news/score_regime は ValueError を送出して明示的に失敗
  - .env 読み込み時に OS 環境変数を保護するため protected set を導入し、.env.local による上書きを制御
- 機密情報（API キー等）は環境変数で管理する想定

Notes / Implementation details（補足）
- DuckDB を前提としたテーブル名（例: prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols）をコード中で参照
- OpenAI 呼び出しは gpt-4o-mini + JSON Mode を利用する設計で、レスポンスの頑健なパース・復元処理を実装
- 各種処理は冪等性（DB の DELETE→INSERT、ON CONFLICT DO UPDATE 想定）と部分失敗耐性を重視
- 各モジュールにログ出力を多用しているため、LOG_LEVEL による制御が可能
- テスト容易性を意識し、外部 API 呼び出し関数は patch 可能に実装

Acknowledgements
- 初回リリース。利用方法、マイグレーション、既知の制限や TODO は別ドキュメント（README / StrategyModel.md / DataPlatform.md）で補足予定。

--- 

（以降のリリースでは Unreleased → バージョン の移動、変更点の追加を行ってください。）