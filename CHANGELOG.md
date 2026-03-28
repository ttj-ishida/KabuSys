CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に準拠して記載しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現時点のコードはバージョン 0.1.0 としてリリース済みの想定です。今後の変更はここに追記してください。）

[0.1.0] - 2026-03-28
--------------------

Added
- 初回リリース。日本株自動売買・データ基盤向けライブラリ "KabuSys" の主要機能を追加。
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - エクスポート: data, strategy, execution, monitoring（__all__）
  - 環境設定管理（kabusys.config）
    - .env / .env.local 自動ロード機能（優先順位: OS 環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途向け）。
    - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - 環境変数取得ユーティリティ Settings 提供:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
      - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
      - KABUSYS_ENV（development / paper_trading / live 検証）、LOG_LEVEL（DEBUG/INFO/... 検証）
      - is_live / is_paper / is_dev ヘルパー

  - AI ニュース分析（kabusys.ai）
    - news_nlp.score_news
      - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを取得。
      - バッチ処理（最大 20 銘柄／API 呼び出し）、トークン肥大化対策（記事数・文字数制限）。
      - JSON モードを利用したレスポンス検証・パース。冗長な前後テキストが混入する場合の復元処理あり。
      - 429／ネットワーク断／タイムアウト／5xx に対する指数バックオフのリトライ。
      - スコアは ±1.0 にクリップ。取得スコアのみ ai_scores テーブルに部分置換（DELETE → INSERT）して部分失敗時の既存データ保護。
      - テスト用に内部の _call_openai_api をパッチ差し替え可能。

    - regime_detector.score_regime
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp によるマクロセンチメント（重み 30%）を合成して市場レジームを判定（bull / neutral / bear）。
      - prices_daily / raw_news / market_regime テーブルを使用し、冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
      - API 呼び出しで問題が発生した場合は macro_sentiment=0.0 へフォールバックするフェイルセーフ実装。
      - OpenAI クライアント生成は引数 api_key または環境変数 OPENAI_API_KEY を参照。内部の _call_openai_api はニュースモジュールと独立実装。

  - データ処理基盤（kabusys.data）
    - calendar_management
      - JPX カレンダー管理と営業日判定ユーティリティ群を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
      - market_calendar がない場合は曜日ベースでフォールバック（週末を非営業日扱い）。
      - 夜間バッチ job（calendar_update_job）: J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存を実装。
      - 最大探索日数・ルックアヘッド・バックフィル日数などの安全パラメータを導入して異常時の保護を実装。

    - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
      - ETLResult データクラスを公開（ETL 実行のメタ情報と品質チェック情報を保持）。
      - 差分更新、バックフィル、品質チェック（kabusys.data.quality 連携）の設計方針を反映。
      - DuckDB を前提としたテーブル存在チェック・最大日付取得等のユーティリティ実装。

  - 研究用機能（kabusys.research）
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
      - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（EPS=0/欠損時は None）。
      - 実装は DuckDB 上の SQL + Python。欠損データ時の None 処理やデータ不足への警告を含む。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを取得（LEAD を使用）。
      - calc_ic: スピアマンランク相関（IC）を計算（最小サンプル数判定、None 返却）。
      - rank: 同順位は平均ランクで扱う実装（丸めによる ties 回避）。
      - factor_summary: count/mean/std/min/max/median を算出する軽量実装（外部依存なし）。

  - 共通設計上の注意点（ドキュメント的特徴）
    - すべての「日付ベース」処理は datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス防止）。target_date を明示して呼び出す設計。
    - OpenAI 呼び出しは JSON Mode を利用し、パース失敗や API エラーに対して堅牢にフォールバックする実装。
    - DuckDB を主要な格納先と想定。executemany の空パラメータ回避など DuckDB 互換性考慮あり。
    - テスト容易性のため内部 API 呼び出しポイント（_call_openai_api など）をパッチ可能に設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーを環境変数 OPENAI_API_KEY または関数引数で解決する方式。キーの取り扱いは呼び出し側で適切に管理すること。

Notes / Breaking changes
- これは初回の公開バージョンの changelog です。今後のマイナー／メジャー変更では API（関数シグネチャ、テーブルスキーマ、環境変数名など）の互換性に影響する可能性があります。
- DuckDB テーブル名やカラム（prices_daily, raw_news, ai_scores, market_regime, raw_financials, news_symbols など）を前提とする実装が多数あるため、既存データスキーマを変更する場合は互換性に注意してください。

作者注記
- 各 AI 呼び出しは外部サービス（OpenAI）に依存するため、実行環境ではネットワーク接続および適切な API キー設定が必要です。
- .env 自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に依存します。パッケージ配布後の利用環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してロードを制御してください。