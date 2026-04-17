# Changelog

すべての重要な変更はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新更新日: 2026-04-17

## [Unreleased]

### 追加
- run-time / デプロイ周り
  - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を上書き可能に（デフォルト 60 秒）。不正な値（0 以下や非整数）は安全にデフォルトにフォールバックして警告を出力するようにした（src/kabusys/run_monitoring.py）。
  - 監視プロセスと実行プロセスの停止制御にプロジェクト内の data/stop_requested.flag を使用する仕組みを採用（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
  - 実行エンジン起動時、paper_trading 環境向けに SQLite の記録先を本番 DB と分離（data/paper_trading.db を既定）する挙動を明示（src/kabusys/run_execution.py）。
  - 実行エンジンを別スレッドで起動し、停止フラグで安全に停止できるようにした（src/kabusys/run_execution.py）。
  - 起動時にプロセス優先度を設定するユーティリティを追加/活用（high/normal/low）。Windows / POSIX（Linux/Mac/FreeBSD）で差異を吸収し、失敗時は警告でスキップする（src/kabusys/utils/process_priority.py, 使用箇所: run_* スクリプト）。

- 設定・環境変数読み込み
  - .env 自動読み込みの実装。プロジェクトルートは .git / pyproject.toml を基準に探索し、自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（src/kabusys/config.py）。
  - .env パーサーの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - コメント処理（クォート外の # を考慮）などを実装して現実的な .env を正しく読み込めるようにした（src/kabusys/config.py）。
  - 環境変数保護機構: OS 環境変数を上書きしないよう保護セットを導入（src/kabusys/config.py）。
  - 各種設定プロパティを追加 / バリデーション強化:
    - PAPER_FILL_MODE の値検証（instant/partial/never/reject）を実装。
    - PAPER_TRADING_SQLITE_PATH, DUCKDB_PATH, PID/KILL フラグ等のパスプロパティを提供。
    - CPU/MEMORY/DISK 閾値など監視用設定をプロパティ経由で取得可能に（src/kabusys/config.py）。

