CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースを記録しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- 初回リリース。日本株自動売買システム「KabuSys」の基礎機能を実装。
  - パッケージ公開
    - src/kabusys/__init__.py で主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
  - 設定管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数の読み込み機能を実装。
      - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
      - export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理を考慮した堅牢な行パーサを提供。
      - 設定参照用 Settings クラスを提供（必須キー取得時に未設定だと ValueError を送出）。
      - 環境変数の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値検証）とユーティリティプロパティ（is_live / is_paper / is_dev）。
  - データプラットフォーム（DuckDB ベース）
    - src/kabusys/data/*
      - calendar_management.py
        - JPX カレンダーの管理、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間バッチ更新（calendar_update_job）を実装。
        - market_calendar が未取得の場合の曜日ベースフォールバック、DB 優先の一貫した挙動、最大探索日数制限などの安全設計。
      - pipeline.py / etl.py
        - ETL パイプラインの枠組みと ETLResult データクラスを実装（差分取得、バックフィル、品質チェックの統合を想定）。
        - DuckDB テーブル存在チェック、最大日付取得ユーティリティなど。
      - jquants_client など外部 API クライアントと連携する設計（差分取得・冪等保存を前提）。
  - 研究用モジュール（Research）
    - src/kabusys/research/*
      - factor_research.py
        - モメンタム、ボラティリティ（ATR 等）、バリュー（PER/ROE）等のファクター計算を実装。
        - DuckDB の SQL ウィンドウ関数を活用し、(date, code) 単位で結果を返す設計。
      - feature_exploration.py
        - 将来リターン calc_forward_returns（複数ホライズン対応）、IC（Spearman の ρ）計算、ランク化ユーティリティ、ファクター統計サマリーを実装。
      - research パッケージは一部ユーティリティ（zscore_normalize）を再エクスポート。
  - AI / ニュース解析
    - src/kabusys/ai/news_nlp.py
      - ニュース記事から銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む処理を実装。
      - 前日15:00 JST〜当日08:30 JST の時間ウィンドウ計算（UTC 変換）や、銘柄ごとに記事を集約して最大文字数・記事数でトリム。
      - OpenAI（gpt-4o-mini）へのバッチコール（最大 20 銘柄/回）、JSON Mode を利用したレスポンス検証、リトライ（429/ネットワーク/5xx）・指数バックオフを実装。
      - レスポンスのバリデーションとスコアの ±1.0 クリップ、部分成功時に既存スコアを保護するための部分置換（DELETE → INSERT）。
      - テスト容易性のため _call_openai_api を差し替え可能。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
      - マクロニュース抽出、OpenAI 呼び出し、失敗時のフェイルセーフ（macro_sentiment=0.0）、リトライ・バックオフを実装。
      - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。
  - テスト性・堅牢性のための設計上の配慮
    - OpenAI 呼び出しはモジュール間で共有しない形で実装し、単体テストで差し替え可能（unittest.mock.patch を想定）。
    - API 呼び出し失敗時は例外で停止させずフェイルセーフ（0.0 を採用）で継続する箇所がある（ニュースセンチメント・マクロセンチメント等）。
    - DuckDB の executemany の挙動（空リスト不可など）に配慮した実装。
    - SQL クエリはルックアヘッドを避けるために date < target_date 等の条件を使用。
  - 公開 API と型
    - 主要関数は引数として DuckDB 接続と target_date を受け取り、副作用（DB 書き込み）は明示的に実行。
    - OpenAI API キーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出する。
    - ログ出力を多用し、警告・情報を記録する挙動。

Changed
- 初版につき該当なし。

Fixed
- 初版につき該当なし。

Known limitations / Notes
- 動作前提
  - DuckDB を利用するため適切なテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime 等）が必要。
  - OpenAI（gpt-4o-mini）を利用するため OPENAI_API_KEY が必須（score_news / score_regime はキー未設定で ValueError）。
  - J-Quants や kabu ステーション等の API キー（環境変数）を必要とする機能が含まれる（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）。
- 設計上の注意
  - 日付処理はタイムゾーンを混在させない方針（UTC naive を DB 比較に使用、JST ⇄ UTC の変換は明示的に実施）。
  - LLM の応答は必ず厳密な JSON を期待するが、実際の応答にノイズが混入することを考慮した復元処理を実装している。
  - 一部の失敗はログ記録のうえスキップする（フェイルセーフ）ため、呼び出し側で結果の妥当性チェックが推奨される。
- テスト支援
  - _call_openai_api の差し替えによるモック化を想定している（ユニットテストでの API 呼び出し抑止が容易）。

Security
- 初版につき該当なし。

Acknowledgements
- 本リリースは DuckDB と OpenAI API（JSON Mode）を中心に設計されており、外部データソース（J-Quants 等）との連携を前提にしています。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時は差分・コミット履歴・リリース方針に基づいて追記・修正してください。