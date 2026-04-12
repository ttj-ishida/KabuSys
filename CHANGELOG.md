# CHANGELOG

すべての注目する変更を記録します。フォーマットは Keep a Changelog に準拠しています。

なお、本ログはリポジトリ内のコードを解析して推測した変更点・機能一覧をまとめたものであり、実際のコミット履歴ではありません。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-12
初回リリース。自動売買システム「KabuSys」のコア機能群を実装しています。主な追加点は以下のとおりです。

### Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として導入（src/kabusys/__init__.py）。
  - Settings クラスにより環境変数・設定を集中管理（src/kabusys/config.py）。
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - .env パースの強化（コメント、export プレフィックス、クォート中のエスケープ処理などに対応）。
    - 多数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス /監視閾値 / 環境モード 等）。
    - 値検証を行い、不正値時には ValueError を送出。

- 実行・監視プロセス
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（モックと実ブローカーを切替）。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine.run_session() を起動。
    - DuckDB と SQLite の接続を確立し、終了時に確実にクローズ。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒、無効値は警告してデフォルト使用）。
    - 監視処理は設定にかかわらず本番 sqlite_path を使用して監視 DB を初期化。
    - プロセス優先度設定（高優先度）と例外耐性（check_once() 内の例外は記録してループ継続）。
    - Ctrl+C（KeyboardInterrupt）時のグレースフル終了。

- モニタリング DB
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を呼び出し、監視用テーブルの存在を保証（冪等）。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) によるコアピンニング機能。
    - 権限不足や未対応 OS の場合は警告してスキップするフェイルセーフ実装。

- ポートフォリオ構成（Portfolio Construction）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates：スコア降順で上位 N を選択、同点時は signal_rank でタイブレーク。
    - calc_equal_weights / calc_score_weights：等金額・スコア加重配分。スコア全てが 0 の場合は等金額にフォールバックして警告。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap：既存ポジションのセクター集中を計算し、上限超過セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier：レジームに応じた投下資金乗数（bull/neutral/bear のマッピングとフォールバック）。
  - ポジションサイズ決定（src/kabusys/portfolio/position_sizing.py）。
    - calc_position_sizes：risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）で丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）を考慮してスケールダウン。
    - cost_buffer による手数料・スリッページ見積りを組み込み、残余キャッシュの再配分ロジックを実装。

- リサーチ / ファクター計算
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）。
    - calc_momentum：1M/3M/6M リターン、MA200 乖離率を DuckDB SQL で計算。
    - calc_volatility：20日 ATR、ATR/株価、20日平均売買代金、出来高比率を計算。
    - calc_value：raw_financials から EPS/ROE を取得して PER・ROE を計算。
    - DuckDB を用いた高パフォーマンスな SQL 実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns：複数ホライズンの将来リターンを一括で取得。
    - calc_ic：Spearman（ランク相関）によりファクターの IC を計算（ties の平均ランク処理含む）。
    - factor_summary / rank：基本統計量・ランク付けの純粋 Python 実装。
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。

- AI / ニュースNLP
  - news_nlp（src/kabusys/ai/news_nlp.py）。
    - raw_news を銘柄単位に集約し、OpenAI API（gpt-4o-mini）に対してバッチスコアリングを行うワークフローを実装。
    - バッチサイズ、トークン肥大化対策（1銘柄あたり最大記事数・文字数）、JSON Mode を期待するプロンプト、スコアクリッピング（±1.0）。
    - リトライ（429/ネットワーク/5xx）に対する指数バックオフ、結果バリデーション、部分更新（成功銘柄のみ ai_scores に置換）をサポート。
    - score_news のタイムウィンドウ計算（JST基準→UTC変換）を提供。

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、P95 レイテンシ等を集計して人間向けレポートを出力。
    - デフォルト閾値（稼働率 99% 等）と Pass/Fail 判定ロジックを採用。
    - コマンドライン引数 --from / --to / --db をサポート。
    - P95 計算、NULL 考慮や SQLite の OperationalError に対するフォールバックを実装。

### Changed
- （新規リリースのため該当なし）

### Fixed / Robustness
- 環境変数の検証強化
  - MONITOR_POLL_INTERVAL が無効値（非整数・0以下）の場合は警告してデフォルトにフォールバックするように実装（run_monitoring）。
  - PAPER_FILL_MODE 等の限定文字列は不正値時に明示的にエラーを出すように実装（config.Settings）。
- DB/リソース管理
  - run_* スクリプトで DuckDB / SQLite コネクションを finally ブロックで確実にクローズするようにしている。
- フェイルセーフとログ
  - monitoring ループ内で check_once() の例外をキャッチしてログに記録後に再試行（ループ継続）する実装。
  - process_priority / cpu_affinity の権限不足や未対応環境時に警告して処理を続行するフェイルセーフ。
- 数値処理の落とし穴に対する配慮
  - rank() 関数で浮動小数の丸め（round(..., 12)）を行い ties 判定の誤差を抑制。
  - position_sizing のスケーリングで lot_size 単位での端数処理と残余配分ロジックを実装。

### Notes / Known issues / TODO
- position_sizing:
  - 現状は全銘柄共通の lot_size を想定。将来的に銘柄別 lot_map をサポートする旨の TODO コメントあり。
  - apply_sector_cap では price_map に欠損（0.0）があるとエクスポージャーが過小見積もりされる可能性があり、将来的に前日終値等のフォールバックを検討。
- DuckDB 側での制約:
  - news_nlp の執筆では executemany 前に params が空でないことを確認する注意書き（DuckDB 0.10 の制約）あり。
- news_nlp:
  - OpenAI API キーが未設定の場合は ValueError を送出。実行環境での設定が必要。
  - API 呼び出しの失敗時は部分的にスコア取得できないケースがあり得るが、既存スコアは保護される設計。
- 自動 .env ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により明示的に無効化可能）。

### Migration / Upgrade notes
- KABUSYS_ENV により DB パス / broker の挙動が変わります（paper_trading は paper DB に切替）。
- 運用時は MONITOR_POLL_INTERVAL / PAPER_FILL_MODE / 各種閾値（CPU/MEM/DISK）等を環境変数で設定してください。
- OpenAI を利用する機能（news_nlp）を使う場合は OPENAI_API_KEY を環境変数または関数引数で提供してください。

---

変更点について不明な点や、実際のコミット粒度に合わせた細かい Changelog を作成したい場合は、コミットログやブランチ差分を提示してください。