CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
フォーマットのセクション: Added, Changed, Fixed, Deprecated, Removed, Security。

[Unreleased]
-------------

- ドキュメント化されている未実装箇所や将来対応予定:
  - portfolio/risk_adjustment.apply_sector_cap における価格欠損時のフォールバック（TODOコメントあり）。
  - position_sizing の将来的な拡張（銘柄ごとの lot_size を持つマスタ導入）。
  - research/factor_research モジュールの一部が未完（ソースが途中で切れている箇所あり）。実装を継続予定。

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース: KabuSys v0.1.0 を追加。
  - パッケージメタデータ: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 実行/監視用エントリポイントを追加:
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用する実行分離の仕組みを導入。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、および ExecutionEngine のスレッド起動／停止制御を実装。
    - data/execution.pid に PID を出力する仕組み（pid_file の取り扱い）および data/stop_requested.flag による外部停止フラグ監視を実装。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する明確化（monitoring 用 DB 初期化）。
    - stop flag（data/stop_requested.flag）検出による安全停止。
- 設定関連ユーティリティと CLI:
  - src/kabusys/config.py
    - .env 自動ロード（.env, .env.local）と OS 環境変数保護の実装。
    - .env パースロジックは export プレフィックス・クォート・コメント処理に対応。
    - 各種設定（DBパス、PID ファイル、閾値、PAPER_FILL_MODE など）を Settings クラスとして提供。環境値の検証ロジック（許容値チェック）を実装。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加（項目定義、既存 .env 読込、秘密値のマスク表示、保存確認など）。
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス親ディレクトリ存在チェック、PyYAML の有無に応じた YAML 検証、KABUSYS_ENV=live 時の追加ガードを実装。
    - --strict オプションで警告を FAIL として扱う機能を追加。
- ポートフォリオ構築用純粋関数群:
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順で候補選択（signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 重み付けロジック（スコア全0時は等分配へフォールバック、ログ警告あり）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外（sell_codes を考慮、"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームで警告して 1.0 フォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method("risk_based", "equal", "score") に基づく発注株数計算、lot_size（単元）丸め、per-position / aggregate cap の実装、cost_buffer を考慮した保守的見積り、キャッシュが不足する場合のスケーリングと余剰配分ロジック（端数処理を実装）。
  - src/kabusys/portfolio/__init__.py に API エクスポートを追加。
- 監視・検証ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成ツールを追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（平均／最大／P95）を算出して人間可読レポートを出力。
    - 閾値を定義 (稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200ms) し PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）、DB パス指定（--db または PAPER_TRADING_SQLITE_PATH）に対応。
- ユーティリティ:
  - src/kabusys/utils/logging_setup.py
    - 統一ログセットアップ関数 setup_logging を追加。
    - stdout への StreamHandler と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーへ設定。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続。
    - LOG_LEVEL / LOG_DIR の解決順および既存ハンドラの安全な再設定を実装。
  - src/kabusys/utils/process_priority.py
    - クロスプラットフォーム（Windows / POSIX）対応のプロセス優先度設定 set_process_priority を追加。psutil の権限エラー等を安全にハンドリング。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装（未指定時は no-op）。
- モニタリング DB 初期化ユーティリティ（参照のみ）
  - run_* スクリプトや実行コンポーネントから init_monitoring_db / SystemMonitor を参照して使用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数や秘密情報の扱いについて:
  - config_setup の .env テンプレートに注意書きを追加（.env を絶対に Git にコミットしない旨を明記）。
  - Settings クラスの必須環境変数取得時に未設定で例外を投げることで、起動時に明確に失敗させる。

Notes / Known issues
- research/factor_research.py の実装が途中で切れている（ファイル末尾が不完全）。ファクター計算モジュールは今後の実装が必要。
- apply_sector_cap の価格欠損時の扱い（現在は price_map に 0.0 があると過少見積りになり得る）について改善予定（前日終値などのフォールバック検討）。
- position_sizing の lot_size は現状グローバル固定（将来は銘柄別の単元情報を導入予定）。
- 一部外部依存（psutil, duckdb, PyYAML 等）が必要。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告する。

以上。今後のリリースでは factor_research の完成、実運用での挙動改善（ログ・例外ハンドリング強化、テスト追加等）を予定しています。