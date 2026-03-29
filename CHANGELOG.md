# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」仕様に準拠し、慣例に従ってセクションを分けています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-29

初回リリース — KabuSys のコア機能を実装しました。以下はコードベースから推測してまとめた主な追加・設計方針・重要な実装上の注意点です。

### Added
- パッケージの初期公開
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ で data / strategy / execution / monitoring をエクスポート（将来モジュール拡張を想定）

- 設定管理
  - 環境変数読み込みユーティリティ（kabusys.config）を実装
    - プロジェクトルート検出（.git または pyproject.toml を基準）により、CWD に依存しない .env 自動ロード
    - .env / .env.local の優先順位処理（OS 環境変数は保護、.env.local は上書き）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートやバックスラッシュエスケープの考慮、インラインコメント処理）
  - Settings クラスを提供し、アプリ設定をプロパティ経由で取得
    - J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを実装
    - 未設定の必須変数は ValueError を送出

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news, news_symbols を集約して銘柄ごとのニュースを作成
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄／チャンク）
    - JSON Mode 応答の検証とパース、スコアの ±1.0 クリップ
    - 429・ネットワーク断・タイムアウト・5xx を対象に指数バックオフ再試行
    - レスポンス検証失敗や API エラー時は該当チャンクをスキップ（フェイルセーフ）
    - DuckDB に対して idempotent（DELETE → INSERT）で書き戻し。部分失敗時に他銘柄データを保護する実装
    - テスト容易性のために _call_openai_api を分離（unittest.mock.patch で差し替え可能）
    - ニュースウィンドウ計算ユーティリティ calc_news_window を実装（JST 基準、UTC 変換）

  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定
    - prices_daily / raw_news / market_regime を参照してスコアを計算し、冪等的に market_regime テーブルへ書き込み
    - マクロセンチメントは OpenAI を用い、API エラー時は 0.0 にフォールバック（フェイルセーフ）
    - API 呼出しの再試行・バックオフ、JSON パースの堅牢化、スコアクリッピングを実装
    - テストのため _call_openai_api を分離

- Research モジュール（kabusys.research）
  - factor_research: calc_momentum, calc_value, calc_volatility を実装
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - Value: PER／ROE（raw_financials から最新レコード取得）
    - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - DuckDB SQL ウィンドウ関数を活用した実装
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank を実装
    - 将来リターン（任意の営業日ホライズン）を LEAD により一括取得
    - スピアマン（ランク）IC 計算（ties は平均ランク）、有効レコードが少ない場合は None を返す
    - 基本統計量（count/mean/std/min/max/median）を計算するユーティリティ
  - kabusys.research.__init__ で必要関数をエクスポート

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar テーブル参照）と営業日ロジックを実装
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得の場合は曜日（平日）ベースのフォールバックを行う設計
    - calendar_update_job: J-Quants から差分取得し冪等的に保存、バックフィルと健全性チェック（将来日付過大時はスキップ）
  - pipeline / etl
    - ETLResult データクラスを実装し、ETL 実行結果の構造化（品質チェック結果・エラー一覧等）を行う
    - デフォルトのバックフィルやカレンダー先読みなど DataPlatform に準じた設計方針
  - etl モジュールで pipeline.ETLResult を再エクスポート

### Fixed / Behaviors hardened
- .env パーサの改良
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いを実装して誤読を防止
- DuckDB 対応の互換性処理
  - executemany に対する空リスト問題（DuckDB 0.10）を回避するため、空リストチェックを追加してから executemany を実行
  - 日付値変換ユーティリティ (_to_date) を実装し DuckDB の戻り値を安全に date に変換
- Look-ahead バイアス回避
  - AI / リサーチ処理のすべてで date.today() / datetime.today() を直接参照しない設計（target_date を明示的に受け取る）
  - prices_daily クエリでルックアヘッドを防ぐ条件（date < target_date / date BETWEEN ..）を明記

### Security / Safety
- OpenAI API キーの取り扱い
  - api_key を引数で注入可能にし、未設定時は環境変数 OPENAI_API_KEY を参照。未設定なら ValueError を送出して誤動作を防止
- フェイルセーフ方針
  - LLM 呼び出し失敗時は例外を上位に伝播させず（該当部分をスキップ or 0.0 にフォールバック）して全体処理の継続を優先

### Design notes / テスト性
- テスト容易性
  - OpenAI 呼び出しを行う内部関数をモジュール内で分離しており、unittest.mock.patch により注入・差し替えが可能
- 冪等性
  - DB 書き込みは可能な限り冪等（DELETE → INSERT、ON CONFLICT 想定）にして再実行耐性を確保

### Documentation / 説明
- 各モジュール冒頭に処理フロー・設計方針・注意点を詳細に記述した docstring を多数追加（コード自体がドキュメント的にまとまっている）

### Removed / Deprecated
- なし

---

注: 上記は提示されたコード内容からの推測に基づく CHANGELOG です。実際のコミット履歴やリリースノートとは差異があり得ます。必要であれば、個々の関数・ API 仕様や外部依存（OpenAI / J-Quants / kabuapi）に関するより詳細な変更点や既知の制約・注意事項を追記します。