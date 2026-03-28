# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」準拠です。  

最新リリース
=============

Unreleased
----------

（なし）

[0.1.0] - 2026-03-28
-------------------

初回公開リリース。以下の主要機能・モジュールを実装・公開しました。

Added
- パッケージ基本情報
  - kabusys パッケージ初版（__version__ = 0.1.0）。
  - パブリックAPI: kabusys.data, kabusys.research, kabusys.ai, kabusys.execution, kabusys.monitoring を __all__ で公開。

- 環境設定
  - 環境変数 / .env 読み込みユーティリティを実装（kabusys.config）。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き可能）。
    - export KEY=val, クォート／エスケープ、インラインコメント等に対応したパーサー実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
    - Settings クラスを提供し、必須値取得（_require）・既定値・検証（env 値・LOG_LEVEL）を行う。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）や API ベース URL 等の設定プロパティを用意。

- AI モジュール
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）に対して銘柄ごとのセンチメントスコアをバッチ取得。
    - チャンクサイズ、文字数／記事数上限、JSON mode 利用、リトライ（429/ネットワーク/5xx）と指数バックオフを実装。
    - レスポンス検証ロジック（JSON 復元、results 検証、コード一致、数値検証、±1.0 クリップ）。
    - ai_scores テーブルへの冗長性を考慮した置換処理（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - 公開関数: score_news(conn, target_date, api_key=None)、calc_news_window(target_date)。
    - フェイルセーフ設計: API失敗時は処理をスキップして継続（例外を投げず 0 件を返す等）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）200日移動平均乖離（重み70%）と、ニュース由来の LLM マクロセンチメント（重み30%）を合成して日次レジーム判定（bull/neutral/bear）を行う。
    - DuckDB の prices_daily / raw_news / market_regime を使用し、計算はルックアヘッドバイアスを防ぐため target_date 未満のデータのみ参照。
    - OpenAI 呼び出しを独立実装（news_nlp と内部実装を共有しない設計）。
    - API 呼び出しはリトライ実装（429/ネットワーク/5xx 対応）、最終的に失敗した場合は macro_sentiment=0.0 として継続。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

- データモジュール
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー管理、営業日判定・前後営業日取得・期間内営業日列挙・SQ判定等を提供。
    - market_calendar の有無に応じたフォールバック（DB データ優先、未登録日は曜日ベースの判定）。
    - next_trading_day / prev_trading_day / get_trading_days は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループ防止。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得・冪等保存を行う（バックフィルと健全性チェック実装）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存（jquants_client を利用）、品質チェック（kabusys.data.quality 想定）の統合フロー設計。
    - ETLResult データクラスを実装（kabusys.data.etl で再エクスポート）。
    - DB テーブル存在チェック、最大日付取得、トレードデイ調整などユーティリティを実装。

- Research / 分析モジュール（kabusys.research）
  - Factor 計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER/ROE）を実装。
    - DuckDB の prices_daily / raw_financials のみ参照し、返り値は (date, code) を含む dict のリスト形式。
    - 不足データは None を返す等、堅牢な欠損取り扱い。
    - 公開関数: calc_momentum, calc_volatility, calc_value。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン算出（calc_forward_returns; 可変ホライズン対応）、IC（Spearman ρ）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部依存を持たない純粋な実装（標準ライブラリ + duckdb）。
    - 公開関数: calc_forward_returns, calc_ic, rank, factor_summary。

Changed
- 設計上の重要事項（ドキュメント化）
  - LLM 関連モジュール（news_nlp, regime_detector）はルックアヘッドバイアス防止のため datetime.today()/date.today() を内部で参照しない設計であることを明示。
  - OpenAI 呼び出し時のリトライ方針・フェイルセーフ挙動を明文化（API障害時はスコアを 0.0 またはスキップして処理継続）。

Fixed
- （初版のため履歴なし）

Security
- OpenAI API キーの扱い
  - score_news / score_regime は api_key 引数を受け取り、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて安全に失敗する仕様。

Notes / 実装上の注意
- DuckDB 互換性
  - 一部 executemany の空リストバインドが動作しない DuckDB バージョンを考慮し、空チェックを明示的に行ってから executemany を呼ぶ実装を採用。
- ロギング
  - 主要処理（ETL、news scoring、regime scoring、calendar update 等）は詳細な info/debug/warning ログを出力。
- テスト容易性
  - OpenAI 呼び出しラッパー（_call_openai_api 等）はモジュール内で分離実装されており、unittest.mock.patch による差し替えが可能。

今後の予定（例）
- モデルのハイパーパラメータや重みのチューニング（MA/MACRO 重み等）。
- jquants_client の実装と統合テスト、監視/通知（Slack 等）連携の追加。
- 性能最適化（大規模銘柄数時のクエリ／バッチ制御）。

---

この CHANGELOG はコードベースの実装内容から推定して作成しています。実際のリリースノートに反映する際はリリース日・バージョン・変更の確定内容を適宜調整してください。