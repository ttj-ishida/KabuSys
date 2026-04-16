# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリース日付はコードベースから推測したものを使用しています。

### [Unreleased]
- 現時点で未リリースの変更はありません（初回リリース: 0.1.0）。

---

### [0.1.0] - 2026-04-16
初回リリース。KabuSys 自動売買フレームワークのコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加・仕様です。

Added
- 基本構成
  - パッケージ初期化とバージョン管理（kabusys.__version__ = "0.1.0"）。
  - 環境変数 / .env 管理モジュール（kabusys.config.Settings）。
    - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - 読み込み順: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサーで export KEY=val、クォート（'"/"）・バックスラッシュエスケープ・インラインコメント処理をサポート。
    - 設定の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
  - DB パス設定プロパティ（duckdb/sqlite/paper_trading 用パス）と監視関連設定（pid/kill flag、閾値など）。

- 実行エンジン / ブローカー周り
  - Execution 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時は専用の PaperTrading SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock を含む想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て、デーモンスレッド実行と停止フラグ監視。
    - RiskConfig 初期値（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）および initial_portfolio_value を broker.get_available_cash() から取得。

- 監視（Monitoring）
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒、0 以下や不正値はデフォルトにフォールバック）。
    - 実行時にはプロセス優先度を "high" に設定。
    - 監視用 DB 初期化（init_monitoring_db）、DuckDB 接続、停止フラグファイル検知によるループ終了、例外発生時のログ出力で継続するフェイルセーフ。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（意図的な設計）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - スコア全てが 0 の場合は等配分へフォールバック（WARNING ログ）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、レジームに基づく投下資金乗数（calc_regime_multiplier）。
    - 不明セクター ("unknown") はセクター上限の対象外。
    - レジーム別乗数: bull=1.0, neutral=0.7, bear=0.3。未知レジームは 1.0 でフォールバック（WARNING）。
  - position_sizing: 株数決定ロジック（risk_based / equal / score）
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケーリング）を実装。
    - コストバッファ（cost_buffer）を用いた保守的見積り、残差に基づく lot 単位での追加配分（再現性のある安定ソート）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB 上の prices_daily から計算。
    - calc_volatility: ATR(20)、相対 ATR、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播制御を含む）。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を算出。
    - 実装は DuckDB SQL を活用した設計で高パフォーマンスを想定。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を用いる）、horizons バリデーション。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（同順位は平均ランク）。
    - factor_summary / rank: 基本統計量とランク付けユーティリティ（外部依存を使わない純粋 Python 実装）。

- AI / ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングの基盤を実装。
    - タイムウィンドウの明確化（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）。
    - 記事集約、1 銘柄あたりの文字数/記事数上限（トークン肥大化対策）。
    - バッチ処理（最大 20 銘柄／API 呼び出し）、JSON Mode 想定出力、429/タイムアウト/5xx の再試行（指数バックオフ）とリトライ上限。
    - レスポンス検証、スコア ±1.0 クリップ、部分的書き換え（対象コードのみ DELETE→INSERT）による耐障害性。
    - API キー解決（引数 / 環境変数 OPENAI_API_KEY）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading DB に対する検証レポート生成 CLI（--from/--to/--db オプション）。
    - 指標: 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）。
    - P95 計算、閾値判定（稼働率 99% など）による PASS/FAIL 判定。
    - DB テーブル欠如時に堅牢に N/A を扱う。

- ユーティリティ
  - process_priority:
    - set_process_priority: Windows/Linux(Mac/FreeBSD) の差分吸収実装（psutil 使用）。権限不足や未対応 OS は警告でスキップ。
    - set_cpu_affinity: 指定コア数へのピン留め（権限/未サポート時は警告でスキップ）。
    - 不正パラメータのバリデーションとログ出力。

Changed
- 初期アーキテクチャ設計として、DB（SQLite / DuckDB）をデータ層に明確に分離。Paper Trading と Live の DB を切り分ける設計。
- 環境ロードの保護機構を導入（OS 環境変数を protected として .env/.env.local の上書きを制御）。

Fixed
- .env パーサーの多岐にわたるケース対応（export 句、クォート内のバックスラッシュエスケープ、コメント扱いの改善）により実運用での読み込み失敗に強くした。
- ポーリング間隔の環境変数値検証（不正値や 0/負値はデフォルトにフォールバック）や check_once() の例外ハンドリング強化（監視ループが落ちないようにするフェイルセーフ）。

Security
- OpenAI API キーの未設定時は明示的にエラーを返す（誤った silent failure を防止）。

Notes / Implementation details
- 多くの関数は副作用を持たない純粋関数（ポートフォリオ構築・リサーチ系）として実装され、テストや再利用を想定。
- DuckDB を主にファクター集計に使用し、SQL ベースで効率よく集計。DuckDB の制約（executemany の空パラメータ等）に配慮した実装注記あり。
- 実行環境の差分（開発 / paper_trading / live）を Settings.env で制御。validation により誤設定を早期に検出。

---

今後の改善候補（コード中の TODO コメントなどから推測）
- position_sizing: 銘柄ごとの lot_size をサポートするため、stocks マスタから lot_map を受け取る設計への拡張。
- apply_sector_cap: 価格が欠損（0.0）時のエクスポージャーフォールバック（前日終値や取得原価の利用）を導入。
- news_nlp: 大量記事時のトークン最適化や追加の入力プリプロセッサ、OpenAI レスポンスのより厳密なスキーマ検証の強化。
- テストカバレッジの拡充（特に SQL クエリ周りと API 再試行ロジック）。

以上が、コードベースの内容から推測して作成した CHANGELOG.md です。必要であれば、各項目をより詳細に分解したり、日付や担当者情報を追加することができます。