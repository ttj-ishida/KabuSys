CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-29
--------------------

初回リリース。日本株の自動売買 / データプラットフォームを構成する主要機能を実装しました。

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）。
  - 公開モジュール群: data, research, ai, monitoring, strategy, execution（__all__ によるエクスポートの準備）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env および .env.local の自動ロード（プロジェクトルート判定: .git または pyproject.toml）。
  - OS 環境変数を保護する protected 機能、.env.local が .env を上書きする優先度ルール。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 強制取得ヘルパー _require と Settings クラスを提供。主要な環境変数プロパティを定義:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV の検証（development/paper_trading/live）
    - LOG_LEVEL の検証（DEBUG/INFO/...）
  - 環境変数パースはシェルスタイル（export KEY=val）やクォート・エスケープ、インラインコメント等に対応。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - news_nlp
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini）の JSON モードでセンチメントを計算。
    - 時間ウィンドウ定義（JST 前日 15:00 〜 当日 08:30 相当、UTC に変換して DB と比較）。
    - バッチ処理（最大 20 銘柄/chunk）・記事トリム（最大記事数、最大文字数）・レスポンスバリデーションを実装。
    - リトライ（429・接続断・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスパースの堅牢化（余計な前後テキストから最外側の {} を抽出するなど）。
    - テスト容易性のため _call_openai_api をパッチで差し替え可能。
  - regime_detector
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる記事抽出、OpenAI 呼び出し、スコアクリップ、閾値によるラベリング、DuckDB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI 呼び出しのリトライ・フェイルセーフ（API 失敗やパース失敗時は macro_sentiment=0.0）を備える。
    - news_nlp と内部実装を分離しモジュール結合を避ける設計。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン
    - pipeline.ETLResult の公開（etl.py 経由）。
    - ETLResult により ETL の取得数・保存数・品質問題・エラー集約を提供。
    - 差分更新、バックフィル、品質チェック（quality モジュールと連携する想定）、id_token 注入など設計に考慮。
  - カレンダー管理（calendar_management.py）
    - market_calendar を用いた営業日判定・前後営業日取得・期間の営業日列挙・SQ判定機能を実装。
    - DB が不完全な場合の曜日ベースフォールバック（週末休日扱い）、最大探索範囲制限、バックフィル・先読み・健全性チェックなどを提供。
    - calendar_update_job により J-Quants から差分取得して冪等保存するワークフローを実装（バックフィルと健全性チェック含む）。
  - 各種内部ユーティリティ（テーブル存在確認、日付変換、最大日付取得等）を実装し DuckDB を前提にした堅牢な操作を提供。

- Research モジュール（src/kabusys/research）
  - factor_research: momentum / value / volatility / liquidity に関するファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200 の乖離率（データ不足時は None 扱い）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - calc_value: PER（EPS が無効なら None）、ROE（raw_financials から最新財務データを取得）。
    - DuckDB 内の SQL ウィンドウ関数を利用しパフォーマンスを考慮した実装。
  - feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を提供。
    - calc_forward_returns: 複数ホライゾンを1クエリで計算。horizons の検証を実装。
    - calc_ic: None やデータ不足の扱い、最小有効レコード数チェックを実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数ロード時に OS 環境を保護（既存の OS 環境変数を上書きしないデフォルト挙動）。.env.local は明示的に上書きする設計。
- OpenAI / 外部 API キーは Settings 経由で必須チェックを行い、未設定時は明確な例外を投げる（入力ミスの早期検出）。

Design / Reliability notes（実装上の重要設計判断）
- ルックアヘッドバイアス防止: 各種処理（news window, score_regime, score_news, factor 計算など）は内部で datetime.today()/date.today() を参照せず、外部から target_date を与える設計。
- API 呼び出し: 429・ネットワーク断・タイムアウト・5xx に対する再試行（指数バックオフ）を実装。非再試行対象エラーはスキップして処理継続（フェイルセーフ）。
- DB 書き込み: 冪等性を意識（DELETE → INSERT、ON CONFLICT を期待）しトランザクション / ROLLBACK ハンドリングを備える。
- スコアのクリップ・バリデーション: LLM からのスコアは ±1.0 にクリップ、レスポンスバリデーションを厳密に行う。
- テストしやすさ: OpenAI 呼び出しポイント（_call_openai_api）をパッチ可能にして単体テストでの差し替えを容易化。

Environment / Requirements
- 実行に必要な代表的環境変数（Settings で必須とされているもの）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI 関連機能実行時）
- DuckDB をデータストアとして利用（デフォルトパス: data/kabusys.duckdb）。
- OpenAI モデル: gpt-4o-mini（JSON Mode）を想定したプロンプト / パース実装。

Notes
- 本リリースは初版機能の集合体であり、実運用前に環境変数・DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）準備とエンドツーエンド検証が必要です。
- 今後の予定: 監視・実行（発注）モジュールの詳細実装、品質チェックの強化、より詳細なテストカバレッジとドキュメント化。

未記載の変更やバグについて問題が発生した場合は issue を作成してください。