Keep a Changelog に準拠した CHANGELOG.md（日本語）

すべての重要な変更をこのファイルに記載します。フォーマットは Keep a Changelog に従っています。
リリースは semver に基づき管理します。

注意: 以下はコードベースの内容から推測して作成した変更履歴です（コミット履歴がないため初回公開相当のまとめとして記載しています）。

Unreleased
---------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------
Added
- パッケージ基盤
  - 初期パッケージ kabusys を追加。バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パッケージ公開用 __all__ を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートの検出ロジックは __file__ を基点に .git または pyproject.toml を探索するため CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理など）。
  - 環境変数上書き制御（override と protected キーセット）を実装。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定などのプロパティを備える。
    - 必須項目チェック（_require）と enum 的なバリデーション（KABUSYS_ENV, LOG_LEVEL）を実施。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）を定義。

- データプラットフォーム（kabusys.data）
  - カレンダー管理モジュール（calendar_management）
    - JPX カレンダー操作ロジックを実装（market_calendar テーブル参照）。
    - 営業日判定・前後営業日取得・期間内営業日列挙・SQ判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがまばらな場合は曜日ベースでフォールバック。最大探索日数に上限を設け無限ループを防止。
    - 夜間バッチ calendar_update_job を実装（J-Quants API クライアント経由で差分取得→冪等保存、バックフィル・健全性チェック付き）。
  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETL 結果集約、品質チェック結果とエラー一覧を含む）。
    - pipeline/etl モジュール設計概念に基づいた差分取得・保存・品質チェックのインターフェース実装（jquants_client, quality モジュールとの連携を想定）。
    - デフォルトのバックフィルやカレンダー先読み等の定義を含む。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を用い、指定ウィンドウ内の記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチサイズ、1銘柄あたりの記事/文字数制限、JSON Mode を利用したレスポンス検証、レスポンス整形（前後余計テキスト除去）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ処理を実装。非5xx はスキップ処理。
    - レスポンス検証で未知らコードは無視し、得られたスコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT）。
    - テスト用に OpenAI 呼び出しポイントを patch 可能に設計（_call_openai_api を差し替え可能）。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の calc_news_window を使ってウィンドウを算出し、raw_news からキーワードでフィルタ。
    - OpenAI 呼び出しは独立実装（modular coupling を避けるため news_nlp の内部呼び出しを共有しない）。
    - API エラー/パース失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。ロールバック処理を含む。
    - リトライ・エラーハンドリングを実装（RateLimit, network, timeout, APIError などの分類と再試行ポリシー）。

- リサーチ（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン・200日MA乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）などファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベースの実装、データ不足時の None 取り扱い、ログ出力を備える。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Spearman rank）計算（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。ランクは平均ランク（ties を平均化）で処理。

- その他ユーティリティ
  - 多数の内部ユーティリティ（テーブル存在チェック、日付変換、クエリ用ヘルパーなど）を実装。
  - DuckDB を主要なストレージとして利用する設計（duckdb 接続を明示的に受け取る API）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キー等の重要情報は Settings 経由で取得。自動ロードを無効化する環境変数（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。
- .env の読み込みは protected set（OS 環境変数）を尊重して上書きを防止する仕組みを実装。

Notes / 設計上の重要点
- ルックアヘッドバイアス防止: 主要な関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）での失敗時は通常処理を中断せずフォールバック（例: macro_sentiment=0.0）や部分的スキップを行い、障害の影響を局所化する設計。
- テスト容易性: OpenAI 呼び出しポイントに差し替え可能なフックを用意し、ユニットテストでモック化しやすい。
- DuckDB との互換性配慮: executemany の空リストバインド回避や DATE 型取り扱い等、DuckDB 実装の差異に配慮した実装。

依存（コード上明示）
- duckdb
- openai（OpenAI SDK）

今後の課題（推測）
- strategy / execution / monitoring パッケージの実装（パブリッシュ時点ではモジュール構造は宣言済みだが実装の有無はコードに依存）。
- ai スコアリングの追加検証、モデル切替やAPIコスト管理機能の導入。
- 品質チェック（quality モジュール）と jquants_client の具体実装・テスト。

（以上）