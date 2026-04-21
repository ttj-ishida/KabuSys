# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
以下のエントリは、提示されたコードベースの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]
- ドキュメントやテストに基づく微小な改善・補足を想定。
- ロギングや環境変数まわりのメッセージ改善、エラーハンドリングの向上などの小さな修正が含まれる可能性があります。

---

## [0.1.0] - YYYY-MM-DD
初回リリース（コードベースから推測した主要機能セット）。

### 追加
- 全体
  - KabuSys 初版リリース。日本株自動売買システムの基礎モジュール群を提供。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行・監視
  - run_execution: ExecutionEngine を起動するエントリポイントを提供。バックグラウンドスレッドでエンジンを起動・監視し、停止フラグ（data/execution.pid / data/stop_requested.flag）に応じた安全な停止をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト60秒）。停止フラグでのループ終了、例外発生時のログ記録と継続動作を実装。
  - Monitoring と Execution の DB 接続は DuckDB / SQLite を使用。Paper Trading 環境時は発注系 DB を本番と分離（`data/paper_trading.db` デフォルト）。

- 設定・検証
  - config.py: 環境変数とアプリ設定を管理する Settings クラスを実装。自動 .env ロード（プロジェクトルート検出: .git or pyproject.toml）機能を備える。入力値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - config_setup.py: 対話式ウィザードで `.env` を生成・更新する CLI を提供。シークレット入力、デフォルト選択肢、保存確認などを実装。
  - validate_config.py: .env および config/*.yaml の設定検証 CLI を提供。必須環境変数チェック、パス存在チェック、YAML パースチェック（PyYAML が存在する場合）や本番環境用ガード（LINE トークン未設定など）を実装。`--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティ。コンソール（stdout）と日次ローテーションされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: Windows / POSIX を吸収したプロセス優先度設定、CPU affinity 設定ユーティリティ。権限不足時や未対応 OS では警告を出してスキップする安全実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順 + signal_rank タイブレークで選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。スコア合計がゼロの場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限を適用して候補をフィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームはフォールバックで 1.0。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて株数を算出。単元株（lot_size）で丸め、個別上限・全体上限（aggregate cap）によりスケーリングするロジックを実装。スリッページ / 手数料見積り用の cost_buffer をサポート。

- 研究モジュール
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算の骨格を追加（モメンタム・MA・ATR・ボラティリティ等の計算方針と定数を定義）。（実装の一部が切れているため継続実装が必要）

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加。稼働率、注文成功率（Fill / Send）、リスク却下数、レイテンシ（平均・最大・P95）を計算し、PASS/FAIL 判定を行う。P95 算出、期間フィルタ、DB 存在チェック、出力フォーマットを実装。
  - tools/__init__.py: ツールパッケージを追加。

- その他
  - monitoring/monitoring_db.py, monitoring/system_monitor.py, execution/*, data/* 等（コード参照のための各種モジュールを想定）と連携する設計。

### 変更（設計上の明記）
- 環境変数自動ロード
  - `.env` と `.env.local` の読み込み順序を定義（OS 環境 > .env.local > .env）。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。

- DB 分離ポリシー
  - Paper Trading 環境では SQLite DB を本番と明確に分離（`PAPER_TRADING_SQLITE_PATH` または Settings.paper_sqlite_path）。監視テーブルは起動時に冪等に初期化（init_monitoring_db）することで、監視関連の依存を保証。

- ログおよび例外ハンドリング方針
  - 例外発生時は logger.exception で詳細ログ出力し、ループ/スレッドは継続・安全停止を行う方針。

### 修正（バグ修正・堅牢化）
- run_monitoring: 環境変数 MONITOR_POLL_INTERVAL の値が正しくない場合（非整数・0 以下）はデフォルト（60秒）にフォールバックして警告を出力するように堅牢化。
- logging_setup: ログディレクトリ作成に失敗した場合にファイルハンドラの作成をスキップしてコンソール出力を継続する耐障害性を実装。
- process_priority / set_cpu_affinity: 権限不足や未サポート環境での例外を捕捉して警告を出すように変更（起動失敗を避ける）。

### 既知の制限 / 注意点（Breaking-like）
- Settings.* の値検証は厳密であり、不正な環境変数値（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）は ValueError を送出するため、デプロイ前に validate_config を実行して事前確認が必要。
- research/factor_research.py の実装が一部（末尾）で切れているため、完全なファクター計算は追加実装が必要。
- ポジション算出・価格取得において価格が欠損（0.0）だとエクスポージャーが過小評価される旨の TODO（将来的にフォールバック価格の採用を検討）が記載されている。

---

開発者向けメモ:
- 実行時はまず `python -m kabusys.config_setup` で `.env` を生成し、`python -m kabusys.validate_config` で検証することを推奨します。
- Paper Trading を利用する場合は `KABUSYS_ENV=paper_trading` を設定すると mock ブローカークライアントと `data/paper_trading.db` が使用され、本番 DB と分離されます。
- ログはデフォルトで `logs/` に日次ローテートで出力されます。権限やディレクトリ作成の問題が発生した場合はコンソール出力へフォールバックします。

（注）上記 CHANGELOG は提示されたソースコードの内容から推測して作成したものです。実際のコミット履歴とは差異がある可能性があります。必要に応じてリリース日や詳細な変更点を実際のコミット履歴に合わせて更新してください。