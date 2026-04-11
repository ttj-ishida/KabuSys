# CHANGELOG

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
慣例に従い、バージョンごとに「Added/Changed/Fixed/Deprecated/Removed/Security」カテゴリで変更点を記載します。

## [Unreleased]

- ドキュメント、テスト、及びいくつかの機能拡張（単元ごとの lot_size マスタ対応、価格フォールバック戦略、AI 呼び出しの更なる堅牢化など）を予定。

---

## [0.1.0] - 2026-04-11

初回公開リリース。システムは日本株自動売買のための以下主要コンポーネントを含みます。

### Added
- 全体
  - パッケージ基礎（kabusys）を追加。バージョンは `0.1.0`。
  - DuckDB / SQLite を用いたオンプレミスデータワークフローを導入。
  - ロギングは基本的に INFO レベルで初期化。

- 設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートの .git または pyproject.toml を探索）。
  - 高機能な .env パーサーを実装：
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートなしの場合は '#' の前に空白があるとコメントとみなす）
  - 認証トークン / DB パス /監視閾値 / 環境種別（development/paper_trading/live）などを Settings クラス経由で取得し、値チェック（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の妥当性検証）を実施。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。

- 実行スクリプト
  - run_execution:
    - ExecutionEngine 起動スクリプトを追加。
    - Paper trading 環境（KABUSYS_ENV=paper_trading）の場合、Paper 用 SQLite を分離して使用（デフォルト: data/paper_trading.db）。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててセッションを実行。
    - 起動時にプロセス優先度を「high」に設定（set_process_priority）。
  - run_monitoring:
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境に関わらず本番 sqlite_path を使用する挙動を明記。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux/Mac/FreeBSD）を吸収するプロセス優先度設定機能を実装。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
  - アクセス権限エラー等が発生した場合は警告ログを出して安全にスキップ。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - 候補選定（select_candidates）: スコア降順、同点は signal_rank でタイブレーク。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）: 全スコアが 0 の場合は等配分にフォールバックして警告ログ。
  - risk_adjustment:
    - セクター集中制限（apply_sector_cap）: 現物保有時価を考慮して同一セクターの新規候補を除外。unknown セクターは制限対象外。
    - レジーム乗数（calc_regime_multiplier）: 'bull'/'neutral'/'bear' に対する乗数マップ（未指定レジームは 1.0 へフォールバックし警告）。
  - position_sizing:
    - position size 計算（calc_position_sizes）: risk_based / equal / score の各方式を実装。単元株（lot_size）丸め、per-position 上限 / aggregate cap（available_cash）でのスケールダウン、cost_buffer を考慮した安全なスケーリング処理を実装。
    - aggregate スケールダウン時の端数配分（lot 単位）に関する安定なアルゴリズムを実装。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（calc_momentum）: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - ボラティリティ（calc_volatility）: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算。欠損がある場合の取り扱いに注意。
    - バリュー（calc_value）: raw_financials の最新財務を取り出して PER / ROE を算出。
  - feature_exploration:
    - 将来リターン算出（calc_forward_returns）: 任意ホライゾン（デフォルト [1,5,21]）でのリターンを一括取得。
    - IC（calc_ic）: スピアマンランク相関による Information Coefficient を計算（有効レコードが 3 件未満の場合 None を返す）。
    - 基本統計（factor_summary）: count/mean/std/min/max/median を算出（None 値除外）。
    - ランク付けユーティリティ（rank）。
  - 実装方針として外部ライブラリに依存せず DuckDB SQL と標準ライブラリのみで計算する設計。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）に対して銘柄ごとのニュースセンチメントを問い合わせ、ai_scores テーブルに書き込む機能を実装。
    - JST 時間ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して厳密な窓で抽出。
    - バッチサイズ、トークン抑制（最大記事数・文字数）、バリデーション、スコアクリッピング（±1.0）、冪等的な書き込み（DELETE→INSERT）を実装。
    - API の 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでのリトライを実装。失敗時はフェイルセーフでスキップ。
    - DuckDB の executemany が空リストを受け付けない制約（0.10 系）への対処を組み込む。
    - 外部 API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。未設定時は例外。

  - regime_detector:
    - ETF (1321) の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（'bull'/'neutral'/'bear'）を判定し、market_regime テーブルへ冪等的に書き込む。
    - prices_daily の参照は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
    - マクロニュース抽出は定義されたキーワード群でフィルタ。
    - API 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。

### Changed
- DB 関連の扱い
  - run_execution は paper_trading 環境で明示的に別 DB を使うようにし、本番 DB とデータ分離を明確化。
  - monitoring 用の DB 初期化（init_monitoring_db）を起動時に冪等的に呼び出すことでテーブルの存在を保証。

- 日時取り扱い方針
  - 主要な AI / レジーム判定 / ニュース集約部分では datetime.today()/date.today() を使用せず、明示的な target_date を受け取る設計でルックアヘッドバイアスを防止。

### Fixed
- 設定値の堅牢性強化
  - MONITOR_POLL_INTERVAL が 0 や負値、非整数のケースで ValueError を避け、警告ログを出してデフォルト（60 秒）にフォールバックする処理を追加。
  - PAPER_FILL_MODE の不正値チェックを強化し、許容値以外は ValueError を投げるようにした。
  - DuckDB に対する executemany の空パラメータ問題を回避するガードを追加（空リスト時は実行しない）。

- OpenAI 統合の堅牢化
  - API レスポンスの JSON パースに失敗した場合、文字列中の最外枠の JSON を抽出して復元を試みる。
  - レスポンスのバリデーションを厳格化（results キーの存在、要素それぞれの型検査、未知コードの無視、スコアの数値性・有限性確認）。
  - リトライ対象エラーを限定し、上限到達時は安全にスキップして継続。

### Known issues / Notes
- price_map の欠損（0.0 や None）によるセクターエクスポージャーの過少評価があり得る（TODO: 前日終値や取得原価などでフォールバックする拡張を検討）。
- position_sizing の将来的拡張として銘柄別 lot_size マスタ対応を予定（現状は全銘柄共通の lot_size を使用）。
- AI 呼び出しはレート制限やコストに依存するため、運用時のキー管理とコスト監視が必要。
- regime_detector のしきい値や重みは現状ハードコード（MA/マクロ比率等）であり運用時の検証が必要。
- 未対応 OS でのプロセス優先度設定はスキップして警告を出す。

---

著者: KabuSys 開発チーム (コードベースから自動推測して記載)