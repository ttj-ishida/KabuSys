KEEP A CHANGELOG 準拠の CHANGELOG.md を以下に作成しました。リポジトリ内のソースコード内容から推測して記載しています。

Changelog — Keep a Changelog
https://keepachangelog.com/ja/1.0.0/

Unreleased
- (なし)

v0.1.0 - 2026-04-12
Added
- 基本アプリケーションの初期機能を追加。
  - パッケージ情報:
    - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - 実行エントリ:
    - run_execution（src/kabusys/run_execution.py）
      - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を高く設定（set_process_priority("high")）。
      - 環境に応じて本番 DB と paper_trading 専用 DB を切り替え（KABUSYS_ENV により paper_trading 時は data/paper_trading.db を使用）。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine.run_session() を実行。
      - duckdb と sqlite3 両方の接続を使用。
    - run_monitoring（src/kabusys/run_monitoring.py）
      - SystemMonitor のポーリングループ起動スクリプトを追加。起動時にプロセス優先度を高く設定。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様。
  - 設定管理（src/kabusys/config.py）
    - .env 自動読み込み機構を実装（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env / .env.local の読み込み順・上書きルールを実装（OS 環境変数を保護）。
    - 環境変数パース関数を実装（export プレフィックス、クォート、インラインコメント等に対応）。
    - Settings クラスを実装し、多数のプロパティを提供:
      - J-Quants / kabu API のトークン/パスワード・URL
      - データベースパス (DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH)
      - 監視関連パス (PID_FILE_PATH, KILL_FLAG_PATH) としきい値 (CPU/MEMORY/DISK)
      - PAPER_FILL_MODE の検証（"instant" | "partial" | "never" | "reject"）および KABUSYS_ENV 検証（development, paper_trading, live）
      - ログレベル検証 (LOG_LEVEL)
  - ポートフォリオ構築モジュール（src/kabusys/portfolio/）
    - portfolio_builder:
      - シグナルの候補選定 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
      - 等金額配分 calc_equal_weights。
      - スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
    - risk_adjustment:
      - apply_sector_cap によるセクター集中上限チェック（既存保有の時価を計算して候補を除外、"unknown" セクターは除外対象外）。
      - calc_regime_multiplier によるレジーム別乗数（"bull":1.0, "neutral":0.7, "bear":0.3、未知は 1.0 でフォールバック）。
    - position_sizing:
      - calc_position_sizes により株数決定を実装（allocation_method="risk_based"/"equal"/"score" をサポート）。
      - 単元株 (lot_size)、max_position_pct、max_utilization、cost_buffer による上限および aggregate cap（スケーリングと端数処理）を実装。
  - リサーチモジュール（src/kabusys/research/）
    - factor_research:
      - calc_momentum（1/3/6 ヶ月リターン、MA200 乖離）。
      - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）。
      - calc_value（PER, ROE：raw_financials と prices_daily を結合）。
      - DuckDB を用いた SQL ベースの実装、欠損時の None 処理。
    - feature_exploration:
      - calc_forward_returns（horizons の将来リターンを一括 SQL で取得。horizons の入力検証あり）。
      - calc_ic（Spearman のランク相関に基づく IC。レコード不足時は None を返す）。
      - factor_summary（count/mean/std/min/max/median を計算）。
      - rank ユーティリティ（同順位は平均ランク）。
    - research パッケージの公開 API を整理（zscore_normalize を kabusys.data.stats から再公開）。
  - AI ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news を OpenAI (gpt-4o-mini) でセンチメント分析し ai_scores に書き込むワークフローを実装。
    - 処理:
      - ニュース収集ウィンドウ計算（JST -> UTC 変換で前日 15:00 ～ 当日 08:30 相当）。
      - 銘柄毎に記事を集約（記事数・文字数に上限を設けてトリム）。
      - 最大 20 銘柄ずつバッチ送信（JSON Mode を期待）。
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフリトライ（上限 _MAX_RETRIES）。
      - レスポンス検証、スコアを ±1.0 にクリップ。
      - 部分成功時は該当銘柄のみを差し替える形で ai_scores を更新（部分失敗で他銘柄の既存スコアを保護）。
    - OpenAI API キーの解決ロジックと未設定時の ValueError を実装。
  - ユーティリティ（src/kabusys/utils/）
    - process_priority:
      - set_process_priority(level) で Windows / POSIX (Linux, Darwin, FreeBSD) を吸収してプロセス優先度を設定。権限不足や未対応 OS の場合は警告を出してスキップ。
      - set_cpu_affinity(cpu_count) を実装（None で無効、負値検証、権限不足は警告してスキップ）。
  - ツール（src/kabusys/tools/paper_verification_report.py）
    - Paper Trading 検証レポート生成ツールを追加。コマンドライン引数 (--from, --to, --db) に対応。
    - 検証指標:
      - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等。
      - 判定閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 <=200 ms）。
    - DB の存在チェック、OperationalError 発生時の保護コード、出力フォーマットを用意。
  - DB 初期化ユーティリティ:
    - init_monitoring_db を呼び出して監視関連テーブル存在を保証（冪等）。

Changed
- （新規リリースのためなし）

Fixed
- （新規リリースのためなし）

Notes / Implementation details / Caveats
- .env 自動ロードはプロジェクトルートが検出できない場合や環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されている場合はスキップされる。
- Settings の複数プロパティは入力値検証を行い、不正値時に ValueError を送出する（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等）。
- position_sizing では price が欠損（0.0）だと conservative にスキップする旨のログと TODO コメントが残されている。
- news_nlp は OpenAI への外部 API 呼び出しを伴うため、API キー未設定や API 側のエラー発生時の挙動に注意が必要（設計上はフェイルセーフで継続する実装）。
- 実行スクリプトは起動時にプロセス優先度変更を試みるが、権限がなければ警告ログを出して続行する。

今後の推奨改善点（参考）
- position_sizing: 銘柄別 lot_size をマスタで持たせる設計への拡張。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値など）を導入して過小評価を防止。
- ニュース NLP: レスポンスバリデーション/回復ロジックの追加強化（schema 変化等に対する堅牢化）。
- テスト: 各モジュール（特に DuckDB を使うリサーチ関数、AI 呼び出し箇所）に対するユニット/統合テスト整備。

もし特定のコミット単位やより細かい変更差分（例: 機能ごとの細分化や既存バージョンとの比較）での記載を希望される場合、対象のコミット履歴や過去の CHANGELOG を提供してください。