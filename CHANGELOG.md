# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

- リリース日付は YYYY-MM-DD 形式で記載しています。
- すべての変更は後方互換性や設計上の注意点を可能な限り明記しています。

## [0.1.0] - 2026-03-31

### Added
- パッケージの初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
  - src/kabusys/__init__.py にて __version__ を設定し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - OS側の既存環境変数を保護するため、読み込み時の「protected」キーセットを扱う設計。
  - .env パーサ実装: export プレフィックス、クォート文字列（バックスラッシュエスケープ対応）、インラインコメント判定などに対応。
  - Settings クラスを公開（settings）。J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level）等のプロパティを提供。
    - env の有効値チェック（development / paper_trading / live）。
    - log_level の有効値チェック。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へ JSON モードで投げて銘柄単位のセンチメント（-1〜1）を算出。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数・最大文字数）などトークン肥大化対策を実装。
    - API エラー（429, ネットワーク断, タイムアウト, 5xx）は指数バックオフでリトライ。その他はスキップして継続するフェイルセーフ設計。
    - レスポンス検証機能を実装（JSON パース、results 配列・code/score 検証、スコア数値化とクリッピング）。
    - DuckDB への書き込みは部分的に置換（対象 code のみ DELETE → INSERT）することで部分失敗に強い設計。
    - ルックアヘッドバイアスを避けるため datetime.today()/date.today() を参照しない設計。calc_news_window ユーティリティを提供（JST 窓 → UTC に変換）。
    - テスト容易性のため _call_openai_api をモック差し替え可能（unittest.mock.patch）。

  - regime_detector.score_regime
    - 日次で市場レジーム（bull / neutral / bear）を判定する機能を提供。
    - ETF 1321 の 200日移動平均乖離（重み 70%）と、news_nlp により得たマクロニュースセンチメント（重み 30%）を合成してスコア化。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価の呼び出し実装（JSON 出力期待）。
    - API 失敗時は macro_sentiment = 0.0 とするフェイルセーフ。リトライロジック・5xx 判定など堅牢化。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）を実装。
    - ルックアヘッドバイアス回避の設計（prices_daily のクエリで date < target_date を用いる等）。
    - テスト容易性のため _call_openai_api を差し替え可能にしている。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル）と夜間バッチ更新処理（calendar_update_job）を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日判定ユーティリティを提供。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した方針。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）やバックフィル、健全性チェック等を追加して安全性を確保。
    - J-Quants クライアント（jquants_client）との連携で差分取得・保存を行う。

  - pipeline / etl / ETLResult
    - ETLResult データクラスを公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
    - ETL パイプライン設計: 差分取得、保存（idempotent）、品質チェック（quality モジュール）を想定した設計ドキュメントに沿った実装方針を反映。
    - _get_max_date などの内部ユーティリティを実装して DB 状態に基づく差分取得をサポート。
    - デフォルトのバックフィル日数、カレンダー先読み日数、最小データ開始日等の定数を設定。

- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性指標（20日平均売買代金、出来高比）およびバリュー（PER、ROE）を DuckDB の SQL と Python 組合せで計算する関数を実装。
    - データ不足時の None 処理やログ出力を実装。
    - 出力は (date, code) をキーとする dict のリストで統一。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対する将来終値リターンを一括クエリで取得。入力検証（horizons の正当性）あり。
    - IC（Information Coefficient）計算（calc_ic）: Spearman ランク相関を実装。レコード不足や定数分散の際は None を返す。
    - rank, factor_summary: ランク付けユーティリティ（同順位は平均ランク）や基本統計量サマリー関数を提供。
  - research パッケージの __all__ に主要関数を明示的に公開（zscore_normalize を含む）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / Design decisions / 互換性
- OpenAI 呼び出しでは JSON mode（response_format={"type": "json_object"}）を想定しているが、実運用で前後に余計なテキストが混入する場合があるため、その復元ロジックを実装している。
- DuckDB 0.10 の executemany に空リストを渡せない制約に対する対策（空チェック）を実装。
- ルックアヘッドバイアス防止のため、すべてのバッチ処理で target_date を明示的に受け取り、内部で date.today() を直接参照しない設計を採用。
- テスト容易性の確保: OpenAI 呼び出しポイント（_call_openai_api）をユニットテストで差し替え可能にしている。
- 環境変数の自動読み込みはプロジェクトルート検出に基づくため、パッケージ配布後も動作することを想定。ただしプロジェクトルートが見つからない場合は自動ロードをスキップする。

### Security
- API キー（OpenAI 等）は引数で注入可能（テスト用）かつ環境変数 OPENAI_API_KEY を用いる。キーの直接ハードコードは行われていない。
- .env パーサはエスケープやクォートを適切に扱うよう実装しているが、.env ファイルの取り扱いは運用者側で厳重に管理すること。

---

今後の予定（例）
- strategy / execution / monitoring の実装拡充（バックテスト、実行エンジン、監視アラート等）。
- docstring を元にしたユーザ向けドキュメント（使用例・API リファレンス）の整備。
- テストケース（ユニット・統合）の追加と CI 連携。

もし CHANGELOG の粒度（モジュール別により細かく、または逆に要約）や日付の変更など希望があれば指示ください。