- 監視（Monitoring）
  - 監視データベース初期化関数 init_monitoring_db を呼び出して監視用テーブルが存在することを保証する仕様に統一（冪等）（src/kabusys/monitoring/* を利用する箇所）。
  - monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を用いる旨の挙動を明記（src/kabusys/run_monitoring.py）。

- Execution（発注実行系）
  - BrokerClientFactory によるブローカークライアント生成を利用（実運用 / モック切替を容易にするファクトリ）（src/kabusys/run_execution.py）。
  - RiskManager のデフォルト設定を Execution 起動時に明示（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 周りなど）。初期の available_cash を broker.get_available_cash() から取得してリスク計算に用いる（src/kabusys/run_execution.py）。
  - OrderRepository / OrderManager / Reconciler を組み合わせた実行エンジン起動フローを実装（src/kabusys/run_execution.py）。

- ポートフォリオ構築
  - 候補選定/重み付けモジュールを実装（等金額／スコア加重／スコアが全て 0 の場合のフォールバック等）（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限ロジック（apply_sector_cap）を実装（既存保有を除外する sell_codes サポート、unknown セクターは制限を適用しない設計）（src/kabusys/portfolio/risk_adjustment.py）。
  - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear、未知レジームは警告のうえフォールバック）（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイズ計算ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、per-position および aggregate cap、コストバッファによる保守見積り、スケーリング＋端数配分ロジックを実装（src/kabusys/portfolio/position_sizing.py）。

- リサーチ / ファクター計算
  - DuckDB 接続を受け取って動作するファクター計算を実装:
    - モメンタム（1/3/6 か月リターン、MA200 乖離）calc_momentum（欠損時は None）（src/kabusys/research/factor_research.py）。
    - ボラティリティ / 流動性（ATR20、相対ATR、20 日平均売買代金、出来高比率）calc_volatility（NULL 伝播に注意して計算）（src/kabusys/research/factor_research.py）。
    - バリュー（PER, ROE：raw_financials の最新レコードを結合）calc_value（src/kabusys/research/factor_research.py）。
  - 特徴量探索ユーティリティ:
    - 将来リターン計算（複数ホライズン対応、入力整合性チェック）calc_forward_returns。
    - IC（Spearman）の計算、ランク付けユーティリティ（同順位は平均ランク）、統計サマリー（count/mean/std/min/max/median）など（src/kabusys/research/feature_exploration.py）。
  - 研究用 API を __all__ でエクスポートして外部から利用しやすくした（src/kabusys/research/__init__.py）。

- AI / ニュース NLP（下書き・主要実装）
  - raw_news から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装（バッチサイズ、文字数制限、記事数制限、JSON 出力厳格化、スコアクリップ、リトライ戦略等を仕様化）（src/kabusys/ai/news_nlp.py）。
  - ニュース集計ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST に相当する UTC 時間帯）を実装（calc_news_window）。
  - API キーの解決と未設定時のエラー処理を実装。
  - （注）ファイル末尾で処理本文が途中で切れているため、score_news の完全実装は現在進行中。エラー耐性や部分成功時のデータ保護（対象銘柄のみ置換）などは設計に含まれている。

- ツール
  - Paper Trading 用の検証レポート生成スクリプトを提供（コマンドライン: python -m kabusys.tools.paper_verification_report）。稼働率／注文成功率／送信率／レイテンシ（P95）等を集計し PASS/FAIL 判定を行う（しきい値はソース内定義）。DB パスは環境変数または --db オプションで指定可能（src/kabusys/tools/paper_verification_report.py）。

### 変更
- SQLite / DuckDB の利用ポリシーを明確化:
  - 監視は本番 sqlite_path を使用、paper_trading 環境では execution が専用の paper_sqlite_path を使用する（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）。
- ロギング初期化を起動スクリプト側で統一（basicConfig INFO）。
- 一部の関数で入力検証を強化（例: calc_forward_returns の horizons 検証、_get_poll_interval の非正整数ハンドリングなど）。

### 修正
- calc_score_weights: 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックするよう修正し、警告を出力するようにした（src/kabusys/portfolio/portfolio_builder.py）。
- ファクター / 研究関係で NULL 伝播やデータ不足時の扱いを明確化（cnt 判定による None の返却等）（src/kabusys/research/*）。
- _parse_env_line のクォート/エスケープ/コメント処理を改善し、より現実的な .env の記述に耐性を持たせた（src/kabusys/config.py）。
- process_priority の未対応 OS や権限不足時に警告でスキップするように修正（src/kabusys/utils/process_priority.py）。

### 既知の問題
- src/kabusys/ai/news_nlp.py の score_news 実装はファイル末尾で途中になっており、完全な動作確認が必要。現在は API キー解決・ウィンドウ計算・設計（バッチ/リトライ/検証）の骨格が存在するが、最終的な DB 書き込みロジックの一部は未完。
- position_sizing の価格欠損時の挙動について TODO コメントあり（price のフォールバック戦略が未実装）。大きな欠損データがある場合、セクターエクスポージャーやポジション判定が過小評価される可能性がある（src/kabusys/portfolio/*）。

---

## [0.1.0] - 2026-04-17

初回リリース (ベースライン実装)。

### 追加
- 基本パッケージ構造を追加（kabusys パッケージ、サブモジュール: data, strategy, execution, monitoring, portfolio, research, ai, tools, utils）。
- 実行エントリースクリプト:
  - run_execution: ExecutionEngine 起動フロー、Broker クライアント抽象化、OrderManager / OrderRepository / RiskManager / Reconciler の組立て。
  - run_monitoring: SystemMonitor ポーリングループ（デーモン的な監視プロセス）、ポーリング間隔設定、停止フラグ対応。
- 設定管理モジュール（.env 自動読み込み、保護された環境変数取扱、便利プロパティ）。
- ポートフォリオ構築モジュール（候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数）。
- リサーチモジュール（DuckDB を用いたファクター計算: momentum, volatility, value、特徴量探索: 将来リターン、IC、統計サマリー）。
- AI ニュース NLP（初期設計と主要実装を追加。OpenAI を用いた銘柄スコアリングの骨格）。
- ユーティリティ:
  - process_priority (プロセス優先度 & CPU affinity)。
- ツール:
  - paper_verification_report: Paper Trading 用の検証レポート出力ツール。

### 既知の制約
- AI モジュールの完遂部分や一部のフォールバック戦略は今後の改善項目として残す。

---

注: 実装の詳細や API 仕様はソースコード（src/ ディレクトリ）を参照してください。ご要望があれば、特定モジュールの変更履歴やリリースノートをより詳細に作成します。