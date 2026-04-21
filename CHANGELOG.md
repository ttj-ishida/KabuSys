# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

現在のパッケージバージョン: 0.1.0

---

## [Unreleased]

（現在の開発中の変更点はここに記載してください）

---

## [0.1.0] - 初回リリース

初期公開リリース。以下の主要機能・ユーティリティを含みます。

### 追加 (Added)
- 実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知で安全に停止。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用して接続。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを実装。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の MockBroker を使用し、専用 SQLite（`data/paper_trading.db` がデフォルト）を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）でセッションを停止、PID ファイル管理。
- 環境/設定管理
  - config.py
    - 環境変数読み込みおよび Settings クラスを実装。アプリケーションで使用する設定値をプロパティとして提供。
    - プロジェクトルート自動検出機能（.git または pyproject.toml を基準）。
    - 自動 .env ロード順序: OS 環境 > .env.local > .env。自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
    - 各種設定の検証（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` など）。
  - config_setup.py（対話型ウィザード）
    - .env の初期作成 / 更新を対話式で支援。
    - シークレット項目はマスク表示して入力可能。既存 .env の読み込み・再利用に対応。
  - validate_config.py（検証 CLI）
    - .env と config/*.yaml の設定検証ツールを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を表示。
- ロギング
  - utils/logging_setup.py
    - ルートロガーを統一して設定するユーティリティ。
    - コンソール出力（stdout）用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて設定。ログフォーマット/日付形式を統一。
    - ログディレクトリ作成失敗時はファイルロギングをスキップして stdout のみで継続。
    - 既存ハンドラの二重登録を防ぐため、設定時に既存ハンドラを flush/close して削除。
- プロセス優先度 / CPU 固定
  - utils/process_priority.py
    - Windows / POSIX を吸収する set_process_priority() を実装（"high"/"normal"/"low"）。
    - set_cpu_affinity() によりプロセスを最初の N コアにピン留め可能。
    - 権限不足や未対応 OS に対しては警告を出し安全にスキップ。
- ポートフォリオ構築関連（純粋関数群、DB参照なし）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates()
    - 等金額配分 calc_equal_weights()
    - スコア加重配分 calc_score_weights()（全銘柄スコアが 0 の場合は等金額配分にフォールバック）
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap()（既存保有のセクター比率が閾値超過時に新規候補を除外）
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier()
  - portfolio/position_sizing.py
    - position sizing ロジック calc_position_sizes()
    - risk_based / equal / score の配分方式をサポート
    - 単元株（lot_size）で丸め、max_position_pct / max_utilization / cost_buffer を考慮
    - aggregate cap 超過時にスケールダウンし、残差は大きい順に lot 単位で再配分するロジックを実装
- Research（ファクター計算）
  - research/factor_research.py
    - Momentum 等のファクター計算を目的としたモジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する設計）。
    - モメンタム等の定数、calc_momentum の実装着手（設計方針と定義を含む）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率(uptime_pct)、注文成功率(fill_rate)、送信率(send_rate)、P95 レイテンシ等を算出し PASS/FAIL を判定。
    - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
- パッケージメタ
  - kabusys/__init__.py にバージョン `0.1.0` を設定。
  - portfolio モジュールのトップレベルエクスポートを整備（select_candidates 等を直接 import できるようにした）。

### 変更 (Changed)
- .env 自動読み込みの挙動
  - OS 環境変数を保護するため、.env 読み込み時に既存の OS 環境変数は上書きされない（.env.local は override=True で上書き可能だが protected により OS 環境は保護）。
- run_monitoring / run_execution のログ設定開始順序
  - 起動時にまず setup_logging() を呼び出すことで統一的なログ取り扱いに変更。
- run_monitoring / run_execution のプロセス優先度設定
  - 起動時に set_process_priority("high") を呼び出すよう変更（CPU リソース確保を優先）。

### 修正 (Fixed)
- .env パーサの改善
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの判定など、現実的な .env の記法に対する堅牢性を向上。
- logging_setup の二重ハンドラ問題を回避
  - 再実行時にハンドラが二重登録される問題を解消するため、既存ハンドラをクリアしてから設定するようにした。
- process_priority の例外ハンドリング強化
  - 権限不足や未実装 API 呼び出しに対してログ警告でスキップするようにしてクラッシュを防止。
- run_monitoring の例外耐性
  - monitor.check_once() で例外が発生してもポーリングループを継続するように例外をキャッチしてログ出力。

### ドキュメント / メッセージ (Documentation)
- 各スクリプトとモジュールに docstring と使用方法を追加（CLI の使い方、環境変数説明、デフォルトパス等）。
- config_setup が生成する .env テンプレートに注意事項（.env を絶対に Git にコミットしない）を明記。

### 既知の制限 / 注意点 (Known issues / Notes)
- research/factor_research.calc_momentum は実装途中（ファイル末尾で切れている部分があり、完全実装は今後の作業）。
- portfolio.position_sizing は現時点で単元株数を全銘柄共通の引数（lot_size）で扱っている。将来的には銘柄別 lot_size をサポートする予定（TODO を注記）。
- apply_sector_cap は price_map に欠損（価格 0.0）がある場合にエクスポージャーが過少見積になる可能性がある旨を TODO として注記。将来的にフォールバック価格を導入する予定。
- 一部機能は外部パッケージに依存（例: duckdb, psutil, PyYAML）。これらが存在しない場合は該当機能が限定的に動作または検証がスキップされる。

---

著者: KabuSys チーム  
初期リリース (0.1.0) — 基盤機能の実装と運用・検証ツールを提供。今後はファクター計算の完全実装、戦略部分の統合、テストカバレッジ強化を予定しています。