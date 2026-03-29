CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記録します。  
このファイルは主にコードベースから推測して作成した初期リリースの変更履歴です。

フォーマット:
- 変更カテゴリは Added / Changed / Fixed / Deprecated / Removed / Security を使用しています。
- 日付は推測に基づき付与しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース (0.1.0)
  - パッケージのバージョン管理:
    - kabusys.__version__ を "0.1.0" に設定。
  - 設定・環境変数管理 (kabusys.config)
    - .env / .env.local 自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサ実装:
      - export KEY=val 形式に対応。
      - シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いを考慮したパース。
      - 無効行（空行やコメント行等）は無視。
    - 環境変数取得ヘルパー _require と Settings クラスを提供。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須キーを明示。
      - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供（data/kabusys.duckdb, data/monitoring.db）。
      - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証（DEBUG/INFO/...）。
      - 環境に応じたユーティリティプロパティ: is_live / is_paper / is_dev。

  - AI 関連 (kabusys.ai)
    - ニュース NLP (kabusys.ai.news_nlp)
      - score_news(conn, target_date, api_key=None):
        - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI (モデル: gpt-4o-mini, JSON mode) を使ってセンチメントスコアを計算し ai_scores テーブルへ書き込み。
        - タイムウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換した上で DB クエリに使用）。
        - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたりは記事数・文字数制限（上限 _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
        - リトライ/バックオフ: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
        - レスポンス検証: JSON 抽出、"results" 構造検証、未知コード除外、スコア数値化・±1.0 クリップ。
        - 部分失敗に強い DB 書き込み設計（対象コードのみ DELETE → INSERT を行い既存スコアを保護）。
        - テスト用に _call_openai_api を patch して差し替え可能。
    - 市場レジーム判定 (kabusys.ai.regime_detector)
      - score_regime(conn, target_date, api_key=None):
        - ETF 1321 の 200 日移動平均乖離 (重み 70%) とマクロ経済ニュースの LLM センチメント (重み 30%) を合成して日次レジームを判定（'bull' / 'neutral' / 'bear'）。
        - ma200_ratio の計算は target_date 未満データのみ使用（ルックアヘッドバイアス防止）。
        - マクロ記事抽出は news_nlp.calc_news_window と連携し、マクロキーワードでフィルタ。
        - OpenAI 呼び出しは独立実装で、リトライ・エラーハンドリング（RateLimit/Connection/Timeout/APIError）を実装。API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
        - 最終的に market_regime テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
        - 設計方針として datetime.today()/date.today() を直接参照せず、入出力の明示化でルックアヘッドを防止。

  - データプラットフォーム (kabusys.data)
    - カレンダー管理 (kabusys.data.calendar_management)
      - JPX カレンダー管理: market_calendar テーブルを元に営業日判定ロジックを提供。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - DB 登録がない場合は曜日ベース（土日非営業日）でのフォールバック。DB 登録がある場合は DB 値を優先して一貫性を保つ設計。
      - カレンダー夜間バッチ update_job (calendar_update_job) を追加: J-Quants API から差分取得・バックフィル（直近 _BACKFILL_DAYS）・健全性チェックを行い、jquants_client を介して保存。
      - 最大探索や健全性チェック（_MAX_SEARCH_DAYS、_SANITY_MAX_FUTURE_DAYS）により無限ループ・異常値を防止。
    - ETL パイプライン (kabusys.data.pipeline / etl)
      - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
      - 差分更新、バックフィル、品質チェック（quality モジュール経由）を想定した ETL の基盤設計。
      - _get_max_date / _table_exists 等のユーティリティを提供。
      - ETLResult は品質問題の集計やエラー有無判定ヘルパーを持つ。
      - J-Quants クライアント (jquants_client) 経由で idempotent な保存を前提とする設計。

  - リサーチ機能 (kabusys.research)
    - factor_research:
      - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
      - Value: PER / ROE（raw_financials の最新報告を参照）。
      - DuckDB のウィンドウ関数を活用した SQL ベースの実装。
    - feature_exploration:
      - calc_forward_returns (任意ホライズンで将来リターン取得)、calc_ic (Spearman ランク相関)、rank（平均ランクの tie 処理）、factor_summary（基本統計量）。
      - 外部依存（pandas 等）を用いず標準ライブラリ + DuckDB で実装。
    - research パッケージは主要関数を上位で再エクスポートして簡易に利用可能。

  - パッケージ公開 API
    - kabusys.__all__ に data/strategy/execution/monitoring を列挙（将来のサブパッケージを想定）。
    - ai および research の __init__ で主要関数を再エクスポート。

Changed
- （初回リリースのため過去バージョンからの変更はなし）

Fixed
- （初回リリースのため過去バージョンからの修正はなし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- OpenAI API キーの取り扱い:
  - score_news / score_regime は api_key 引数を受け取る（None の場合は環境変数 OPENAI_API_KEY を参照）。キー未設定時は ValueError を送出して安全に失敗する設計。

Notes / 設計上の重要事項（開発者向け）
- ルックアヘッドバイアス対策:
  - AI・研究・ファクター計算・ETL いずれも内部で date.today()/datetime.today() を直接参照せず、target_date を明示的に受け取る方針。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを 0.0 にフォールバックする（例外を投げず処理を継続）する箇所があるため、上位での監視・アラートが推奨される。
- テスト容易性:
  - OpenAI 呼び出し部分は内部関数を patch して差し替えることを想定している（unittest.mock など）。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB のバージョン差異を考慮した実装上の注意がある。

将来の提案（推奨）
- strategy / execution / monitoring サブパッケージの具体的な公開 API 定義とドキュメントを追加。
- QA: quality モジュールと jquants_client の実装に対するユニット・統合テストの整備。
- 運用: OpenAI 呼び出しのコスト/レート管理、Slack 通知・監視ルールの整備。

--- 

注: 本 CHANGELOG は提供されたコード内容から推測して作成しています。実際のリリースノートや運用ポリシーと差異がある場合は、該当ドキュメントを優先してください。