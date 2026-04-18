CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
形式は "Keep a Changelog" に準拠します。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリースを追加。
- コア機能
  - 自動売買システム「KabuSys」の基本モジュール群を実装：
    - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
      - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、Paper Trading 用 DB を分離（data/paper_trading.db）。
      - 実行エンジンをスレッドで起動し、data/stop_requested.flag を監視して安全に停止可能。
      - 実行時 PID ファイルを data/execution.pid に出力。
    - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py
      - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
      - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
      - 停止フラグファイルを検知してループを抜ける仕組みを提供。
    - 設定・環境管理: src/kabusys/config.py
      - .env 自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）と、環境変数アクセス用 Settings クラス（プロパティベース）を提供。
      - 多数の設定プロパティとバリデーション（KABUSYS_ENV、PAPER_FILL_MODE 等）。
    - 設定ウィザード CLI: src/kabusys/config_setup.py
      - 対話式で .env を新規作成 / 更新するウィザードを提供。
    - 設定検証 CLI: src/kabusys/validate_config.py
      - .env と config/*.yaml の存在・形式等を起動前に検査（--strict オプションで警告も失敗扱い）。
    - ロギング設定ユーティリティ: src/kabusys/utils/logging_setup.py
      - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler）を組み合わせた統一ロギングを提供。
      - ログディレクトリ自動作成、失敗時はファイル出力をスキップしてコンソールのみで継続するフォールバックあり。
    - プロセス優先度 / CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
      - Windows / POSIX の差分を吸収して優先度設定を試みる (high/normal/low)。
      - CPU コア数固定（set_cpu_affinity）をサポート、権限不足時は警告してスキップ。
    - ポートフォリオ構築関連（純関数）
      - 銘柄選定 / 重み計算: src/kabusys/portfolio/portfolio_builder.py
        - 候補選定（score 降順、同点は signal_rank でブレーク）、等重み・スコア重みの計算（スコア全て 0 の場合は等重みへフォールバック）。
      - セクター集中制限・レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
        - セクター上限の適用（unknown セクターは除外しない）、レジームに応じた資金乗数（bull/neutral/bear）。
      - 株数決定・リスク制限・単元丸め: src/kabusys/portfolio/position_sizing.py
        - risk_based / equal / score の配分方式実装。lot_size（既定 100）に合わせた丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積り。
    - 研究用ファクター計算（骨格）: src/kabusys/research/factor_research.py
      - モメンタム、移動平均、ATR、出来高などを DuckDB 上の prices_daily / raw_financials を参照して計算する設計。
    - ツール
      - Paper Trading 検証レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py
        - 稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定。閾値を定義してレポート出力。
- 初期パッケージメタ情報: src/kabusys/__init__.py にバージョン 0.1.0 を追加。

Changed
- （初回リリースのため「変更」は実質的になし。設計上の挙動を明記）
  - ログは stdout に出力することをデフォルトとし、cron/Task Scheduler からのリダイレクトを想定。
  - .env 自動読み込みの優先順位を OS 環境変数 > .env.local > .env とし、既存 OS 環境変数を保護する実装。
  - run_execution と run_monitoring は起動時にプロセス優先度を "high" に設定する呼び出しを行う（権限不足時は警告で継続）。
  - run_monitoring は常に Settings.sqlite_path（本番監視 DB）を使用する仕様（KABUSYS_ENV に依存せず）。

Fixed / Robustness improvements
- .env パーサーの強化（src/kabusys/config.py）
  - export KEY=val 形式のサポート、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、スペース前の # をコメント扱いする等を実装。
  - .env 読み込みでファイル IO エラーが発生した場合は警告を出して処理を継続。
  - .env.local を上書きモードで読み込む際に OS 環境変数を上書きしない保護機能を実装。
- ロギング設定でログディレクトリ作成に失敗した場合にコンソール出力のみへ安全にフォールバック。
- run_execution / run_monitoring で使用する DB 初期化（init_monitoring_db）を呼び出し、監視テーブルの存在を保証（冪等）。
- Paper Verification レポート
  - P95 計算を実装し、空データ時には N/A を返すようにした。
  - date 範囲フィルタを ISO8601 UTC 文字列に変換して問い合わせする実装。

Notes / Known behaviors
- 監視 (run_monitoring) は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します。テスト目的で監視 DB を分離したい場合は設定を変更してください。
- 実行 (run_execution) は paper_trading モード時に PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）を使用して本番 DB と分離します。
- MONITOR_POLL_INTERVAL に不正な値（0、負数、非整数）が設定された場合は 60 秒のデフォルトへフォールバックします。ログに警告が出力されます。
- PAPER_FILL_MODE の値は "instant" / "partial" / "never" / "reject" のいずれかでないと起動時に ValueError を送出します。
- position_sizing の aggregate scaling は lot_size 単位で丸めを行い、残余キャッシュを使ってフラクション残差順に追加配分するロジックを持ちます。価格欠損（0.0）によりエクスポージャーが過少見積りされる可能性がある点は TODO コメントで指摘しています。
- risk_adjustment の apply_sector_cap は sector_map に登録のないコードを "unknown" として扱い、unknown のセクターには上限適用を行いません（つまり除外されない）。

Security / Privacy
- .env ファイルの内容は出力テンプレートで明示的にコメントされ、.env を絶対に Git にコミットしない旨を明記しています。
- config_setup のウィザードではシークレット項目をマスクして表示します。

Breaking Changes
- なし（初回公開）

References
- コードベース: src/ 以下の各モジュール実装に基づく記述。