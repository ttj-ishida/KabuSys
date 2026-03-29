CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に従い、セマンティックバージョニングを使用します。

Unreleased
----------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初回公開（kabusys v0.1.0）
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0"、および主要サブパッケージの __all__ を定義。

- 設定・環境変数管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）または OS 環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動読み込みを実現。
    - .env のパース実装（コメント、export プレフィックス、クォート内のエスケープ、インラインコメント処理などに対応）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 環境変数未設定時に例外を投げる必須取得ヘルパ _require と、Settings クラスを提供。
    - Settings により J-Quants / kabu ステーション / Slack / DB パス / ログレベル / 実行環境（development/paper_trading/live）等のプロパティを公開。

- AI モジュール（ニュース NLP / 市場レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を用い、銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini、JSON mode）へ一括送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチサイズ、記事数・文字数トリム、レスポンス検証、スコアクリップ（±1.0）、リトライ（429/ネットワーク/5xx）と指数バックオフを実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - フェイルセーフ設計：API 失敗時はスキップし継続（例外を上位に伝播させない）、NULL/不正レスポンスは無視。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込む score_regime を実装。
    - マクロ記事抽出、OpenAI 呼び出し（gpt-4o-mini、JSON mode）、リトライ・バックオフ、API 失敗時のフォールバック（macro_sentiment=0.0）などを実装。
    - ルックアヘッドバイアス対策：date 引数を基準に DB をクエリし、datetime.today()/date.today() を直接参照しない設計。

- データプラットフォーム（Data）関連
  - src/kabusys/data/calendar_management.py
    - JPX 市場カレンダー管理機能を提供（market_calendar の読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新ジョブ calendar_update_job）。
    - DB にデータがない場合の曜日ベースのフォールバックや、最大探索日数の保護、バックフィル／健全性チェック等を実装。
    - J-Quants クライアント経由のフェッチ/保存との連携（差分取得・冪等保存の想定）。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプライン用ユーティリティと返却用データクラス ETLResult を実装。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携）等を想定した設計。
    - ETLResult は処理統計・品質問題・エラー情報を保持し、辞書化ユーティリティを提供。

  - jquants_client 関連 API の想定インターフェースを利用する設計（fetch/save 関数呼び出し箇所を用意）。

- Research（因子／特徴量探索）
  - src/kabusys/research/* にて以下関数を実装・公開：
    - calc_momentum, calc_volatility, calc_value（ファクター計算）
    - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・IC 計算・統計サマリ）
    - zscore_normalize は外部の kabusys.data.stats から再公開
  - 実装は DuckDB の SQL と純粋 Python（外部依存を避ける）で行い、prices_daily / raw_financials テーブルのみを参照する設計。

- DB / トランザクション設計
  - DuckDB を利用した SQL 実装（多くの関数で明示的な BEGIN/COMMIT/ROLLBACK を使用し、冪等書き込みパターンを採用）。
  - executemany の空パラメータ回避（DuckDB 0.10 の互換性考慮）や、NULL の取扱いに注意した集計実装。

- 例外処理・ログ
  - API 呼び出しの失敗はログで警告/例外記録し、失敗時は安全側のデフォルトを用いる（例: macro_sentiment=0.0、スコア未取得はスキップ）。
  - 各モジュールで詳細なデバッグ/情報ログを出力。

Changed
- 新規リリースのため変更なし（初回提供）。

Fixed
- 新規リリースのためなし。

Security
- 秘密情報（OpenAI API キー、J-Quants トークン、Kabu API パスワード、Slack トークン等）は必須環境変数として Settings 経由で取得。未設定時は ValueError を送出する仕様を採用。
- .env 自動ロード時に OS 環境変数は保護され、.env.local による上書きは許可するが保護されたキーは上書きされない挙動。

注意事項 / 既知の制限
- OpenAI クライアントは gpt-4o-mini（JSON mode）を前提に実装。将来的なモデル変更や SDK 変更に影響を受ける可能性あり。
- DuckDB のバージョン差異（特に executemany・リストバインドの扱い）を考慮した実装を行っているが、運用環境の DuckDB バージョンに依存する可能性あり。
- 外部 API（J-Quants / OpenAI / kabu）が利用不可な場合は一部処理がスキップされる設計。重要なステップで例外を上げる箇所（たとえば DB 書き込み失敗）は呼び出し元でハンドルが必要。
- datetime.today()/date.today() を直接参照しない設計により、target_date を明示的に渡す運用が前提。

参考（主な公開 API）
- Settings（kabusys.config.settings）: 環境設定プロパティ群
- AI:
  - score_news(conn, target_date, api_key=None) -> int（ai_scores への書き込み件数）
  - score_regime(conn, target_date, api_key=None) -> int（market_regime への書き込み成功）
- Data:
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day, calendar_update_job
  - ETLResult（kabusys.data.pipeline.ETLResult）
- Research:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---

このリリースは初版の公開版です。ご利用・フィードバックにより改良・バグ修正を行っていきます。