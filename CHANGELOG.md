CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

Unreleased
----------

- なし

0.1.0 - 2026-03-27
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基本コンポーネントを実装。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エントリポイント: src/kabusys/__init__.py（data, strategy, execution, monitoring を公開）
- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数読み出し用 Settings クラスを提供（J-Quants, kabuステーション, Slack, DB パス, ログレベル, 実行環境フラグなど）。
  - 必須変数未設定時は明示的な ValueError を送出。KABUSYS_ENV / LOG_LEVEL の検証を実装。
- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュースセンチメント分析（news_nlp.score_news）
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI (gpt-4o-mini) JSON Mode でバッチ評価。
    - バッチサイズ、文字数・記事数の上限、429/ネットワーク/5xx に対する指数バックオフ・リトライ実装。
    - レスポンスの厳密バリデーションとスコアの ±1.0 クリップ。
    - スコア書き込みは冪等（DELETE → INSERT）で、部分失敗時に既存データを保護する設計。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api をモック可能）。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - prices_daily / raw_news を参照し、DuckDB に対して冪等な書き込みを実施（BEGIN/DELETE/INSERT/COMMIT）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ実装。
    - ルックアヘッドバイアス対策として内部で datetime.today()/date.today() を使用せず、クエリは target_date 未満のデータのみ参照。
- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - JPX カレンダーを管理する market_calendar テーブルの読み書き・営業日判定ユーティリティを提供。
    - DB にデータがない場合は曜日ベースのフォールバック（平日を営業日と判定）。
    - next/prev/get_trading_days/is_sq_day 等の一貫した API と最大探索日数制限による安全設計。
    - calendar_update_job: J-Quants から差分取得して冪等保存。バックフィル・健全性チェックを実装。
  - ETL / パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー集約）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装するための基盤を提供。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティ等を実装。
  - jquants_client / quality などのクライアントを想定したインテグレーションポイントを定義（詳細実装は外部モジュール）。
- Research（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）を DuckDB SQL ベースで計算。
    - データ不足時の安全な None 処理、結果は (date, code) をキーとする dict のリストで返却。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、IC（Spearman ρ）計算、ランク関数、ファクター統計サマリーを実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。
- 汎用設計・品質上のポイント
  - DuckDB を一次 DB として利用する設計（DuckDB 型特性に合わせた executemany の空リスト回避等の実装）。
  - OpenAI 呼び出しに対する堅牢なエラーハンドリング（リトライ、ログ、フェイルセーフのスコアフォールバック）。
  - ルックアヘッドバイアス対策：ターゲット日を明示的に受け取り、内部で現在日時を参照しない関数設計。
  - テストしやすさを考慮した差し替え可能な抽象化（_call_openai_api のモック等）。
  - ロギング出力を各種処理に埋め込み（情報/警告/例外ログ）。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- OpenAI API のキーは api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出する。
- 一部 DuckDB バインドや executemany の挙動に依存する箇所があるため、DuckDB バージョン差異に注意。
- 実行環境（live/paper_trading/development）判定は KABUSYS_ENV に依存。安全な取り扱いを推奨。

Authors
- KabuSys 開発チーム

---