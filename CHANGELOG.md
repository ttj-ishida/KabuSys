Keep a Changelog
================

このプロジェクトは "Keep a Changelog" の形式に従います。
リリースノートは安定版の変更点をわかりやすく記録することを目的としています。

未公開 (Unreleased)
--------------------
（現在のところ未公開の変更はありません）

0.1.0 - 2026-03-28
-----------------
初回公開リリース

追加 (Added)
- パッケージ全体の初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - 読み込みの優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサはコメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュでのエスケープに対応。
  - Settings クラスを公開（settings インスタンス）。以下のプロパティを提供:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - slack_bot_token (SLACK_BOT_TOKEN 必須)
    - slack_channel_id (SLACK_CHANNEL_ID 必須)
    - duckdb_path（デフォルト: data/kabusys.duckdb）
    - sqlite_path（デフォルト: data/monitoring.db）
    - env（KABUSYS_ENV: development/paper_trading/live の検証）
    - log_level（LOG_LEVEL の検証）
    - is_live / is_paper / is_dev のブール判定ユーティリティ

- AI 関連 (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を読んで、銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini、JSON mode）でセンチメント評価。
    - バッチ処理（最大 20 銘柄 / チャンク）、トークン肥大対策（記事数・文字数制限）、レスポンス検証、スコアの ±1.0 クリップ。
    - 再試行・バックオフ: 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフを実装。
    - テスト容易性のため _call_openai_api をパッチ可能に実装。
    - calc_news_window(target_date) を提供（タイムウィンドウ計算: 前日15:00 JST ～ 当日08:30 JST を UTC に変換）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出し時のリトライ・フォールバックロジック（API 失敗時は macro_sentiment=0.0）。
    - レジーム結果を market_regime テーブルに冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 内部でのルックアヘッドバイアス対策（datetime.today() を参照しない、DB クエリで date < target_date を使用）。

- リサーチ機能 (kabusys.research)
  - factor_research: calc_momentum, calc_value, calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が不正な場合 None）、ROE（raw_financials から取得）。
    - DuckDB SQL を主体に実装し、外部 API や本番発注ロジックは一切含まない。
  - feature_exploration: calc_forward_returns（任意ホライズン）、calc_ic（Spearman のランク相関）、rank、factor_summary（count/mean/std/min/max/median）。
    - rank は同順位を平均ランクにする実装、丸め処理で ties の検出精度を向上。

- データ基盤モジュール (kabusys.data)
  - calendar_management
    - market_calendar に基づく営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - calendar_update_job: J-Quants から差分取得・バックフィル・健全性チェックを行い market_calendar を更新するジョブを実装。
  - pipeline + ETLResult
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETL パイプライン共通ユーティリティ（最終取得日の算出、テーブル存在チェック、バックフィルのデフォルト等）。

- その他
  - duckdb との連携を前提に実装（多くの関数が DuckDB 接続オブジェクトを引数に取る）。
  - OpenAI Python SDK（OpenAI クライアント）を使用する想定で実装（api_key 引数や環境変数 OPENAI_API_KEY をサポート）。
  - ロギングを広範に追加（info/debug/warning/exception）。

変更 (Changed)
- 初回リリースのため履歴は初期追加のみ。

修正 (Fixed)
- 該当なし（初回リリース）。

破壊的変更 (Removed / Deprecated)
- 該当なし（初回リリース）。

セキュリティ (Security)
- 該当なし。

重要な注意点 / マイグレーション情報
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID またはそれに相当するテスト時のモック。
  - OpenAI を利用する機能を呼び出す場合は OPENAI_API_KEY を環境変数か各関数の api_key 引数で指定してください。未設定時は ValueError を送出します。
- 期待する DB スキーマ（DuckDB）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar などのテーブル構造を前提にしています。実行前にスキーマを準備してください。
- ルックアヘッドバイアス対策:
  - AI スコア (news_nlp, regime_detector) やリサーチ関数は内部で datetime.today()/date.today() を参照しない設計です。全て target_date ベースで動作します。
- テスト支援:
  - OpenAI 呼び出し部分は _call_openai_api を内部関数として実装しており、unittest.mock.patch などで差し替えてユニットテストが可能です。
- .env パーサの仕様:
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメントなど複数の .env 形式に対応しています。

今後の予定（ロードマップの例）
- ETL パイプラインの上位統合（スケジューラ・監視・差分実行フローの完成）
- 追加ファクターやポートフォリオ構築・評価機能の実装
- テストカバレッジ拡充と CI/CD パイプラインの整備
- OpenAI 呼び出しのコスト最適化・ローカル評価器の導入検討

貢献
- バグ報告、改善提案、プルリクエストは歓迎します。README / CONTRIBUTING（未実装）を参照してください。