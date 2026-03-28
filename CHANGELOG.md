# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

全般
- 日付表記は YYYY-MM-DD。
- このリポジトリに含まれる機能は主にデータ取得・前処理（ETL）・研究（リサーチ）・AI ベースのニュースセンチメント評価・市場レジーム判定・カレンダー管理・設定読み込みを提供します。
- DuckDB を主要な組み込みデータストアとして利用します。
- OpenAI（gpt-4o-mini）を用いた JSON Mode での API 呼び出しを行います（API キーは引数または環境変数 OPENAI_API_KEY で指定）。

[Unreleased]
- （現状なし）

[0.1.0] - 2026-03-28
Added
- パッケージ基本構成
  - kabusys パッケージの初期公開。サブパッケージ: data, research, ai, monitoring/strategy/execution を想定した名前空間をエクスポート。
  - バージョン: 0.1.0

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env パーサはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの基本的な取り扱いをサポート。
  - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL などをプロパティとして取得。
  - KABUSYS_ENV の検証（development, paper_trading, live）と LOG_LEVEL の検証を実装。
  - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- データプラットフォーム機能（kabusys.data）
  - calendar_management: JPX カレンダー管理、営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 日判定（is_sq_day）を実装。
    - market_calendar テーブルが未取得の場合は曜日ベースでフォールバック。
    - データがまばらでも DB 値を優先して一貫性を保つ実装。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル／健全性チェックを実装。
  - etl / pipeline: ETLResult データクラスを公開。差分取得、保存、品質チェックの流れを想定した ETL パイプライン基盤を用意。
    - DuckDB 上のテーブル存在チェックや最大日付取得ユーティリティを提供。
    - ETLResult は品質問題やエラーの集約/辞書化をサポート。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄ごとに最新記事（最大件数・最大文字数でトリム）をまとめて OpenAI にバッチ送信。
    - gpt-4o-mini の JSON Mode を利用し、{"results": [{"code": "XXXX", "score": 0.0}, ...]} 形式でスコアを受け取る想定。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。失敗時は該当チャンクをスキップし処理継続（フェイルセーフ）。
    - レスポンスのバリデーションと ±1.0 へのクリップを実施。
    - DuckDB executemany に関する互換性考慮（空リスト渡し回避）を反映した安全な書き込み処理（DELETE→INSERT の置換方式）。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。

  - regime_detector.score_regime:
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出して market_regime テーブルに冪等書き込み。
    - ma200_ratio は DuckDB の prices_daily から target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロキーワードで raw_news をフィルタして LLM に送信。API 失敗時は macro_sentiment=0.0 として継続。
    - OpenAI クライアント生成部分は api_key 引数または環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出。

- Research（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M・ma200乖離）、ボラティリティ（20日 ATR）、バリュー（PER/ROE）などのファクター計算を提供（prices_daily / raw_financials を参照）。結果は (date, code) をキーとする dict リストで返す。
    - calc_momentum / calc_volatility / calc_value を実装。データ不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションを実装。
    - calc_ic: factor と forward return の Spearman ランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を実装。
  - zscore_normalize は kabusys.data.stats から再エクスポート（初期 API 整備）。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Removed
- （初回リリースのため削除履歴なし）

Security
- 環境変数（OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）を必須とする設定が多いため、秘匿情報は .env ファイルまたは OS 環境変数で管理すること。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- OpenAI の呼び出しに関してはリトライ制御・フェイルセーフ（スコア 0.0 にフォールバック）を入れているが、API キーの漏洩には注意。

Notes / Known limitations
- 本コードは DuckDB を想定しているため、他の SQL エンジンでは互換性のない SQL 式（window 関数や executemany の挙動）を使用している箇所がある。
- OpenAI SDK の挙動（例: APIError の status_code 所有の有無）に依存する箇所があり、SDK の将来変更に備えた defensive コードを入れているが、互換性テストが必要。
- datetime.today()/date.today() を内部実装で参照しない方針（ルックアヘッドバイアス防止）。すべて関数呼び出し側から target_date を与える設計。
- news_nlp / regime_detector は外部 API（OpenAI）に依存するため、ネットワークやレート制限の影響を受ける。失敗時の部分スキップ戦略を採用している。
- DuckDB executemany に空リストを渡すと問題になるバージョンがあるため、空チェックを行っている。

Dependencies / 環境
- Python: 型ヒントで | を使用しているため Python 3.10 以降を想定。
- 外部ライブラリ: duckdb, openai（OpenAI の Python SDK）
- データベース: DuckDB を利用（ai_scores, prices_daily, raw_news, market_calendar, raw_financials, news_symbols, market_regime 等のテーブルスキーマを想定）

Usage highlights
- 設定参照例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
- ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")
- 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

マイグレーション / 移行手順
- なし（初回公開）。今後バージョンアップ時は API の互換性や DB スキーマ変更を明記します。

貢献
- バグ修正、テスト追加、ドキュメント改善、DB スキーマの明文化などの貢献を歓迎します。