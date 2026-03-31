CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog (https://keepachangelog.com/ja/1.0.0/)

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

初回公開リリース。以下の主要機能／実装が含まれます。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。パブリック API として data, research, ai モジュール等を公開。
- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env / .env.local）または OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（カレントワーキングディレクトリに依存しない）。
  - 複数形式の .env 行パースを実装（コメント、export プレフィックス、クォート内エスケープ等に対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB 等の設定をプロパティで取得（必須キーは未設定時に ValueError を送出）。
  - KABUSYS_ENV の検証（development/paper_trading/live）と LOG_LEVEL の検証（DEBUG/INFO/...）を追加。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等に安全なデフォルトを設定。
- データプラットフォーム（data）
  - ETL パイプライン基盤 (kabusys.data.pipeline)
    - 差分取得、バックフィル、品質チェックを想定した ETLResult データクラスを実装。実行結果のサマリ、エラー／品質問題の判定ユーティリティを提供。
    - DuckDB 上の最大日付取得やテーブル存在確認ユーティリティを提供。
  - カレンダー管理 (kabusys.data.calendar_management)
    - JPX マーケットカレンダーを扱うユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar テーブルが無い場合の曜日ベースフォールバック、DB 値優先の一貫した判定ロジックを実装。
    - calendar_update_job により J-Quants から差分取得し冪等的に保存する処理を実装（バックフィル・健全性チェック付き）。
  - ETL 公開インターフェース (kabusys.data.etl)
    - pipeline.ETLResult を再エクスポート。
- 研究（research）
  - factor_research モジュール
    - モメンタム / ボラティリティ / バリュー等のファクター計算関数を提供:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None を返す動作）。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（部分窓の扱い、NULL 管理）。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算。
    - DuckDB のウィンドウ関数を活用した高効率な集計を実装。
  - feature_exploration モジュール
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得（horizons 検証あり）。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を実装（不足データ・定数分散時の None 処理）。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties 対策含む）。
    - factor_summary: count/mean/std/min/max/median の基本統計量算出ユーティリティ。
- AI / NLP（kabusys.ai）
  - news_nlp
    - raw_news + news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出。
    - チャンク処理（デフォルト 20 銘柄）、1 銘柄あたりの最大記事数／文字数トリム (_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK) を実装。
    - OpenAI 呼び出しは JSON mode を用い、レスポンスの厳密バリデーション（results 配列、code/score の妥当性チェック）を行う。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx を対象とした指数バックオフ）、失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（_call_openai_api を patch 可能）。
  - regime_detector
    - ETF 1321（日経225連動型）を用いた 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する実装。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出しのリトライ／フェイルセーフ、スコア合成・クリップ、label 判定を実装。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、例外発生時は ROLLBACK）。
    - LLM 呼び出しは news_nlp 側と独立実装（モジュール結合を避ける設計）。
- ロギング・堅牢性
  - 多数の処理で詳細な logger メッセージを追加（INFO/DEBUG/WARNING/EXCEPTION）。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）を徹底。
  - DuckDB executemany の空リスト問題への対処（空時は実行しない）。
  - JSON パース失敗時の復元処理（文字列の最外側 {} を抽出して再パースするなど）。
  - lookahead / date handling の設計方針: datetime.today()/date.today() を直接参照する箇所を避け、呼び出し側から target_date を与えることでルックアヘッドバイアスを防止。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数注入または OPENAI_API_KEY 環境変数で供給するよう設計。未設定時は ValueError を返して明示的に扱う。

Notes / Implementation details
- 外部サービス:
  - OpenAI（gpt-4o-mini）を JSON Mode で利用する想定。レスポンスの形式やステータスコードに依存するため、API SDKのバージョン差分に配慮した例外処理を実装。
  - J-Quants クライアント（kabusys.data.jquants_client）を利用してカレンダーや時系列データを取得／保存することを前提としている（実装は別モジュール）。
- テスト性:
  - OpenAI 呼び出し箇所はテスト時に差し替え可能（unittest.mock.patch など）。
  - 環境変数の自動ロードはテストで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- 互換性:
  - DuckDB のバージョン差（executemany の空リストバインドなど）に配慮した実装を行っている。

参考
- 主要設計方針ドキュメントへの言及は各モジュールの docstring に含まれています（DataPlatform.md / StrategyModel.md 等を想定）。

シンボル
- 主要公開 API: kabusys.data.ETLResult（kabusys.data.etl で再公開）、kabusys.ai.score_news / score_regime、kabusys.research の factor 関数群など。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0