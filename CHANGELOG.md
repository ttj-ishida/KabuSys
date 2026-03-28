Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット
- 重大な変更はリリース単位で記載します。
- 各リリースはカテゴリ（Added, Changed, Fixed, Removed, Deprecated, Security）で整理します。

Unreleased
---------

（未リリースの変更はここに記載）

[0.1.0] - 2026-03-28
-------------------

Added
- 基本パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報（src/kabusys/__init__.py）を追加。公開 API: data, strategy, execution, monitoring。
- 環境設定・自動.env読み込み（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルートから自動読み込み（.git または pyproject.toml を基準にプロジェクトルートを特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントに対応した .env パーサを実装。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や各種デフォルト（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）、env / log_level の検証ロジックを実装。
- ニュースNLP スコアリング（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols テーブルから記事を集約し、OpenAI (gpt-4o-mini) を用いたバッチセンチメントスコアリングを実装。
  - チャンク処理（最大20銘柄/コール）、記事数と文字数のトリム、JSON Mode を利用した厳格なレスポンス検証をサポート。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ、失敗時はフェイルセーフでスキップ（例外を上位へ伝えず継続）。
  - レスポンスバリデーション（results 配列・code/score の型チェック・スコアの有限性確認）を実装し、スコアは ±1.0 にクリップして ai_scores テーブルへ冪等（DELETE → INSERT）で保存。
  - テスト容易化のため _call_openai_api をパッチ差し替え可能に実装。
  - 公開 API: score_news(conn, target_date, api_key=None) を提供。
- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来の LLM マクロセンチメント（重み30%）を合成して、日次で 'bull' / 'neutral' / 'bear' を判定・保存する処理を実装。
  - prices_daily / raw_news / market_regime を参照し、計算結果を market_regime テーブルへ冪等に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - OpenAI 呼び出しは独立実装とし、API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。リトライ・バックオフを実装。
  - Look-ahead バイアス対策として、内部で datetime.today() / date.today() を参照せず、target_date 未満のデータのみ使用。
  - 公開 API: score_regime(conn, target_date, api_key=None) を提供。
- 研究用ファクター/探索モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等を DuckDB の prices_daily / raw_financials から計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足ハンドリング（必要行数未満で None を返す等）とログ出力を実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）算出（スピアマンのランク相関）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を追加。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - 研究 API の再エクスポート（src/kabusys/research/__init__.py）で主要関数を公開。
- データ管理（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）および is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを実装。
    - market_calendar 未取得時の曜日ベースフォールバックや最大探索日数の制限、バックフィル・健全性チェックを実装。
    - J-Quants クライアントを介した差分取得 / 保存の仕組みを想定（jquants_client を利用）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得、保存（idempotent）、品質チェック（quality モジュールと連携）を行う ETLResult データクラスとユーティリティを実装。
    - ETLResult は品質問題やエラーの集約、辞書化(to_dict) をサポート。
    - 内部でのテーブル存在確認・最大日付取得ユーティリティを提供。
  - ETLResult の再エクスポート（src/kabusys/data/etl.py）。
  - jquants_client / quality 等の外部モジュールとの連携ポイントを設計（実装は別モジュール想定）。
- package の細かな公開設定
  - ai と research パッケージで public API を __all__ により明示的にエクスポート（例: ai.score_news, ai.score_news のエクスポート、research の主要関数群のエクスポート）。

Changed
- 仕様設計上のポリシーをコード中に文書化（各モジュールで設計方針・フェイルセーフ・ルックアヘッドバイアス対策・DuckDB 互換性考慮などをコメントで明示）。

Fixed
- （初回リリースのため特定の「修正」はなし。実装時に想定されるエラー処理とログ出力を多めに盛り込んでいるため、運用での微修正に対応しやすい設計とした。）

Security
- 環境変数の読み込みで OS 環境変数を保護する仕組み（protected set）を実装し、.env による既存環境の上書きを制御可能にした。
- OpenAI API キーは明示的に引数で注入可能（api_key）かつ環境変数 OPENAI_API_KEY を利用する設計。未設定時は ValueError を送出して安全性を確保。

Notes / Implementation details
- DuckDB を主要なローカル DB と想定。各種処理は DuckDB の SQL ウィンドウ関数を多用して効率的に実装。
- OpenAI 呼び出し部はテスト容易性のため差し替え可能に実装（ユニットテストでのモック注入を想定）。
- 全モジュールで look-ahead バイアスを避ける設計（target_date を明示的に渡し、内部で現在時刻を参照しない）。
- DB 書き込みは可能な限り冪等に行い（DELETE→INSERT、ON CONFLICT を想定）、トランザクション（BEGIN/COMMIT/ROLLBACK）を使用して整合性を保つ。

Acknowledgements
- 本リリースはシステム設計文書（StrategyModel.md、DataPlatform.md 等）に基づく実装を意図しています。外部 API クライアント（J-Quants, OpenAI 等）は別モジュールで提供される想定です。