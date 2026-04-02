# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

現在のバージョン: 0.1.0

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティを含む基本機能を提供。

### Added
- パッケージの初期構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - エクスポート済みモジュール: data, strategy, execution, monitoring

- 設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - .env/.env.local の読み込み順序・上書きルール（OS 環境変数保護）に対応。
  - export KEY=val 形式やクォート・エスケープ、インラインコメントの取り扱いを考慮したパーサを実装。
  - 環境変数必須チェック（_require）と Settings クラスを提供：
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等の必須項目。
    - KABU_API_BASE_URL やデフォルト DB パス（DUCKDB_PATH / SQLITE_PATH）、監視用しきい値（CPU/MEM/DI S K）などの設定をプロパティで取得。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols から指定ウィンドウのニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄当たりの記事数・文字数のトリム、JSON Mode 応答のバリデーションを実装。
    - 再試行（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、失敗時のフェイルセーフ（スキップ）を実装。
    - DuckDB への置換書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）に対応。
    - calc_news_window ユーティリティ（JST 基準ウィンドウの UTC 変換）を実装。
  - regime_detector モジュール
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しのリトライ・フォールバック（API 失敗時に macro_sentiment=0.0）を実装。
    - LLM 呼び出しは専用の内部実装で分離（news_nlp とプライベート関数を共有しない設計）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未存在・未登録の場合は曜日ベース（土日除外）でフォールバック。
    - カレンダーの夜間バッチ更新 job (calendar_update_job)：J-Quants から差分取得・バックフィル・健全性チェックを実装。
  - pipeline / ETLResult
    - ETLResult データクラスと ETL パイプラインの基本方針を実装（差分取得、保存、品質チェックの流れ）。
    - jquants_client 経由での取得・保存を想定し、品質チェック（quality モジュール）とエラー集約をサポート。
    - DuckDB のテーブル存在チェックや最大日付取得などのユーティリティを実装（ETL の一部）。
  - etl モジュールで ETLResult を再エクスポート。

- 研究用ユーティリティ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を計算する関数群を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの計算でデータ不足時に None を返す挙動を明示。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）なしで標準ライブラリのみで実装。

- 共通設計方針（コード全体）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない（対象日を引数で受け取る設計）。
  - DuckDB を主要なオンディスク DB として利用。書き込みは冪等性を重視（DELETE→INSERT/ON CONFLICT ロジック想定）。
  - OpenAI API 呼び出しは JSON モードを利用し、厳格なレスポンス検証とパース回復ロジックを実装。
  - API の一時エラーに対する指数バックオフリトライを多数の箇所で実装。
  - ロギングを多用し、警告・情報ログでフォールト状況を可視化。

### Changed
- 初期リリースのため、既存の外部仕様の確定と初期 API を導入（将来的な拡張を前提とした分離設計）。

### Fixed
- 初期リリース（該当なし）

### Removed
- 初期リリース（該当なし）

---

注記:
- OpenAI API キー関連の関数は api_key 引数によりテスト時の注入が可能。環境変数 OPENAI_API_KEY を使う際は Settings 経由や直接 os.environ を参照する実装が混在している箇所があるため、運用時は環境変数の整備を推奨します。
- DuckDB バージョン依存（executemany に空リストを渡せない等）への互換性配慮が多所に実装されています。運用環境の DuckDB バージョンに注意してください。