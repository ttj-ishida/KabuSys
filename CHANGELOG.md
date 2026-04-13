# Changelog

すべての変更は Keep a Changelog 準拠の形式で記載しています。  
現在のバージョン: 0.1.0

フォーマット: https://keepachangelog.com/ja/

## [Unreleased]

## [0.1.0] - 初期リリース（初版機能群）
リリース日: 未設定

### Added
- 基本パッケージ情報
  - パッケージメタ情報を src/kabusys/__init__.py に追加（__version__ = "0.1.0"）。

- 設定管理
  - 環境変数 / .env ファイルを扱う Settings クラスを追加（src/kabusys/config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）と .env/.env.local の自動ロード機能を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - 必須環境変数未設定時に明示的なエラーを投げる _require() 実装。
  - 多数の環境設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）、SQLITE_PATH（デフォルト data/monitoring.db）
    - Paper Trading 用 DB: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
    - PAPER_FILL_MODE（instant/partial/never/reject。無効値はエラー）
    - 監視関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証

- 実行・監視スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository/OrderManager/RiskManager/Reconciler を組み立て ExecutionEngine を起動。
    - デフォルトでプロセス優先度を "high" に設定。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視は本番 DB を参照する仕様）。
    - プロセス優先度設定、SQLite / DuckDB 接続、ループ内で monitor.check_once() を周期実行（例外はログ出力して継続）。

- 監視 DB 初期化
  - init_monitoring_db 呼び出しを各エントリポイントで行い、監視テーブルが存在することを保証（冪等）。

- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py を提供。
    - set_process_priority(level: "high" | "normal" | "low")：Windows / POSIX を吸収してプロセス優先度を設定。アクセス権限不足や未対応環境では警告を出力してスキップ。
    - set_cpu_affinity(cpu_count: int | None)：最初の N コアに固定する機能。引数検証と例外ハンドリング実装。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/*
    - portfolio_builder.py
      - select_candidates: スコア降順（同点は signal_rank でタイブレーク）
      - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分にフォールバック）
    - risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（unknown セクターは上限非適用）
      - calc_regime_multiplier: regime に応じた乗数（bull/neutral/bear。未知レジームは警告の上フォールバック）
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づく株数決定、単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer を考慮したスケールダウンアルゴリズムを実装。
    - パブリック API を kabusys.portfolio パッケージでエクスポート。

- 研究・ファクター計算
  - src/kabusys/research/*
    - factor_research.py
      - calc_momentum：1M/3M/6M リターン、MA200乖離を DuckDB SQL で計算（データ不足時は None）。
      - calc_volatility：20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
      - calc_value：raw_financials と prices_daily から PER / ROE（最新報告）を計算。
    - feature_exploration.py
      - calc_forward_returns：指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。
      - calc_ic：Spearman ランク相関（IC）計算の実装（レコード数不足時 None）。
      - factor_summary / rank：統計サマリーやランク変換ユーティリティ。
    - research パッケージで必要な関数をエクスポート。DuckDB 接続を受け取る設計。

- ニュース NLP / OpenAI 連携
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols を集約し、OpenAI API (gpt-4o-mini) にバッチ送信して銘柄単位の ai_score を生成・ai_scores テーブルへ保存する処理を実装。
    - バッチサイズ 20、1銘柄あたり最大記事数/文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）を行う。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ（上限 _MAX_RETRIES）。
    - レスポンスバリデーション（JSON 形式, results キー, code の整合性, score 数値）とスコアの ±1.0 クリップ。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。未設定時は ValueError。

- ツール
  - src/kabusys/tools/paper_verification_report.py：Paper Trading 検証レポート生成スクリプトを追加。
    - CLI から --from / --to / --db を受け取る。
    - デフォルト DB は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数。
    - 判定基準（デフォルト閾値）:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - DB 内のテーブルが存在しない場合の耐性（sqlite3.OperationalError を捕捉して N/A を返す）。

### Changed
- （初回リリースのため「変更」は該当なし）

### Fixed
- （初回リリースのため「修正」は該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キー等の秘密情報は環境変数経由で取り扱う設計。コード中にハードコーディングされた秘密情報は含まれていない。

### Notes / Known limitations / TODOs
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う仕様になっているため、テスト実行時は注意が必要（監視データは本番 DB に記録される可能性あり）。
- calc_position_sizes:
  - price が欠損（0.0）の場合、現在は単純にスキップする。将来的には前日終値や取得原価等のフォールバック価格を検討する旨の TODO がある。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_size をサポートする拡張を想定。
- config._load_env_file の .env パースは多くのケースに対応しているが、極端なエスケープ/クォート構文に対する互換性の詳細検証は必要。
- news_nlp の処理は OpenAI API のレスポンス正確性・料金・レート制限に依存する。API エラー時は一部の銘柄スコアが取得できない可能性があるが、部分成功を保護するために書き込みは対象コードのみ削除→挿入を行う。
- research モジュールは DuckDB のテーブル構成（prices_daily / raw_financials 等）に依存する。データ整備・インポート手順は別途整備が必要。
- process_priority の優先度設定は権限不足（非 root 等）や未対応 OS で失敗する可能性があるが、失敗時は警告を出して処理を続行する。

### Setup / Usage examples
- 環境変数の自動ロード:
  - プロジェクトルートに .env または .env.local を置くと自動的に読み込まれる（既存 OS 環境変数は保護される）。
- 監視起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（デフォルト 60）。不正値は警告の上デフォルトにフォールバック。
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper DB を使用して発注テストが可能。
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で DB パスを直接指定。

---

（以降のリリースでは変更点をバージョンごとに追記してください）