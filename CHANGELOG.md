CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。訳注: 以下はコードベースから推測して作成した初期リリース向けの変更履歴です。

[Unreleased]
------------

- （現時点の変更なし）

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ初期公開: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
  - パッケージの公開 API に data, strategy, execution, monitoring を定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装（コメント、export プレフィックス、クォート内のエスケープ処理、インラインコメント処理などに対応）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / データベース / システム設定（KABUSYS_ENV, LOG_LEVEL）をプロパティとして提供。
  - 必須設定が未設定の場合に ValueError を送出する _require ヘルパーを提供。

- AI モジュール (kabusys.ai)
  - news_nlp モジュールを実装（score_news）
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON mode を用いたバッチセンチメント評価を実装。
    - チャンク処理（デフォルト 20 銘柄/回）、記事トリム、スコアのバリデーションおよび ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフとリトライを実装。
    - レスポンス不整合時は安全にスキップし続行（例外を投げずフェイルセーフ）。
    - ai_scores テーブルへの冪等書き込み（対象コードのみ DELETE → INSERT）を実装。
    - calc_news_window ヘルパーを実装（前日 15:00 JST 〜 当日 08:30 JST の UTC 範囲を計算）。
  - regime_detector モジュールを実装（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - マクロニュースは news_nlp.calc_news_window に基づき抽出、OpenAI によりマクロセンチメントを取得。
    - API 呼び出しのリトライ・タイムアウト・フェイルセーフ処理を実装。API 失敗時は macro_sentiment=0.0 をフォールバック。
    - market_regime テーブルへ冪等的に書き込むトランザクション制御（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - AI モジュールは OpenAI クライアント呼び出しをテスト容易に差し替え可能（内部の _call_openai_api を patch 可能）。

- Data モジュール (kabusys.data)
  - calendar_management を実装
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック付き）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを導入（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新・バックフィル・品質チェックを想定したユーティリティ関数群を実装（内部ユーティリティ: _table_exists, _get_max_date 等）。
    - jquants_client を介した取得と jquants 側 save_* の呼び出しを想定。
  - etl モジュールで pipeline.ETLResult を再エクスポート。

- Research モジュール (kabusys.research)
  - factor_research を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比等を計算。
    - calc_value: raw_financials から PER/ROE を計算（最新報告基準）。
    - DuckDB ベースの SQL 実装で、データ欠損時の安全処理を実装。
  - feature_exploration を実装
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位を平均ランクとするランク化ユーティリティ。
    - factor_summary: ファクター列の基本統計（count/mean/std/min/max/median）を計算。
  - research パッケージの __all__ に主要関数群を公開。

- その他ユーティリティ
  - 各モジュールで「ルックアヘッドバイアスを避ける」方針を採用（datetime.today()/date.today() を内部で参照せず、target_date を明示的に受け取る）。
  - DuckDB 互換性に関する注意（executemany の空リスト不可等）を考慮した実装。
  - ロギングと警告メッセージを多用し、異常時に安全に継続する設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （現時点で既知のセキュリティ修正はなし）

注意事項（Usage / Migration）
- OpenAI API を利用する機能（score_news, score_regime）は OPENAI_API_KEY を環境変数で設定するか、各関数の api_key 引数で渡す必要があります。未設定の場合は ValueError が発生します。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックされます（未設定時 ValueError）。
- 自動で .env を読み込む仕組みを持ちますが、テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- DuckDB を使用したテーブル（prices_daily, raw_news, market_calendar, ai_scores, raw_financials 等）が前提です。テーブルスキーマは実装コメントや DataPlatform/Strategy 文書に従って作成してください。
- AI 呼び出しは外部 API に依存するため、ネットワーク障害やレート制限対策が組み込まれています。API 失敗時は多くの処理が安全にフォールバックしますが、期待するスコアが得られない可能性があります。

貢献
- 初期実装のため、機能追加や不具合報告、テストケースの整備を歓迎します。