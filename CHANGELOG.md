# CHANGELOG

すべての重要な変更を記録します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

注: バージョンはパッケージの __version__（src/kabusys/__init__.py）を参照しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

初回リリース。日本株向け自動売買 / データ基盤 / 研究用ユーティリティ群をまとめて提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージメタ情報（src/kabusys/__init__.py に __version__ = "0.1.0" を設定）。
  - public サブパッケージ公開: data, strategy, execution, monitoring を __all__ にてエクスポート。

- 設定・環境管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パースの柔軟対応（コメント、export プレフィックス、クォート・エスケープ処理、インラインコメント処理）。
  - Settings クラスによる環境変数アクセスラッパ（J-Quants / kabu / Slack / DB パス等のプロパティを定義）。
  - 環境値バリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- AI（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（記事数・文字数制限）。
    - JSON Mode 応答の検証、パース後のスコアクリッピング（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ再試行。
    - テスト容易性のため OpenAI 呼び出し箇所に差し替えポイントを用意（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して market_regime テーブルに書き込み。
    - マクロニュース抽出（キーワードリスト）、OpenAI（gpt-4o-mini）呼び出し、再試行ロジック、API失敗時のフェイルセーフ（macro_sentiment = 0.0）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
    - テスト用に OpenAI 呼び出し差し替え可能（_call_openai_api）。
    - ルックアヘッドバイアス防止設計。

- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定、次/前営業日の探索、期間内営業日リスト取得、SQ日判定、JPX カレンダー差分取得バッチ（calendar_update_job）。
    - DB 未取得時の曜日ベースのフォールバック、最大探索範囲の制限、バックフィルや健全性チェックの実装。
  - ETL / パイプライン基盤（src/kabusys/data/pipeline.py, etl.py）
    - ETLResult dataclass による実行結果表現（取得数、保存数、品質チェック結果、エラー一覧）。
    - 差分更新・バックフィル・品質チェックの設計方針に準拠するユーティリティ群。
    - _get_max_date 等のヘルパーで DuckDB テーブル存在・最終日を取得。

- 研究（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Value（PER、ROE）、Volatility（20日 ATR、相対 ATR、流動性指標）を DuckDB の prices_daily / raw_financials を用いて計算。
    - データ不足時の None ハンドリング、ログ出力。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルトは [1,5,21]）、IC（Spearman ランク相関）計算、統計サマリ（count/mean/std/min/max/median）、ランク関数（同順位は平均ランク）。
    - pandas 等の外部依存無しで純粋 Python + DuckDB にて実装。

- 共通・設計上の配慮
  - DuckDB を主要な分析 DB として採用（多くの関数が DuckDB 接続を受け取るインターフェース）。
  - API 呼び出し失敗時はシステム全体を停止させないフェイルセーフ（多くの箇所でデフォルト値やスキップ動作を採用）。
  - 冪等な DB 書き込み（DELETE→INSERT、ON CONFLICT 想定）を基本設計。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api の patch 等）を複数箇所に用意。
  - ルックアヘッドバイアスの排除を設計方針として明示（date.today() の直接参照回避、クエリで date < target_date 等の排他条件）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- OpenAI API キー等の機密情報は環境変数から取得する方式を採用。必須環境変数が未設定の場合は ValueError を送出する箇所が明示されている（score_news / score_regime / Settings の各 required プロパティなど）。

---

利用上の注意 / マイグレーションメモ（初回導入時）
- OpenAI 連携機能を利用するには OPENAI_API_KEY 環境変数（または関数引数での注入）を設定してください。未設定時は ValueError が発生します。
- デフォルトの DuckDB / SQLite パスは Settings で定義されています（DUCKDB_PATH= data/kabusys.duckdb 等）。運用環境では適宜設定してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を探索します。CI やテストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はテストのために差し替え可能です（モジュール内の _call_openai_api を patch）。ユニットテストの際はこれを利用して外部依存を除去してください。
- ETL / カレンダー更新ジョブ等は DuckDB のスキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials など）を前提としています。初回導入時はスキーマ整備が必要です。

（以上）