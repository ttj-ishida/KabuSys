Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトはセマンティック バージョニング (SemVer) を使用します。

[参考] Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-28

初回リリース。パッケージ全体の主要機能群を実装しました（データ取り込み・カレンダー管理・研究用指標計算・ニュース/マクロのAIスコアリング・設定管理など）。以下は実装内容と設計上の重要な点の概略です。

### Added
- パッケージ初期化
  - kabusys パッケージのベースを追加（src/kabusys/__init__.py、バージョン 0.1.0）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して判定。
  - .env と .env.local の読み込み順序（OS 環境 > .env.local > .env）をサポート。
  - export KEY=val、クォート付き値、インラインコメントなどに対応する堅牢な .env パーサーを実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - Settings クラスを追加し、J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティとバリデーションを提供。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを提供。

- ニュース NLP（src/kabusys/ai/news_nlp.py）
  - OpenAI（gpt-4o-mini）を用いてニュース記事の銘柄ごとセンチメントを算出し、ai_scores テーブルに書き込む機能を実装。
  - ニュース集約ロジック（前日15:00 JST〜当日08:30 JST のウィンドウ計算、記事数/文字数トリム）を実装。
  - バッチサイズ、トークン肥大対策、JSON Mode のレスポンス検証を実装。
  - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライと、失敗時はスキップし継続するフェイルセーフ設計。
  - テストのため _call_openai_api をモック可能に設計。
  - DuckDB の executemany の空リスト問題に対する防御（空時は呼ばない）を実装。

- マクロ・市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等書き込みする機能を追加。
  - prices_daily / raw_news を用いる計算、OpenAI API 呼び出し（JSON mode）、再試行・バックオフ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
  - ルックアヘッドバイアス回避の観点から datetime.today() / date.today() を直接参照しない設計。API キー注入可能。

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py）
    - 差分更新、バックフィル、品質チェック連携を想定した ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧を保持）。
    - DuckDB のテーブル存在チェック、最大日付取得ユーティリティ等を追加。
  - ETL インターフェースの再エクスポート（src/kabusys/data/etl.py）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを参照して営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - カレンダー未取得時は曜日ベースでフォールバック（週末 = 非営業日）。
    - calendar_update_job を実装し J-Quants からの差分取得 -> 保存（バックフィル、健全性チェック含む）を実行可能。
    - DB にある値を優先しつつ、未登録日の一貫したフォールバックロジックを実装。

- 研究用モジュール（src/kabusys/research）
  - factor_research.py: モメンタム、ボラティリティ、バリュー等の定量的ファクター計算を実装（calc_momentum, calc_volatility, calc_value）。
    - MOMENTUM: 1M/3M/6M リターン、200 日 MA 乖離。
    - VOLATILITY: 20日 ATR / 相対 ATR、20日平均売買代金、出来高比率。
    - VALUE: PER / ROE（raw_financials からの最新値を使用）。
  - feature_exploration.py: 将来リターン計算（複数ホライズン対応）、Spearman IC（ランク相関）、ランク付けユーティリティ、統計サマリーを実装。
  - research/__init__.py で主要関数を公開。

- 依存先・設計に関する注記
  - OpenAI 呼び出しは JSON モードを想定し厳密な JSON を期待するが、レスポンスの前後ノイズに対しても復元処理を行う。
  - 各所で詳細なログ出力（info/debug/warning/exception）を行い、運用観点での可観測性に配慮。

### Changed
（初回リリースのため「既存からの変更」は無し。以下は設計上の重要仕様の明示）
- ルックアヘッドバイアス対策: AI スコアリング / レジーム判定 / ETL / 集計処理など、多くの関数は内部で date.today() を参照せず、呼び出し元から target_date を明示的に渡す設計にしている。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT 想定）に設計。
- DuckDB の互換性（executemany の空リスト制約等）に配慮した実装になっている。

### Fixed
- .env パーサーの細かなパターン（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い）に対応して堅牢性を確保。
- OpenAI API 呼び出しでの一部例外に対してリトライやフォールバックを実装（RateLimitError / APIConnectionError / APITimeoutError / APIError の扱いを明確化）。
- JSON レスポンスパース失敗時にフォールバックして安全にスキップするロジックを追加（サービス停止を避けるため）。

### Security
- 機密データ（OpenAI API key など）は Settings を介して環境変数から取得。API キーは関数引数で注入可能でテスト容易性と管理柔軟性を両立。

### Testing / Developer notes
- テストしやすさのため、OpenAI 呼び出し箇所は内部関数（_call_openai_api）を介しており、unittest.mock.patch による差し替えを想定。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できる（CI / 単体テストでの環境分離に有用）。
- DuckDB を想定した SQL 実行パターンのため、ローカルテストでは小さな DuckDB インメモリ DB を用いるとよい。

---

注: 本 CHANGELOG はリポジトリ内の現行コード内容を基に推測して作成しています。実際のリリースノート作成時には変更履歴（コミットログやリリース担当者の意図）に基づいて適宜調整してください。