Keep a Changelog
=================
すべての注目に値する変更点をこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" の慣習に従っています。

フォーマット
-----------
各リリースは日付付きで記載し、主要なカテゴリ（Added, Changed, Fixed, Removed, Security, Known issues 等）でまとめています。

[Unreleased]
------------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-01
-------------------

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト向け）
  - .env パーサは以下をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント判定（直前が空白/タブの場合のみ）
  - 環境変数未設定時に例外を投げる _require と Settings クラスを提供
  - 主要設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - OPENAI_API_KEY（AI モジュールで参照。未設定時は関数が ValueError を投げる）
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス
    - PID_FILE_PATH / CPU/MEMORY/DISK の監視閾値
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄単位で LLM（gpt-4o-mini）へ送信し ai_scores を作成
  - 処理特徴:
    - JST ベースのニュースウィンドウ（前日15:00〜当日08:30）を calc_news_window で算出
    - 1銘柄当たり最大記事数・最大文字数でトリム（トークン肥大化対策）
    - 最大 20 銘柄/チャンクでのバッチ送信（_BATCH_SIZE）
    - JSON Mode を用いた厳密な JSON パース・バリデーション（results list, code, score）
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ
    - レスポンスパース失敗や API エラーは警告ログを残して当該チャンクをスキップ（フェイルセーフ）
    - スコアは ±1.0 にクリップ
    - DuckDB への書き込みは冪等性を意識（DELETE → INSERT、executemany を使用して部分失敗の影響を抑制）
  - テストしやすい設計:
    - _call_openai_api を unittest.mock.patch で差し替え可能

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して
    market_regime テーブルへ日次判定（bull/neutral/bear）を書き込む
  - 特徴:
    - prices_daily と raw_news を参照
    - calc_news_window を利用してニュースウィンドウを取得
    - OpenAI の gpt-4o-mini を JSON mode で呼び出し macro_sentiment を取得
    - API エラーやパース失敗時は macro_sentiment を 0.0 にフォールバック（例外を上げず継続）
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT、エラー時は ROLLBACK）
    - Look-ahead バイアス防止（date < target_date 等の排他条件・datetime.today() を直接参照しない）
  - OpenAI 呼び出しは news_nlp と意図的に別実装（モジュール結合を避ける）

- データ関連 (kabusys.data)
  - ETL パイプラインの結果クラス ETLResult を pipeline モジュールで定義し、data.etl から再エクスポート
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新（calendar_update_job）を実装
    - market_calendar を優先しつつ、DB 未登録日は曜日ベースでフォールバックする一貫した営業日ロジックを提供
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を実装
    - カレンダー更新は差分取得・バックフィル・健全性チェックを実施
  - pipeline モジュール（ETL の骨格）:
    - 差分更新・保存（jq.save_* の冪等性を前提）・品質チェックの流れを設計
    - ETLResult に品質問題（quality.QualityIssue）やエラーを集約して返却する仕組み

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離
    - Volatility: 20 日 ATR（true range の厳密な扱い）、相対 ATR、平均売買代金、出来高比率
    - Value: PER（EPS が 0/欠損の場合は None）、ROE（raw_financials の最新値）
    - 戻り値は (date, code) を含む dict のリスト
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman ランク相関による IC 計算）
    - rank（同順位は平均ランクなどの実装）
    - factor_summary（count/mean/std/min/max/median を計算）
    - 標準ライブラリのみで実装し、外部依存を排除

Changed
- 一貫した設計原則として「ルックアヘッドバイアスを生まない」実装に統一
  - datetime.today()/date.today() をスコープ内で直接参照しない箇所が多く、target_date ベースで処理

- OpenAI 呼び出し周りは JSON Mode を用いることでレスポンスの厳密な構造を期待し、失敗時のフォールバック／リトライポリシーを明確化

Fixed
- （新規リリースのため特定のバグ修正履歴はなし。初版としての安定動作を目指した実装を多数含む）

Known issues / Notes
- pipeline._get_max_date の末尾に未完成なコード片（return date.fro）が存在します。これは現状のままだと該当関数の一部経路で例外や NameError を引き起こす可能性があり、修正が必要です。
- DuckDB executemany に対する互換性問題を考慮しているが、稀にバインド方式での互換性差分が発生する可能性あり（バージョン依存）。コード内に回避策（個別 DELETE の executemany）を実装済み。
- OpenAI の API モデル/レスポンス仕様や SDK の変更（status_code の有無など）に対する互換性処理を含めているが、将来の SDK 変更に追従が必要。

Security
- 必須シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）は環境変数で供給する設計です。リポジトリにシークレットを含めないよう注意してください。
- .env の自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。CI/テスト環境では無効化を検討してください。

Upgrade / Migration notes
- 初版のため既存データ移行ルールはなし。DuckDB テーブルスキーマ / raw_news, prices_daily, ai_scores, market_regime 等はコード内のクエリに依存するため、スキーマ整合性を保ってください。
- OpenAI API キーが未設定のまま news_nlp.score_news や regime_detector.score_regime を呼ぶと ValueError を投げます。運用時は環境変数 OPENAI_API_KEY を設定してください。

開発者向けメモ
- テストを容易にするため、kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替え可能です。
- ロギングを多用しており、info/debug/warning レベルで状態が追跡できます。LOG_LEVEL は Settings.log_level で制御。
- データ取得や書き込みは冪等性・フォールバック・部分失敗の保護を重視して実装されています。

著者
- この CHANGELOG はソースコードの内容から推測してまとめた初期リリースノートです。実際のリリース作業・追加のバグ修正・ドキュメント追記は別途実施してください。