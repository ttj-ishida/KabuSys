CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初回リリース（v0.1.0）はパッケージの主要機能を実装したものです。

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 — 2026-03-31
-----------------

Added
- 基本パッケージ初期実装
  - パッケージ名: kabusys、バージョン: 0.1.0
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml）
  - 読み込みの優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）
  - .env パーサは export 構文、クォートとエスケープ、インラインコメント処理に対応
  - Settings クラスを提供し、主要設定をプロパティ経由で取得
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境モード検証: KABUSYS_ENV 値は development / paper_trading / live のみ許可
    - ログレベル検証: LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可
    - ヘルパープロパティ: is_live / is_paper / is_dev

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄別センチメントを計算し ai_scores テーブルへ保存する処理を実装
  - OpenAI gpt-4o-mini を JSON Mode で呼ぶバッチ処理を実装（バッチサイズ: 20）
  - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）と calc_news_window を提供
  - 1銘柄あたり記事数・文字数上限（_MAX_ARTICLES_PER_STOCK=10、_MAX_CHARS_PER_STOCK=3000）
  - レスポンス検証ロジック（JSONパース回復、results リスト/各要素検証、スコアクリップ ±1.0）
  - エラー耐性: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
  - テスト用フック: OpenAI 呼出しを _call_openai_api をパッチすることで差し替え可能

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム判定を実装
  - LLM 呼び出しは gpt-4o-mini（JSON Mode）を利用、API失敗時は macro_sentiment=0.0 にフォールバック
  - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）で market_regime テーブルへ保存
  - ログ出力・リトライ・エラーハンドリングを備える
  - テスト用フック: OpenAI 呼出しを差し替え可能

- データプラットフォーム関連（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧を保持）
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）方針を実装
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間更新ジョブ calendar_update_job を実装（J-Quants クライアント経由で取得・保存）
    - 営業日判定ユーティリティを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DBデータ優先・未登録日の曜日フォールバック、最大探索日数制限を実装
    - 健全性チェック（未来日付の異常検知）、バックフィル日数、先読み日数などの設定を実装

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）
    - calc_volatility: 20日 ATR、ATR比、平均売買代金、出来高比率を計算
    - calc_value: raw_financials から PER / ROE を計算
    - 全関数は DuckDB の prices_daily / raw_financials のみ参照
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト: [1,5,21]）
    - calc_ic: スピアマンのランク相関（IC）を計算し、データ不足時は None を返す
    - factor_summary: 各ファクター列の基本統計量を計算
    - rank: 同順位を平均ランクで扱うランク関数を実装
  - research パッケージから主要関数を再エクスポート

- 共通設計方針・ユーティリティ
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照する箇所は限定的に使用
  - DBへの書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT 方針など）
  - OpenAI 呼び出し周りは明示的なリトライ・バックオフ・パース保護を実装
  - DuckDB の executemany に関する注意点（空リスト不可）を考慮して実装

Changed
- 初版のため該当なし

Fixed
- 初版のため該当なし

Deprecated
- 初版のため該当なし

Removed
- 初版のため該当なし

Security
- .env 読み込み時、既存の OS 環境変数は protected として .env.local / .env による上書きを制御
- 必須トークン未設定時は明示的に ValueError を発生させることで誤操作を防止

Migration / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - OpenAI API を使用する機能を利用する場合は OPENAI_API_KEY を環境変数または各関数の api_key 引数で渡す必要があります
- DuckDB / DB スキーマ:
  - 多くの機能は特定テーブルが存在することを前提とします（例: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials）
  - ETL・カレンダー更新は jquants_client モジュールを使って外部 API からデータ取得・保存を行います。実行前に対応するテーブル定義を用意してください
- OpenAI 関連:
  - gpt-4o-mini を想定したプロンプト・JSON Mode を使用
  - API 呼び出しはネットワークやレート制限に影響されるため、retry/backoff ロジックが入っていますが、API キーや使用制限には注意してください
- 挙動上の既知の方針:
  - ニュースやマクロセンチメントの取得失敗時は「中立」（0.0）にフォールバックして処理を継続します（フェイルセーフ設計）
  - データ不足時のファクター値は None を返す、または ma200_ratio は不足時に中立値 1.0 を返す

テスト支援
- OpenAI 呼出し部の _call_openai_api はモジュール内で分離されており、unittest.mock.patch 等で差し替えてテスト可能です
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

今後の予定（例）
- さらなる品質チェックルールの追加
- strategy / execution / monitoring モジュールの実装詳細拡充（現在はパッケージ構造のみエクスポート）
- モデルプロンプト・出力のより厳密な正当性検証やロギング強化

以上。