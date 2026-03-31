Keep a Changelog
=================

すべての重要な変更はこのファイルに記載します。フォーマットは "Keep a Changelog" に準拠します。
このプロジェクトはセマンティックバージョニングに従います。

[Unreleased]

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリース。
- 基本メタ情報:
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境・設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを提供。
  - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは export 構文、クォート（エスケープ含む）、インラインコメントを考慮した堅牢な実装。
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（値検証: development, paper_trading, live）
    - LOG_LEVEL（値検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- データ基盤ユーティリティ（kabusys.data）
  - ETL パイプラインインターフェース（ETLResult の公開）。
  - calendar_management:
    - JPX（market_calendar）を扱う営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - 夜間バッチ更新ジョブ calendar_update_job（J-Quants クライアント経由の差分取得・冪等保存、バックフィル、健全性チェック）。
    - DB にデータがない場合は曜日ベースでフォールバックする堅牢な実装。
  - pipeline:
    - ETL の結果をまとめる ETLResult データクラス（品質チェック結果やエラーメッセージの収集機能含む）。
    - 差分更新 / バックフィル / 品質チェック方針に準拠した設計。

- ニュース NLP・AI サブシステム（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から時間ウィンドウ（JST 前日15:00～当日08:30）に基づいてニュースを集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を計算。
    - バッチサイズ、記事数・文字数制限、JSON Mode による厳格なレスポンス設計、結果バリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライと、失敗時フェイルセーフ（該当チャンクをスキップして継続）。
    - レスポンスパースの堅牢化（前後余計なテキストが入る場合の {} 抽出処理など）。
    - テスト容易性のため _call_openai_api をモック差し替え可能。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込み。
    - prices_daily を用いたルックアヘッドバイアス防止（target_date 未満のデータのみ使用）。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける。API エラー時は macro_sentiment=0.0（フォールバック）。
    - リトライロジック・ログ出力を実装。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などの計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率などの計算。
    - calc_value: raw_financials と結合して PER / ROE を算出（EPS が 0 や欠損の場合は None）。
    - DuckDB SQL を活用した効率的な実装。外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン算出（LEAD を利用）。ホライズンに対する入力検証あり。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル数が不足する場合は None。
    - rank: 同順位の平均ランク処理を行うランクユーティリティ（丸めで ties の検出漏れを防止）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - 研究向けユーティリティは標準ライブラリと DuckDB のみで実装（pandas 等に依存しない）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- AI 機能を呼び出す際は OpenAI API キー（OPENAI_API_KEY）を必須として検証し、未設定時は ValueError を発生させることで意図しない呼び出しを防止。

Notes / Usage
- OpenAI API を使う機能（score_news, score_regime）は API キーを必要とします。引数 api_key を指定するか、環境変数 OPENAI_API_KEY を設定してください。
- .env の自動ロードを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB をデータ格納に用いる設計のため、関数群は DuckDB の接続オブジェクト（DuckDBPyConnection）を受け取ります。
- News NLP のレスポンスは JSON Mode を前提とするため、OpenAI 側の出力変更に注意してください（レスポンス検証とフォールバックを実装済み）。

Breaking Changes
- なし（初回リリース）。

---- 

将来のリリースでは以下のような改善を予定（例）
- ai スコアのマルチモデル対応やロギングの強化
- データ品質チェック（quality モジュール）との連携強化およびセルフヒーリング機構
- pipeline のより細かなジョブ制御・スケジューリング機能

（以上）