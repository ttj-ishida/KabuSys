# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
日付はリポジトリ内のコードとドキュメントから推測して記載しています。

## [Unreleased]
- 開発中の小変更、リファクタリング、単体テスト追加など。

---

## [0.1.0] - 2026-04-13 (Initial release)
初回リリース。KabuSys のコア機能群を実装。以下の主要な機能・設計方針を含みます。

### Added
- 全体
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として追加。
  - 設定管理モジュール `kabusys.config` を追加。
    - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
    - `.env` と `.env.local` の読み込み順序（OS 環境変数 > .env.local > .env）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動読み込み無効化。
    - `.env` の堅牢なパース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い対応）。
    - 必須環境変数のチェック `_require()`、各種設定プロパティ（DBパス、PID/kill flag、threshold、env/log level 等）。
    - `PAPER_FILL_MODE` の妥当性検証（"instant"|"partial"|"never"|"reject"）。
    - `KABUSYS_ENV` の妥当性検証（development|paper_trading|live）。

- 実行/監視スクリプト
  - `run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境では Mock ブローカーを使用し、Paper 用 SQLite（`data/paper_trading.db`）で完全分離して動作。
    - `OrderRepository`、`OrderManager`、`RiskManager`、`Reconciler` を組み立てて `ExecutionEngine.run_session()` を実行。
    - DuckDB コネクションを使用（解析/集計用）。
    - 監視テーブルが存在することを保証する `init_monitoring_db()` 呼び出し。
  - `run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 `sqlite_path` を使用する設計。
    - 起動時にプロセス優先度を "high" に設定。

- ユーティリティ
  - `kabusys.utils.process_priority`
    - クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティ。
    - Windows と POSIX（Linux, Darwin, FreeBSD）を吸収。アクセス権限不足や未サポート環境では警告を出してスキップ。
    - `set_process_priority(level)` と `set_cpu_affinity(cpu_count)` を提供。

- 監視・ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - 出力項目: システム稼働率、総ポーリング数、注文成功率（Created/Filled/Sent）、リスク却下数、API レイテンシ（avg/max/P95）。
    - 日付範囲フィルタ（--from / --to）と DB パス指定（--db）をサポート。
    - 判定基準（閾値）を定義：
      - 稼働率 >= 99.0%
      - 注文成功率（Filled/Created） >= 90.0%
      - 送信率（Sent/Created） >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB テーブルが存在しない場合やデータ欠損時のフォールバック処理を実装（OperationalError を捕捉し N/A を出力）。

- ポートフォリオ構築（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点時は signal_rank でブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全銘柄スコアが 0 の場合は等金額にフォールバックし警告）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限 `apply_sector_cap`（既存保有のセクター露出が上限を超える場合に当該セクターの新規候補を除外。unknown セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対して 1.0/0.7/0.3。未知レジームは 1.0 でフォールバックし警告）。
  - `kabusys.portfolio.position_sizing`
    - 株数算出 `calc_position_sizes`。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based：ポジションあたりリスク（risk_pct）と stop_loss_pct に基づく算出。
    - equal/score：重みを用いた配分、max_position_pct と max_utilization による上限制約。
    - 単元（lot_size）で丸め、aggregate cap によるスケールダウンと残差処理（lot 単位で公平に配分）。
    - 手数料・スリッページを見積るための `cost_buffer` を考慮。

- リサーチ（DuckDB ベース）
  - `kabusys.research.factor_research`
    - モメンタム `calc_momentum`（1M/3M/6M リターン、MA200 乖離）。
    - ボラティリティ `calc_volatility`（ATR20、ATR 比、20日平均売買代金、出来高比率）。
    - バリュー `calc_value`（PER, ROE。raw_financials の最新レコードを参照）。
    - DuckDB を用いたウィンドウ関数中心の実装、データ不足時は None を返す設計。
  - `kabusys.research.feature_exploration`
    - 将来リターン計算 `calc_forward_returns`（horizons: default [1,5,21]、horizons の妥当性チェックあり）。
    - IC（スピアマンランク相関）計算 `calc_ic`（結合・欠損除外・有効レコードが 3 未満で None）。
    - ランク作成ユーティリティ `rank`（同順位は平均ランクで処理）。
    - ファクター統計サマリ `factor_summary`（count/mean/std/min/max/median）。

- AI / ニュース NLP
  - `kabusys.ai.news_nlp`
    - raw_news テーブルのニュースを OpenAI（gpt-4o-mini）でセンチメント解析し、銘柄ごとのスコアを `ai_scores` テーブルへ書き込む機能を追加。
    - 処理フロー:
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）で対象記事を集約。
      - 1 銘柄あたり最大記事数 / 文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 20 銘柄ずつバッチ送信（_BATCH_SIZE）。
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフとリトライ。
      - レスポンス検証、スコアを ±1.0 にクリップ。
      - 部分失敗に備え、更新は対象コードに限定して安全に置換（DELETE WHERE date=? AND code=ANY(codes) → INSERT）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - 設計方針としてルックアヘッドバイアス回避（global な date.today() を参照しない）とフェイルセーフを重視。

### Changed
- n/a（初回リリースのため過去リリースからの変更はなし）。

### Fixed
- .env パースの堅牢化
  - コメント、クォート、export プレフィックス、バックスラッシュエスケープ等に対応。空行やコメント行を無視。
- `MONITOR_POLL_INTERVAL` の入力検証
  - 0 以下や非整数値を検知してログ警告を出し、既定値へフォールバックするように変更（監視ループの time.sleep での ValueError を防止）。
- Paper 検証レポート生成時の欠損データハンドリング
  - テーブルが存在しない場合やクエリで OperationalError が発生した場合に N/A を出力して処理を継続。

### Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護（protected set）する挙動を採用。`.env.local` の override は許可するが OS 環境変数は上書きしない。

### Notes / Implementation details / TODOs
- position_sizing:
  - price が欠損（0.0）の場合にエクスポージャーが過小見積りされる懸念がある旨の TODO コメント（前日終値等のフォールバック検討）。
  - lot_size は現状グローバル固定（将来的には銘柄別 lot_map を検討）。
- news_nlp:
  - 実際の OpenAI レスポンス検証、リトライ実装の詳細（JSON Mode 使用、429 等で指数バックオフ）を想定しているが、外部 API の利用環境に依存。
- config:
  - プロジェクトルート探索は __file__ の親を上方向に探索する方式で実装しているため、CWD に依存しない。
- 実運用上の設定（閾値、PID ファイルパス、kill flag 挙動など）は環境変数で調整可能。

---

開発者向け補足:
- 初回リリースでは各モジュールが純粋関数設計（副作用を最小化）で実装されている箇所が多く、単体テストの追加に適した設計になっています。
- DuckDB を解析基盤として広く利用しており、prices_daily / raw_financials / raw_news / ai_scores 等のスキーマが前提となります。DB スキーマの変更は互換性に影響する可能性があります。

（以上）