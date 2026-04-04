# Changelog

All notable changes to this project will be documented in this file.

このファイルは Keep a Changelog の形式に準拠して作成しています。  
初期リリース相当の内容を、ソースコードから推測して記載しています。

---

## [0.1.0] - 2026-04-04

### Added
- パッケージの初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定値を自動ロードする機能を実装（優先順位: OS 環境 > .env.local > .env）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env のパーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理に対応）。
  - OS 環境変数を保護する protected パラメータを実装し、.env ロード時に既存値を上書きしない仕組みを提供。
  - Settings クラスを追加し、アプリケーション設定をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / LINE API / データベースパス（DuckDB/SQLite）/監視閾値/ログレベル/環境種別などを取得。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
  - 必須環境変数の取得時に未設定なら ValueError を投げる _require() を実装。

- AI 関連（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して扱う calc_news_window）を実装。
    - バッチ処理（最大 20 銘柄／チャンク）、記事数・文字数トリム、JSON 応答のバリデーション、スコアクリップなどを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（_call_openai_api を patch してモック可能）。
    - DuckDB の executemany の互換性考慮（空リストでの executemany 回避）を実装。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次の market_regime を決定・保存する機能を実装。
    - マクロ記事はニュースタイトルでフィルタ（マクロキーワードリスト）し、OpenAI で JSON レスポンスを期待してセンチメントを算出。
    - API エラーに対するリトライ、API 失敗時は macro_sentiment=0.0 のフェイルセーフ、レスポンスパース失敗のフォールバックを実装。
    - DB 書き込みは冪等操作（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を行い、例外時は ROLLBACK を実行して整合性を保つ。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX マーケットカレンダー管理ロジックを実装（market_calendar テーブルの参照・更新）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を追加。
    - calendar_update_job を実装し、J-Quants からの差分取得・バックフィル・健全性チェック（未来日チェック）・保存をサポート。
    - DB 登録が不十分な場合の曜日ベースのフォールバック（週末判定）を用意し、DB 値優先の一貫した挙動を確保。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）を導入して無限ループを防止。

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装して ETL の実行結果（取得数・保存数・品質問題・エラー）を保持。
    - 差分取得・保存（jquants_client 経由）・品質チェック（quality モジュール）に関する処理方針を実装（コードとしての骨格）。
    - デフォルトのバックフィル・最小データ日付などの定義を追加。
    - kabusys.data.etl で ETLResult を再エクスポート。

  - jquants_client / quality クライアント利用を想定した設計（実装は外部モジュールへ委譲）。

- リサーチ（kabusys.research）
  - factor_research モジュールを追加:
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER・ROE）を DuckDB 上で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、ログ出力を実装。
  - feature_exploration モジュールを追加:
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）を実装。
    - IC（情報係数）計算（Spearman の ρ）を実装（calc_ic）。
    - 値のランク化ユーティリティ（rank）とファクター基本統計量（factor_summary）を実装。
  - 研究用ユーティリティ（zscore_normalize）は kabusys.data.stats から再利用して公開。

- パッケージ初期化
  - __init__.py で __version__ = "0.1.0" を設定。
  - パッケージの公開 API（__all__）に data, strategy, execution, monitoring を含めたパッケージ構成の骨格を用意。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- 環境変数の取り扱いに注意する旨を明記。API キー等（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は Settings 経由で取得し、未設定時は明示的に例外を投げる設計。

### Notes / Migration
- OpenAI API を用いる機能（news_nlp, regime_detector）は実行時に OPENAI_API_KEY（または各関数の api_key 引数）を必ず設定する必要がある。未設定の場合は ValueError が発生する。
- DuckDB に対する executemany の動作はバージョン差異があるため、空リストの executemany を避ける実装（チェック）を行っている。古い / 将来の DuckDB バージョンでの互換性に留意のこと。
- 日付処理はルックアヘッドバイアス防止を目的として datetime.today()/date.today() を直接参照しない実装方針を採用（関数呼び出し側で target_date を与える設計）。
- テスト用フック: OpenAI 呼び出し部分はモジュール内部の _call_openai_api を patch して差し替え可能。ユニットテストで API をモックしやすい設計。

---

今後のリリースで望まれる追加項目（提案）
- strategy / execution / monitoring の具体実装（現在はパッケージ API に名前のみ存在）。
- jquants_client / quality の統合実装例および ETL の稼働パスのドキュメント化。
- CI 向けのテスト・モック例（OpenAI, DuckDB など）とサンプル DB 初期化スクリプト。
- パフォーマンスチューニング（大規模データセットでの DuckDB クエリ最適化）と詳細なログレベル運用ガイド。

---

（この CHANGELOG はソースコードの内容に基づいて推測して作成しています。実際のリリースノートとして公開する場合は、実際のコミット履歴やリリース日、著者情報などを追記してください。）