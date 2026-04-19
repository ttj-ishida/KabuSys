CHANGELOG
=========
すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-19
-----------------
初期リリース。KabuSys の基本的な実行／監視／ポートフォリオ構築／ユーティリティ群を導入します。

Added
- 基本パッケージ情報を追加
  - src/kabusys/__init__.py: バージョンを "0.1.0" に設定し、主要サブパッケージをエクスポート。

- 環境設定・読み込み
  - src/kabusys/config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - 高機能な .env パーサを実装（export プレフィックス、クォート／エスケープ、インラインコメント処理対応）。
    - Settings クラスを導入し、各種環境変数（J-Quants / kabu / DB /監視閾値 /実行環境 等）をプロパティとして取得・バリデーション。
    - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

  - src/kabusys/config_setup.py:
    - 対話式ウィザードで .env を作成／更新する CLI を追加。
    - 出力時にテンプレートヘッダを付与し、Gitコミットしない旨を明示。

  - src/kabusys/validate_config.py:
    - 起動前に必須環境変数や config/*.yaml の存在・パースをチェックする検証 CLI を追加。
    - --strict オプションで警告も失敗扱いにできる。

- 実行エンジン（Execution）
  - src/kabusys/run_execution.py:
    - ExecutionEngine を起動するエントリスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成（paper_trading では MockBrokerClient を利用する設計）。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を構築。
    - 実行はデーモンスレッドで行い、data/stop_requested.flag による停止制御、PID ファイル出力をサポート。
    - リスク用デフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker_errors 等）を設定。

- 監視（Monitoring）
  - src/kabusys/run_monitoring.py:
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の初期化を行う）。
    - 停止フラグ（data/stop_requested.flag）検出、例外発生時のロギングと継続動作を実装。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py:
    - 候補選定 select_candidates（スコア降順、タイブレークで signal_rank）。
    - 等配分・スコア加重の重み計算 calc_equal_weights / calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。

  - src/kabusys/portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap（既存保有比率に基づく候補フィルタ）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームは警告して 1.0 にフォールバック）。

  - src/kabusys/portfolio/position_sizing.py:
    - 株数決定 calc_position_sizes（allocation_method = "risk_based" | "equal" | "score" をサポート）。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（利用可能現金）によるスケーリング、cost_buffer による保守的コスト見積りを実装。
    - スケーリング時は残差処理で再配分を試みる（再現性のあるソート順での割り当て）。

  - src/kabusys/portfolio/__init__.py:
    - 上記機能をパッケージとして公開。

- リサーチ（factor 計算）
  - src/kabusys/research/factor_research.py:
    - Momentum 等のファクター計算モジュールの骨格を追加（DuckDB 接続を受ける設計、モメンタム等の定数設定）。
    - prices_daily / raw_financials を用いた計算方針をドキュメント化（完全実装は継続作業の位置づけ）。

- ユーティリティ
  - src/kabusys/utils/logging_setup.py:
    - 統一的なログ設定ユーティリティを追加。
    - StreamHandler を stdout に出力（cron 等で stdout/stderr を一本化する運用を想定）。
    - TimedRotatingFileHandler による日次ローテーション（30 日保持）をサポート。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ有効にする。
    - ログレベル／ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。

  - src/kabusys/utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度（Windows の優先度クラス / POSIX の nice 値）を設定するユーティリティを追加。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装（権限不足等は警告してスキップ）。

- 監査・レポートツール
  - src/kabusys/tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算し、閾値（稼働率 99%、fill 90% 等）をもとに PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と DB パス引数（--db または環境変数）をサポート。

- DB 初期化
  - run_execution/run_monitoring から監視用テーブル確保のため init_monitoring_db 呼び出しを追加（冪等に DB を初期化）。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / Known issues
- .env ファイルは機密情報（トークン／パスワード）を含むため .env を絶対にリポジトリにコミットしない旨をドキュメントに明記。
- process_priority / set_cpu_affinity は権限不足や一部 OS で失敗する可能性があり、その場合は警告を出して処理を継続する実装となっている。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャーを過少に見積もる可能性があり、将来的にフォールバック価格の導入を検討（TODO コメントあり）。
- factor_research モジュールは設計・定数を含んだ骨格実装。完全な計算ロジックの拡張が残っている個所がある。
- Logging のファイルハンドラ作成やログディレクトリ作成に失敗した場合、ログはコンソールのみにフォールバックする。

Authors
- KabuSys 開発チーム（コードベースの実装から推測して作成）

License
- プロジェクト内に明示的なライセンス表記が無い場合は注意してください（.env 等に関する注意を再掲）。

(注) 本 CHANGELOG は、提示されたソースコードの内容から推測して作成しています。具体的なリリース手順や日付、著者情報は実際のプロジェクト運用に合わせて調整してください。