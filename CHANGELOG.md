Keep a Changelog
=================

すべての変更はセマンティックバージョニングに従います。  
本ファイルは Keep a Changelog 準拠のフォーマットでリリース履歴を記載します。

[0.1.0] - 2026-03-31
-------------------

Added
- 初回公開: kabusys パッケージ基盤を追加
  - パッケージエントリポイント (src/kabusys/__init__.py) とバージョン 0.1.0 を定義。
- 環境設定管理 (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で探索）。
  - export 形式やクォート、インラインコメント対応の行パーサ実装。
  - OS 環境変数を保護する protected 上書きロジック、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等のプロパティ）。
  - 必須環境変数未設定時は明確な ValueError を送出。
- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から銘柄別に記事を集約し、OpenAI(gpt-4o-mini) により銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込み。
    - ニュース集計ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算する calc_news_window を提供。
    - 1 銘柄あたりの最大記事数・文字数トリム、最大バッチサイズ（20 銘柄）によるバッチ処理。
    - JSON Mode の利用想定とレスポンスバリデーション（results 配列・コード照合・数値チェック）、スコア ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、フェイルセーフとして失敗時は該当チャンクをスキップ（例外は伝播させず継続）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可能）。
  - レジーム検出 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window で定めたウィンドウからマクロキーワードで抽出。
    - OpenAI 呼び出しはリトライやエラー分類を含む堅牢な実装。API 失敗時は macro_sentiment=0.0 を使うフェイルセーフ。
    - ルックアヘッドバイアス防止のため date 引数を使用し datetime.today() に依存しない設計。
- データプラットフォーム / ETL (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベース（週末を非営業日）でフォールバックする一貫した動作。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得 → 保存（バックフィルや健全性チェックを含む）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラーなどを集約）。
    - 差分更新・バックフィル・品質チェックの考慮（quality モジュールと連携する想定）。
    - etl モジュールは pipeline.ETLResult を再エクスポート。
  - データアクセスに DuckDB を採用（DuckDBPyConnection を想定した SQL 実装）。
- リサーチ / ファクター群 (src/kabusys/research)
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出。
    - 実装は DuckDB 上の SQL を中心にし、欠損やデータ不足時は None を返す設計。
  - feature_exploration モジュール
    - calc_forward_returns: 複数ホライズンの将来リターンを一括取得（安全な horizons 検証あり）。
    - calc_ic: スピアマンのランク相関（IC）を計算（結合・欠損処理・最小サンプルチェックあり）。
    - rank: 同順位は平均ランクを返す実装（浮動小数丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
- ロギングとエラーハンドリング
  - 多数の関数で適切な logger.debug/info/warning/exception を追加し、フェイルセーフでの継続や ROLLBACK 処理を実装。
- テストしやすさの考慮
  - OpenAI 呼び出しをモック差し替え可能、api_key を引数注入できる箇所が多数（score_news, score_regime など）。

Security
- 環境変数の敏感情報（API キー等）は Settings を通じて取得し、未設定時はエラーを明示。自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Required environment variables
- 動作に利用される主な環境変数:
  - OPENAI_API_KEY (AI モジュールで必須)
  - JQUANTS_REFRESH_TOKEN (J-Quants API)
  - KABU_API_PASSWORD (kabu API)
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (通知)
  - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。