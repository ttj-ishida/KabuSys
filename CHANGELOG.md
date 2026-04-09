# Changelog

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog に準拠しています。  

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。ライブラリ全体のコア機能群を実装しました。主に日本株向けのデータ収集・ETL・ファクター計算・AIベースのニュースセンチメント評価・市場レジーム判定・カレンダー管理などの機能を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ で定義。

- 環境設定 / ロード
  - .env ファイルおよび環境変数を読み込む設定モジュールを追加（kabusys.config）。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を探索）。
  - .env と .env.local を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式やクォート・エスケープ・インラインコメントなどの .env 文法を考慮したパーサ実装。
  - Settings クラスを追加し、以下などの設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
    - DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE（バリデーション付き）, PAPER_TRADING_SQLITE_PATH
    - 監視用 PID/KILL フラグパス、リソース閾値（CPU/Memory/Disk）
    - 環境種別（development/paper_trading/live）と LOG_LEVEL のバリデーション
  - 設定プロパティは未設定時に ValueError を投げる（必須項目の明示的エラー）。

- AI ニュース NLP
  - kabusys.ai.news_nlp: ニュース記事を LLM（gpt-4o-mini）でセンチメント付与し ai_scores テーブルへ書き込む処理を実装。
  - 対象期間のウィンドウ計算（JST基準）を実装（calc_news_window）。
  - 銘柄ごとに記事を集約し、1銘柄あたり記事数・文字数の上限でトリムするロジックを導入。
  - バッチ処理（最大20銘柄/コール）とリトライ（429/ネットワーク/タイムアウト/5xx）を実装。指数バックオフを採用。
  - JSON Mode を利用しつつ、レスポンスの頑健なパースとバリデーションを実装（results 配列、型チェック、未知コードの無視、スコアのクリップ）。
  - 部分成功を考慮し、ai_scores への書き込みは該当コードのみ DELETE→INSERT で置換（冪等性・部分失敗保護）。
  - テスト容易性のため OpenAI クライアント呼び出し部を差し替え可能に設計（_call_openai_api の patch を想定）。

- 市場レジーム判定
  - kabusys.ai.regime_detector: ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLMセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を決定して market_regime テーブルへ書き込む機能を実装。
  - ma200_ratio 算出は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを排除。
  - マクロキーワードで raw_news をフィルタして LLM に渡すロジックを追加。
  - OpenAI 呼び出しは独立実装、リトライ・フォールバック（API 失敗時は macro_sentiment=0.0）を採用。
  - DB への書込みは BEGIN / DELETE / INSERT / COMMIT の冪等操作を行い、失敗時に ROLLBACK を実施。

- データ & ETL
  - kabusys.data.pipeline: ETL の高水準インターフェースを実装し、ETLResult dataclass を提供（etl 結果集計、品質問題やエラーの集約を含む）。
  - ETLResult に has_errors / has_quality_errors / to_dict を実装。
  - ETL 設計として差分更新、バックフィル（既存データの数日前から再取得）、品質チェックの集約を想定。
  - kabusys.data.etl は pipeline.ETLResult を再エクスポート。

- マーケットカレンダー管理
  - kabusys.data.calendar_management を実装。market_calendar の存在チェック、営業日判定、前後の営業日探索、期間内営業日一覧取得、SQ 日判定を提供。
  - market_calendar が未取得の場合は曜日ベース（土日休み）でフォールバックする挙動を採用し、DB 登録値がある場合はそれを優先。
  - next_trading_day / prev_trading_day は最大探索範囲（_MAX_SEARCH_DAYS）を設定し無限ループを防止。
  - calendar_update_job を実装し、J-Quants から差分取得して market_calendar を冪等に更新する（バックフィル・健全性チェック付き）。
  - jquants_client 経由での取得/保存処理を想定（jq.fetch_market_calendar / jq.save_market_calendar）。

- リサーチ（ファクター計算・特徴探索）
  - kabusys.research パッケージを追加し、以下を実装・公開:
    - factor_research.calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離などを計算。データ不足時は None を返す。
    - factor_research.calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率を計算。
    - factor_research.calc_value: raw_financials から直近財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。
    - feature_exploration.calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで計算。
    - feature_exploration.calc_ic: スピアマン（ランク）相関による IC 計算を実装。サンプル数不足時は None を返す。
    - feature_exploration.factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
    - feature_exploration.rank: 同順位は平均ランクを返すランク関数を実装（丸めにより ties の誤検出を防止）。
  - データベースアクセスは DuckDB を想定し、SQL ウィンドウ関数を多用した実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- フォールバックやエラーハンドリングの実装により、以下を防止:
  - OpenAI API の一時障害や JSON パース失敗による例外の未処理（多くのケースでフォールバック値を使用し処理継続）。
  - DuckDB executemany に対する空パラメータの問題を回避（空時は実行をスキップ）。
  - .env ファイル読み込みの IO エラーに対して警告を出し安全に継続。

### Security
- OpenAI API キーや各種トークンは Settings で必須チェックを行い、未設定時は ValueError を発生させることで誤った運用を防止。
- .env 自動ロード時、既存の OS 環境変数は保護され、.env.local による上書きは意図的に行えるよう配慮（protected set の導入）。

### Notes / Known limitations
- 多くの関数はルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計。必ず target_date を引数で与える必要がある。
- AI 呼び出し周りは OpenAI SDK（gpt-4o-mini）を想定しているため、API 仕様変更時は調整が必要。
- ai_scores / market_regime への書き込みは部分成功を想定した設計だが、DB スキーマ互換性や DuckDB バージョン差異に注意（特に配列バインドの互換性）。
- 一部ファクターはデータ不足時に None を返す。 downstream での扱いに注意。

### Migration / Upgrade notes
- 環境変数の命名と必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等は明示的に設定してください。
- 自動 .env 読み込みを止めたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の挙動は PAPER_FILL_MODE で指定可能（instant/partial/never/reject）。

---

この CHANGELOG はコードベースからの推定に基づいて作成しています。実際のリリースノートを作成する際は追加のリリース日、コミット参照、影響のあるユーザー向けの具体的な手順を追記することを推奨します。