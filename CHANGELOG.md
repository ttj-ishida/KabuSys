# CHANGELOG

すべての notable な変更を Keep a Changelog (https://keepachangelog.com/ja/) 準拠で記載します。

注: この CHANGELOG は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-19
初回リリース。KabuSys 自動売買フレームワークの基礎となる以下の機能を実装・追加しました。

### 追加 (Added)
- パッケージメタ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV = `paper_trading` のときは MockBrokerClient を使用し、Paper Trading 用 DB (デフォルト `data/paper_trading.db`) を使用して本番 DB と分離する設計。
    - プロセス優先度を起動時に設定（high）し、PID ファイル管理・停止フラグ確認・スレッドでのエンジン実行をサポート。
    - 設定に基づく BrokerClientFactory の生成、OrderRepository、OrderManager、RiskManager、Reconciler の組み立てを行う。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用する（監視は常に本番 DB を見る設計）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。

- 設定管理
  - src/kabusys/config.py:
    - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env と .env.local の優先順、OS 環境変数保護（protected）を実装。
    - .env パース機構を強化（export プレフィックス対応、シングル/ダブルクォート中のバックスラッシュエスケープ、行末コメントの取り扱い）。
    - Settings クラスを実装し、主要な環境変数をプロパティとして提供（必須チェックを行う `_require` を含む）。
    - Paper Trading 関連設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）と監視閾値・パス設定（PID_FILE_PATH, KILL_FLAG_PATH, 閾値系環境変数）を定義。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。

- 設定ユーティリティ / CLI
  - config_setup.py:
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を実装。
    - 項目定義と既存 .env 読み込み、保存機能を提供。`.env` 書き込みテンプレートを含む。
  - validate_config.py:
    - 起動前に .env および config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、YAML の存在とパース検証（PyYAML があれば内容検証）、本番環境用の追加警告を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定する共通ユーティリティを追加。
    - ログレベル/ログディレクトリの解決順序、既存ハンドラのクリア、ディレクトリ作成失敗時のフォールバック挙動を定義。
  - utils/process_priority.py:
    - Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（psutil 利用）。
    - CPU affinity 設定ユーティリティも実装。
    - 権限不足や未対応 OS 時は警告を出して安全にスキップする。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - 候補選択 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコアが全て 0 の場合に等金額フォールバックの仕様を実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有・当日売却予定除外・"unknown" セクターは除外しない等の挙動）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear とデフォルトフォールバック）を追加。
  - portfolio/position_sizing.py:
    - 発注株数計算 calc_position_sizes を追加。リスクベース（risk_based）・equal/score ベースの配分に対応。
    - lot_size（単元）丸め、max_position_pct による per-stock cap、aggregate cap（available_cash を超えた場合のスケーリング）や cost_buffer を考慮した保守的見積り、スケーリング後の残差調整アルゴリズムを実装。

- 研究 / ファクター計算
  - research/factor_research.py:
    - ファクター計算モジュールの骨格を追加（Momentum、Value、Volatility、Liquidity を想定）。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルから計算する設計方針（calc_momentum の開始実装を含む、詳細実装は継続）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポートを生成する CLI ツールを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（P95 を含む）等を SQLite のトレードログ/監視テーブルから集計・判定し、PASS/FAIL を出力する。
    - デフォルト DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。
    - P95 計算、日付フィルタ (--from/--to)、閾値定義が含まれる。

### 変更 (Changed)
- DB 接続ポリシー
  - 監視 (run_monitoring) は環境にかかわらず `Settings.sqlite_path` を参照して本番監視 DB を使用するように明確化。
  - 実行エンジン (run_execution) は `settings.is_paper` に基づき `paper_sqlite_path` を使用する（paper_trading と本番 DB を分離）。

- .env 読み込みルール
  - 自動ロードの対象をプロジェクトルート（.git / pyproject.toml）検出に依存させ、CWD 依存を排除。
  - OS 環境変数は保護され、.env.local による上書きは許容するが OS 環境変数は上書きしない。

### 修正 (Fixed)
- .env パースの堅牢化
  - クォート文字内のバックスラッシュエスケープ処理、コメント判定、`export KEY=val` 形式への対応により従来の単純パーサで発生し得た誤読を軽減。

### ドキュメント / 使い方の追加 (Documentation)
- CLI 使用法の記載を各モジュール先頭 docstring に追加（例: python -m kabusys.config_setup, python -m kabusys.validate_config, python -m kabusys.tools.paper_verification_report）。
- logging_setup の使い方を説明する docstring を追加。

### 既知の制限 / 注意点 (Known issues / Notes)
- process_priority/set_cpu_affinity は psutil の権限制約や OS の未対応差異により期待通りに動作しない場合がある。その場合は警告を出してスキップする設計。
- portfolio.position_sizing の price 欠損（price ≤ 0）の場合、一部ロジックはスキップするため期待通りの配分が行われないことがある（将来的にフォールバック価格導入を検討する旨の TODO コメントあり）。
- research/factor_research.py はファクターの実装を進めるための骨格が含まれているが、一部未完（ファイル末尾が途中）ため完全なファクター出力には追加実装が必要。
- monitoring は常に本番 sqlite_path を使用するため、テスト目的で監視データを分離したい場合は別途設定が必要。

---

もし特定のリリースノートやセクション（例: 既知バグ一覧、移行手順、環境変数リスト）を詳細に追加したい場合は、その旨を教えてください。提供されたコードからさらに詳細（関数毎の仕様や戻り値の例、CLI のサンプル出力など）を追記できます。