CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式で記載しています。
日付とバージョンはソースコードの内容から推測して作成しています。

[Unreleased]
------------

- ドキュメントや小さな改善は今後ここに記載されます。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本機能の初期実装を追加。
  - パッケージバージョンを設定 (src/kabusys/__init__.py: __version__ = "0.1.0")。
- 起動スクリプト / デーモン的コンポーネントを追加。
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動するためのエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する仕組みを実装。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（MockBrokerClient の利用を想定）。
    - 実行中の PID を data/execution.pid に記録し、data/stop_requested.flag による停止制御をサポート。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用（設計上の意図）。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了。
- 設定管理と操作用 CLI を追加。
  - 設定読み込み/検証:
    - src/kabusys/config.py
      - .env 自動ロード（プロジェクトルート検出 .git / pyproject.toml 基準）。
      - 環境変数取得ラッパ（Settings クラス）を提供。各種設定（DB パス、API トークン、監視閾値など）をプロパティで取得。
      - PAPER_FILL_MODE の検証、KABUSYS_ENV や LOG_LEVEL のバリデーションを実装。
  - 設定ウィザード CLI: src/kabusys/config_setup.py
    - 対話式に .env を作成・更新するウィザードを実装。
    - .env の読み書き、シークレット表示、既存値の再利用などをサポート。
  - 設定検証 CLI: src/kabusys/validate_config.py
    - 必須環境変数やパス、config/*.yaml の存在/パースを検査。
    - --strict オプションで警告をエラー扱いにできる。
    - 本番（KABUSYS_ENV=live）向けのガードチェックを実装（LINE 通知設定、KILL_FLAG_CLEAR_ON_START 警告等）。
- ポートフォリオ構築用の純粋関数群を追加（DB 非依存）。
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等重み calc_equal_weights、スコア重み calc_score_weights を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算 calc_position_sizes。
    - 単元株丸め（lot_size）、1銘柄上限・aggregate cap（available_cash 超過時のスケールダウン）、cost_buffer を考慮した保守的見積りを実装。
  - これらをパッケージエクスポート (src/kabusys/portfolio/__init__.py)。
- ユーティリティ群を追加。
  - ロギング設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - stdout 出力用 StreamHandler（stdout 使用）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。
    - ログディレクトリ作成の失敗はファイルハンドラ無効化でフォールバック。
    - LOG_LEVEL / LOG_DIR の解決ロジックを実装。
  - プロセス優先度・CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収して set_process_priority/set_cpu_affinity を提供。
    - psutil を利用しつつ権限不足や未対応環境では警告でスキップする堅牢設計。
- 監視・モニタリング基盤関連を追加。
  - 監視用 DB 初期化フック参照（init_monitoring_db を各スクリプトで呼び出す）。
  - SystemMonitor 呼び出し（run_monitoring）が例外をハンドリングしてポーリングを継続する挙動を採用。
- Paper Trading 向け検証ツールを追加。
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計・メトリクスを抽出してレポートを標準出力に表示。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）、リスク却下数などを評価し、PASS/FAIL 判定ロジックを実装。
    - CLI 引数 --from/--to/--db をサポート。
- 研究向けファクター計算モジュールの骨組みを追加。
  - src/kabusys/research/factor_research.py
    - モメンタム・ボラティリティ等の計算方針と定数を実装済み（DuckDB 接続を受け取る設計）。ファイルは途中まで実装。

Changed
- なし（初期リリースにつき新規追加が中心）。

Fixed
- なし（初期リリースにつきバグ修正履歴なし）。

Notes / 実装上の注意（ドキュメント代わり）
- .env 自動ロードはデフォルトで有効。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- run_execution は paper_trading モードでは paper_sqlite_path を使用し、モード分離を保証する設計。
- run_monitoring は MONITOR_POLL_INTERVAL に不正値が設定された場合、デフォルト 60 秒へフォールバックして警告を出力する。
- calc_position_sizes のスケールダウンロジックや lot_size の扱いは注意深く設計されているが、将来的に銘柄ごとの lot_size サポートや価格フォールバック（前日終値など）の追加が予定される旨をコード中に注記している。

今後の課題（今後の変更候補）
- research/factor_research.py の未完部分の実装完了（ファクター計算の SQL 実装など）。
- ブローカー実装（Mock と実ブローカー）の詳細なテストとドキュメント化。
- config/*.yaml のサンプル生成スクリプトや設定のより厳密な検証ロジック。
- 単体テスト・統合テストの追加（特に position sizing / risk adjustment ロジック）。
- 単位や境界条件を保証するための追加のバリデーション（価格欠損時のフォールバック等）。

ライセンス / 配布
- この CHANGELOG はコードベースから推測して作成した要約です。詳細は各ソースファイル内の docstring / コメントを参照してください。