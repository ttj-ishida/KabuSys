CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。本プロジェクトは Keep a Changelog の方針に従います。
リリースにはセマンティックバージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装。
- パッケージエントリポイントを提供（kabusys.__version__ = 0.1.0、__all__ を定義）。
- 環境設定管理（kabusys.config）を実装:
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化スイッチ。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等の実務的な形式に対応。
  - 環境変数必須チェック用 _require と Settings クラスを提供。J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等の設定プロパティを公開。
  - 不正な KABUSYS_ENV や LOG_LEVEL に対する妥当性検査（ValueError）。

- AI モジュール（kabusys.ai）を追加:
  - ニュースNLP スコアリング（kabusys.ai.news_nlp.score_news）:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を算出。
    - JST 時間ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づく対象抽出（UTC 変換済）。
    - 1チャンクあたり最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリム。
    - JSON Mode 応答の厳密な検証、余計な前後テキストが混ざるケースの復元処理あり。
    - レート制限・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライし、最終的に失敗したチャンクはスキップ（フェイルセーフ）。
    - DuckDB 互換性のため、空 params を executemany に渡さないガード。
    - テスト用に _call_openai_api を patch 可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を利用して DB に冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しの個別実装、API エラー時のフォールバック macro_sentiment=0.0、リトライ・バックオフ対応。
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照しない設計（呼び出し側で target_date を与える）。

- データプラットフォーム（kabusys.data）を追加:
  - カレンダー管理（kabusys.data.calendar_management）:
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日リスト取得・SQ 判定機能を提供。
    - market_calendar が未取得または値が NULL の場合は曜日ベース（週末除外）でフォールバック。
    - _MAX_SEARCH_DAYS による無限ループ回避、DB 登録値の優先、部分的データ（まばらな DB）の一貫性保持。
    - JPX カレンダー夜間バッチ更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で取得・保存（バックフィル・健全性チェックを含む）。

  - ETL パイプライン（kabusys.data.pipeline）:
    - 差分取得、保存、品質チェック（quality モジュール）を行う ETL フレームワークの基礎を実装。
    - ETLResult データクラスを導入（target_date, fetched/saved counts, quality_issues, errors, to_dict 等）。
    - 最小データ日（_MIN_DATA_DATE）、バックフィル（デフォルト 3 日）等の設計方針を反映。
    - DuckDB を想定したテーブル存在チェック・最大日付取得ユーティリティ。

  - エクスポート（kabusys.data.etl）で ETLResult を公開。

  - jquants_client 等の外部クライアントとの連携ポイント（fetch/save 関数の利用）を設計に含む（実装は別モジュール想定）。

- リサーチモジュール（kabusys.research）を追加:
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB に対する SQL ベースの計算で、データ不足時は None を返す等の堅牢性。
  - feature_exploration:
    - 将来リターン算出（calc_forward_returns、任意 horizon 対応）、IC（スピアマン）計算（calc_ic）、ランク関数（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - データユーティリティ（z-score 正規化）は kabusys.data.stats から再利用。

- 共通設計上の注意点（プロジェクト全体に共通）:
  - ルックアヘッドバイアスを避けるため、日付は全て呼び出し側からの target_date に依存し、内部で現在日時を参照しない実装。
  - DB 書き込みは冪等性を重視（DELETE→INSERT など）し、失敗時は ROLLBACK を試みる。
  - OpenAI 呼び出しや外部 API についてリトライ処理とフェイルセーフ（失敗時は 0 相当で継続）を実装。
  - テストしやすさを考慮し、API 呼び出し関数は patch 可能に分離。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Security
- 環境変数の自動ロードで OS 環境変数を保護するため protected set を使用（.env.local の上書き制御含む）。
- OpenAI API キーは引数注入か OPENAI_API_KEY 環境変数のみを受け付け、未設定時は ValueError を投げることで誤った実行を防止。

Notes
- 依存: duckdb, openai SDK（OpenAI クライアント）、およびプロジェクト内で参照する jquants_client 等の外部モジュールが必要。
- 実行環境によっては .env/.env.local の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN など）を事前に用意してください。
- 本リリースは「データ取得・解析・スコアリング・カレンダー管理・ファクター計算」の基盤を提供します。発注/実行周り（kabu 実取引ロジック）や監視・運用ジョブは別モジュールにて段階的に追加予定。

References
- Keep a Changelog: https://keepachangelog.com/en/1.0.0/