CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[Unreleased]
------------

追加 / 改良
- 自動環境変数ロード機能を導入（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込む。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - export KEY=val 形式やクォート・コメント処理を考慮したパーサ実装を追加。
  - .env.local は .env 上書き（優先）で読み込む。OS 環境変数は保護。
- 設定管理クラス Settings を追加（kabusys.config）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須 / 任意設定をプロパティで取得。
  - デフォルト値・パス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等）、監視閾値（CPU/MEM/ディスク）やログレベル・環境（development/paper_trading/live）のバリデーションを提供。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。
  - OpenAI（gpt-4o-mini）の JSON Mode を利用し、バッチ処理（最大20銘柄/回）でスコアを取得。
  - タイムウィンドウ（前日15:00 JST〜当日08:30 JST）計算ユーティリティ calc_news_window を提供。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ、レスポンス検証、スコアクリップ（±1.0）を実装。API失敗時はフェイルセーフでスキップ。
  - テスト容易性のため API 呼び出し箇所を差し替え可能（_call_openai_api をモック可能）。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）判定を行う score_regime を追加。
  - duckdb を用いて prices_daily / raw_news / market_regime を参照・更新。冪等性を考慮した DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - OpenAI 呼び出しに対するリトライ、API失敗時のフォールバック（macro_sentiment=0.0）を実装。
- 研究（research）モジュール（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility を実装（prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns（将来リターン算出）、calc_ic（Spearman ランク相関 / IC）、factor_summary（基本統計）、rank（同順位は平均ランク） を追加。
  - 設計上、外部 API 呼び出しや pandas 等の外部依存を避け、DuckDB + 標準ライブラリで実装。
- データプラットフォーム関連（kabusys.data）
  - マーケットカレンダー管理（calendar_management）を追加
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar がない場合は曜日（平日）ベースのフォールバック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・健全性チェックを実装。
  - ETL パイプラインとユーティリティ（pipeline, etl）
    - ETLResult データクラスを公開（処理結果・品質チェック・エラー集計）。
    - 差分取得、バックフィル、品質チェックの設計に対応するインターフェースを用意。
  - jquants_client 経由の取得/保存を想定した idempotent な保存・品質検査フロー設計。
- パッケージ初期化
  - パッケージの __version__=0.1.0／公開モジュール __all__ を設定（data, strategy, execution, monitoring 等をエクスポート想定）。

修正 / 改善
- DuckDB 向けの互換性考慮
  - executemany の空リスト対策、リスト型バインド回避（DELETE → INSERT を個別実行）等、DuckDB バージョン差分に配慮した実装を採用。
- ルックアヘッドバイアス対策
  - 日付の計算で datetime.today()/date.today() を直接参照しない実装方針を採用（関数呼び出しに target_date を明示的に渡す）。
- ロギングとフェイルセーフ挙動の強化
  - OpenAI のレスポンスパース失敗や API エラー時は WARNING ログを出してフォールバック（0.0 やスキップ）するように統一。
  - ROLLBACK が失敗した場合のログ出力追加。

互換性 / マイグレーション
- 重要な環境変数
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings.property が ValueError を投げる）。
  - OpenAI API キーは関数呼び出しの api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError。
  - KABUSYS_ENV は development / paper_trading / live のいずれか。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか。
- デフォルトの設定値
  - KABU_API_BASE_URL デフォルト: http://localhost:18080/kabusapi
  - DUCKDB_PATH デフォルト: data/kabusys.duckdb
  - SQLITE_PATH デフォルト: data/monitoring.db
  - PID_FILE_PATH / KILL_FLAG_PATH 等の既定値を提供。
- DB スキーマ前提
  - 多数のモジュールが prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等のテーブルを前提とするため、ETL 実行・スキーマ準備が必要。

既知の制約
- OpenAI 呼び出し部分は gpt-4o-mini の JSON Mode 想定。API の仕様変更やモデル差異によりレスポンス検証ロジックの調整が必要になる可能性がある。
- DuckDB のバージョン依存（リストバインドや executemany の挙動）に留意すること。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存しており、その実装が必要。

[0.1.0] - 2026-04-04
--------------------
最初の公開リリース。本リポジトリに含まれる基本機能をまとめて公開。

Added
- 基本パッケージ構成とバージョン (kabusys v0.1.0)。
- 環境変数/設定管理（kabusys.config）。
- ニュース NLP スコアリング（kabusys.ai.news_nlp）。
- 市場レジーム判定（kabusys.ai.regime_detector）。
- 研究用ファクター計算と特徴量探索（kabusys.research.*）。
- データ処理・ETL・マーケットカレンダー管理（kabusys.data.*）。
- ETL 実行結果を表す ETLResult（kabusys.data.pipeline）。
- DuckDB をデータ層に用いる一連のユーティリティと冪等保存ロジック。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

注記
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートは開発履歴・コミットログに基づき調整してください。