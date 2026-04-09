CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]: https://example.com/kabusys/compare/HEAD...0.1.0
[0.1.0]: https://example.com/kabusys/releases/tag/0.1.0

## [0.1.0] - 2026-04-09

最初の公開リリース。日本株自動売買支援ライブラリ「KabuSys」のコア機能群を提供します。
主にポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を用いたニュース評価・レジーム判定、環境設定管理、監視ログ永続化のモジュールを含みます。

### Added
- 基本情報
  - パッケージバージョンを設定: __version__ = "0.1.0"。

- 環境/設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索し、自動ロードを行う。
  - .env/.env.local の優先順と上書きルールを実装（OS 環境変数保護、.env → .env.local）。
  - 行パーサー: export 形式、クォート、エスケープ、インラインコメント処理などに対応する堅牢な .env パース実装。
  - Settings クラス: 各種設定プロパティを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE のトークン/ユーザー、DB パス、paper trading 関連、監視閾値、環境 / ログレベル判定ユーティリティ等）。
  - 入力バリデーション: PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の有効値チェックを実装。

- ポートフォリオ構築 (src/kabusys/portfolio/*)
  - 銘柄選定: select_candidates — スコア降順 + signal_rank によるタイブレークで候補抽出。
  - 重み算出:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア比例配分（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - ポジションサイジング: calc_position_sizes — risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、max_position_pct、aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケーリング・端数配分ロジックを実装。
  - リスク調整:
    - apply_sector_cap — 既存保有のセクター露出が上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは除外対象にしない）。
    - calc_regime_multiplier — 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームはフォールバック）。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research/*)
  - calc_momentum — 1M/3M/6M リターンと MA200 乖離率を DuckDB の prices_daily から算出。
  - calc_volatility — 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を算出（true_range の NULL 伝播を注意して処理）。
  - calc_value — raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新財務レコードを target_date 以前から取得）。
  - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons の検証あり。
  - calc_ic / rank — ファクターと将来リターンのスピアマンランク相関（IC）計算。ties を平均ランクで処理するランクユーティリティ。
  - factor_summary — 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - すべての関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照。外部 API にはアクセスしない設計。

- AI モジュール (src/kabusys/ai/*)
  - ニュース NLP (news_nlp.py)
    - raw_news / news_symbols から指定ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む処理を実装。
    - バッチ（最大 20 銘柄）送信、トークン肥大化対策（最大記事数/文字数トリム）、JSON バリデーション、スコアの ±1.0 クリッピング。
    - 再試行ロジック: 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ（最大リトライ回数）。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップ、部分成功時は既存スコアを保護するため対象コードのみを DELETE → INSERT。
  - レジーム検出 (regime_detector.py)
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull' / 'neutral' / 'bear' を日次判定。
    - マクロニュースはキーワードフィルタで抽出し（複数キーワード）、LLM 呼び出しは耐障害性を持たせる。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - レジームスコアは閾値でラベリングし、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を使った MonitoringDB 初期化関数 init_monitoring_db を実装（system_status/trade_logs/positions/risk_logs などのテーブルとインデックスを作成、冪等）。
  - 監視データ保存用の基本スキーマを提供。

- パッケージ公開用 __all__ エクスポート
  - portfolio, research, ai の主要関数をパッケージトップから import できるように公開。

### Changed
- （初回リリースのため該当なし）

### Fixed / Improvements
- 環境変数パーサの堅牢化:
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを実装して .env の柔軟な記述に対応。
- DuckDB SQL 実装上の注意点に対処:
  - raw_financials の最新レコード取得に ROW_NUMBER を使用する等、DuckDB 互換性を考慮したクエリ実装。
  - executemany に空リストを渡せない DuckDB の挙動に対するガードを実装（空時は実行しない）。
- AI 呼び出しの堅牢性:
  - JSON モードでのレスポンスに前後ノイズが入る場合に最外の {} を抽出して復元するロジックを追加。
  - LLM が整数で code を返す等のケースに備え、code を str 正規化して照合。
- フェイルセーフ／ロギングの強化:
  - API・DB エラー発生時にロールバックを試み、ロールバック失敗時は警告ログを残す実装。

### Security
- .env 自動読込時に OS 環境変数を保護（既存の環境変数キーを protected として .env/.env.local による上書きを制御）。
- OpenAI API キーは引数で明示的に渡すか環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出して誤操作を防止。

### Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーやサイジングが過小見積りされ得る旨の注記あり。将来的に前日終値や取得原価をフォールバックとして利用する拡張を検討。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO コメントあり）。
- news_nlp / regime_detector:
  - LLM 呼び出しは外部 OpenAI SDK に依存するため、実行環境に openai パッケージと有効な API キーが必要。
  - LLM レスポンスは非決定性があるため、部分失敗やスコア欠損を考慮した設計（部分書込み保護）にしているが、完全な成功を保証するものではない。
- research モジュール:
  - 各ファクター計算は prices_daily / raw_financials に依存。十分な過去データがない場合は None を返す／中立フォールバックする箇所がある。

### Upgrade notes / 初期設定メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 関連）
  - KABU_API_PASSWORD（kabuステーション API）
  - OPENAI_API_KEY（AI 機能を利用する場合）
- 主要なデフォルト設定:
  - KABUSYS_ENV: "development"（有効値: development, paper_trading, live）
  - LOG_LEVEL: "INFO"（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_FILL_MODE: "instant"（instant/partial/never/reject）
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト等で便利）。

---

今後の開発予定（例）
- 銘柄別 lot_size 対応、手数料/スリッページのより現実的な推定、AI モデル切り替えの抽象化、追加のファクター・ポートフォリオ最適化手法、単体テストと CI の強化など。