# Changelog

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の慣例に準拠しています。  

リリース日付はコードベースの推定に基づきます。

## [0.1.0] - 2026-04-17

### Added
- 初回リリース: KabuSys のコア機能群を追加
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
- 実行・監視用スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御に `data/stop_requested.flag` を使用（存在検知でセッション停止）。
    - ExecutionEngine 起動前に `init_monitoring_db` を呼び出し、監視テーブルの存在を保証（冪等）。
    - デフォルトの RiskManager 設定（例: max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10 等）を組み込んだ初期構成。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）。不正な値はログ警告のうえデフォルトにフォールバック。
    - monitoring は KABUSYS_ENV に関わらず本番用の `sqlite_path` を使用する（監視は本番データを参照する設計）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ `data/stop_requested.flag` の存在でループを終了。
- 設定管理
  - `src/kabusys/config.py`
    - 環境変数 / .env 自動読み込み機構を実装（プロジェクトルートを `.git` または `pyproject.toml` で探索）。
    - `.env`、`.env.local` の読み込み順序と上書きルールを実装。OS 環境変数は保護される（protected）。
    - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト等で使用）。
    - `.env` の行パーサ `_parse_env_line` を実装（`export ` 接頭辞、シングル/ダブルクォートとエスケープ、インラインコメント処理に対応）。
    - 各種設定プロパティを追加: DuckDB/SQLite パス、PID / kill flag パス、監視閾値（CPU/MEM/DISK）、ログレベル、環境種別（development/paper_trading/live）など。
    - Paper Trading 固有設定: `paper_fill_mode`（有効値: `"instant"|"partial"|"never"|"reject"`）、`paper_sqlite_path`。
    - 必須環境変数未設定時は `_require()` により ValueError を送出。
- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading の検証レポートを生成する CLI ツールを追加。
    - 指定期間（--from / --to）で system_status / trade_logs / risk_logs を集計し、稼働率・注文成功率・送信率・P95 レイテンシ等を表示。
    - 合格基準（定数）を導入: 稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms。
    - DB パスは `--db` > 環境変数 `PAPER_TRADING_SQLITE_PATH` > デフォルト `data/paper_trading.db` の優先順で解決。
- ポートフォリオ構築（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全銘柄のスコアが 0 の場合は等配分にフォールバックし警告ログを出力）。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中を防ぐ `apply_sector_cap`（既存保有エクスポージャーに基づき、上限超のセクターの新規候補を除外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知レジームは警告して 1.0 でフォールバック）。
    - 未知セクター ("unknown") はセクター上限の対象外（除外しない）。
  - `src/kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 `calc_position_sizes`（allocation_method: "risk_based" | "equal" | "score"）。
    - risk_based: 損切り率・許容リスク率から個別株数を算出。
    - equal/score: ウェイト・max_utilization に基づく割当。
    - 単元株（lot_size）で丸め、aggregate cap（利用可能現金を超える場合）で縮小・再配分（端数補正ロジック含む）。
    - price 欠損時のスキップ、価格 <= 0 の安全弁を実装。
- 研究・リサーチ
  - `src/kabusys/research/factor_research.py`
    - モメンタム、ボラティリティ、バリュー系ファクターの計算関数を追加（DuckDB 接続を受ける）。
    - mom_1m/3m/6m、MA200 乖離、ATR20、相対ATR、20日平均売買代金、出来高変化率、PER/ROE 等を計算。
    - データ不足時は None を返す設計。
  - `src/kabusys/research/feature_exploration.py`
    - 将来リターン計算（horizons: デフォルト [1,5,21]）と IC（スピアマン）計算、ファクターの統計サマリーを追加。
    - 外部依存を持たず標準ライブラリのみで実装。
  - `src/kabusys/research/__init__.py` で必要関数を公開。
- AI ニュース NLP（初期実装）
  - `src/kabusys/ai/news_nlp.py`
    - raw_news を OpenAI（`gpt-4o-mini`）へ送信して銘柄別センチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む想定のモジュールを追加。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）、トリム（最大記事数・文字数）やリトライ（429/5xx/ネットワーク）など堅牢化を意識した設計。
    - `calc_news_window`（JST の前日 15:00 ～ 当日 08:30 を UTC に変換）と `score_news` の API キー解決ロジックを実装。
    - NOTE: ファイルの末尾が途中で切れている（実装が未完／途中であることを示唆）。完全実装時は DB から記事集約、OpenAI 呼び出し、受信データの検証、部分置換（DELETE+INSERT）などを行う想定。
- ユーティリティ
  - `src/kabusys/utils/process_priority.py`
    - プロセス優先度設定ユーティリティを追加（Windows と POSIX を吸収）。
    - `set_process_priority(level: "high"|"normal"|"low")`、`set_cpu_affinity(cpu_count: int | None)` を提供。
    - 権限不足や未対応 OS の場合は警告ログを出しフォールバック。
- パッケージ初期化
  - `src/kabusys/__init__.py` と各サブパッケージ __init__ を追加し、エクスポートを整理。

### Changed
- 設計上の決定・挙動の明確化
  - 監視プロセスは常に「本番」SQLite パス（Settings.sqlite_path）を使用するように明記（run_monitoring の設計方針）。
  - Execution は paper_trading 環境で紙トレード専用 DB を使用し、本番 DB とデータ分離を行う設計。
  - .env 読み込みにおいて、OS 環境変数は保護され上書きされない（`.env.local` による強制上書きも OS 環境変数を保護）。
  - .env パーサは quoted value とエスケープ、インラインコメントに細かく対応（より堅牢な .env パース）。
  - research / portfolio モジュールはすべて純粋関数（副作用なし、DB 参照は明示）として設計。

### Fixed
- （初期リリースのため該当なし。将来のリリースでログや閾値の調整を行う予定。）

### Known issues / TODO
- `src/kabusys/ai/news_nlp.py` の実装がファイル末尾で途中になっており、記事集約部分以降が未完（スクリプトは現在完全な動作をするとは限らない）。API 呼び出し→DB 書き込みのフローは設計済みだが、実装完了が必要。
- position_sizing: price が欠損（0.0）の場合にエクスポージャーが過少見積りされブロックが外れる可能性があり、将来的に前日終値や取得原価をフォールバック価格として使用する案を TODO として記載。
- CPU affinity の設定は環境により権限や実装差分で失敗する場合があり、その場合はログ出力のうえスキップされる。

### Migration notes
- テスト環境／CI 等で `.env` 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading を用いる場合は `KABUSYS_ENV=paper_trading` を設定し、必要に応じて `PAPER_TRADING_SQLITE_PATH` / `PAPER_FILL_MODE` を設定してください。
- OpenAI を使う機能（news_nlp）は API キーが必須（`OPENAI_API_KEY` 環境変数または関数引数）。未設定だと例外になりますが、現状モジュールは未完のため注意してください。
- 監視ループを手動停止する場合はリポジトリルートの `data/stop_requested.flag` ファイルを作成してください。

---

（注）本 CHANGELOG は提供されたコード内容から仕様・設計意図を推測して作成しています。実際の変更履歴やリリースノートと差異がある可能性があります。必要であれば、実際のコミット履歴やリリースノートに合わせて修正してください。