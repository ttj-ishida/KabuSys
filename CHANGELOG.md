変更履歴（Keep a Changelog 準拠）
=================================

このファイルはリポジトリ内のコード構成および実装から推測して作成した変更履歴です。実際のリリース履歴と異なる場合があります。日付は本ファイル作成日時（2026-04-04）を使用しています。

フォーマットについて
--------------------
- Keep a Changelog: https://keepachangelog.com/ja/1.0.0/
- セクション: Unreleased / バージョンごとに Added / Changed / Fixed / Deprecated / Removed / Security / Breaking Changes を記載

Unreleased
----------
- （現時点の開発中の変更点があればここに追記してください）

[0.1.0] - 2026-04-04
--------------------

Added
- 基本パッケージ公開情報
  - kabusys パッケージのバージョン定義（__version__ = "0.1.0"）と公開モジュールの __all__ を追加。
- 環境設定・管理
  - kabusys.config.Settings クラスを追加。J-Quants / kabuステーション / LINE / DB /監視 /システム設定等の環境変数をプロパティ経由で取得。
  - .env 自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。.env → .env.local の優先度制御、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
  - .env パース機能の実装（export プレフィックス対応、クォート／エスケープ、行内コメント処理）。
- AI（自然言語処理）機能
  - kabusys.ai.news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）に送り、銘柄別センチメントを ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、1銘柄あたりの記事数・文字数上限、JSON Mode 応答検証、スコアの ±1.0 クリップ、リトライ（429/ネットワーク/5xx）・指数バックオフ、部分書き換え（DELETE→INSERT）による冪等性対策。
    - calc_news_window ユーティリティ（JST 時刻ウィンドウ → UTC naive datetime）を追加。
  - kabusys.ai.regime_detector: ETF（1321）200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を追加。
    - マクロニュース抽出（キーワードフィルタ）、OpenAI 呼び出し（JSON モード）、堅牢なリトライ戦略、API 失敗時は macro_sentiment=0.0 とするフェイルセーフ。
  - AI モジュール設計方針: ルックアヘッドバイアス防止のため datetime.today() を直接参照しない実装、モジュール間でプライベート関数を共有しない（テスト容易性・疎結合を考慮）。
- データプラットフォーム（Data）
  - kabusys.data.pipeline / etl: ETLResult データクラスを含む ETL パイプライン基盤の公開インターフェースを追加。差分取得・保存・品質チェックを想定した設計（backfill, calendar lookahead 等）。
  - kabusys.data.calendar_management: 市場カレンダー管理（market_calendar）と営業日判定ユーティリティを追加。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day / calendar_update_job を実装。
    - DB データが無い場合は曜日ベースでのフォールバック、DB 登録値優先の一貫した判定ロジック、バックフィル／健全性チェックを備えた夜間更新ジョブ。
- リサーチ（Research）
  - kabusys.research.factor_research: モメンタム／ボラティリティ／バリュー（PER, ROE）等のファクター計算関数を追加（calc_momentum, calc_volatility, calc_value）。DuckDB を用いた SQL+Python 実装、データ不足時の None ハンドリング。
  - kabusys.research.feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を追加。標準ライブラリのみで実装。
- DuckDB 向けの互換性・運用配慮
  - executemany に空リストを渡さないガード（DuckDB 0.10 互換）、DATE 値の変換ユーティリティ、テーブル存在チェックユーティリティ等を追加。
- ロギング・フェイルセーフ
  - 多数の箇所でログ出力（info/warning/debug/exception）を適切に実装し、外部 API 障害時も例外を全体に波及させない設計（部分的に処理をスキップして継続）。

Fixed
- （初回リリースのため特定のバグ修正履歴は無し。実装には多数のフェイルセーフ／入力検証が組み込まれていることを明記）

Breaking Changes
- なし（初版リリース）

Deprecated
- なし

Removed
- なし

Security
- 環境変数や API キーの扱いに関する注意:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を期待。未設定時は ValueError を送出する箇所あり。
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

注意（運用／マイグレーション）
- 必要な DB テーブル（暗黙の依存）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等が想定されるスキーマとして参照されています。ETL や解析を動かす前にスキーマを準備してください。
- 必須環境変数（一部抜粋）
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）、OPENAI_API_KEY（AI 機能使用時）、その他 LOG_LEVEL, KABUSYS_ENV 等。
- デフォルトパス
  - DUCKDB_PATH: data/kabusys.duckdb（expanduser による展開）
  - SQLITE_PATH: data/monitoring.db
  - PID / KILL フラグファイルのデフォルトパスが設定済み
- デザイン上の重要点
  - 各 AI 関連機能はルックアヘッドバイアスを避けるため日付参照を外部引数（target_date）で受け取り、内部で date.today()/datetime.today() を参照しない実装。
  - OpenAI 呼び出しは JSON 出力を期待し、パースや検証に冗長な安全策を実装。
  - DB 書き込みは冪等性を意識した DELETE→INSERT または ON CONFLICT（jquants_client 側）想定のやり方を採用。

補足
- 本 CHANGELOG はコードの実装内容から推測してまとめたものであり、実際の開発履歴やコミットログに基づいたものではありません。将来のリリースでは Unreleased セクションに機能追加・修正を記載してください。