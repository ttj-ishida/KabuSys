Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠しています。  

v0.1.0 - 2026-04-21
-------------------

Added
- 基本アプリケーションを初回リリースとして追加。
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`。

- 設定・環境変数周り
  - Settings クラスによる環境変数ラップを実装（src/kabusys/config.py）。
    - 必須/任意の設定（J-Quants, kabuステーション, DB パスなど）をプロパティで提供。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証（許容値チェック）を実施。
    - Paper Trading 用の設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH）をサポート。
  - .env ファイル自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を読み込む。
    - OS 環境変数を保護しつつ .env.local で上書き可能。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。
  - .env パースの堅牢化（引用符、エスケープ、export プレフィックス、コメントルール対応）。

- 設定関連 CLI
  - 対話式ウィザードで .env を作成/更新する `kabusys.config_setup` を追加（src/kabusys/config_setup.py）。
    - よく使う設定項目のテンプレート、シークレット入力のマスク、保存確認機能を提供。
  - 起動前設定検証 CLI `kabusys.validate_config` を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在/パース検証（PyYAML がある場合）などを検査。
    - `--strict` オプションで警告も失敗扱いにできる。

- 実行エンジン & ブローカー
  - ExecutionEngine 起動スクリプト `run_execution.py` を追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて本番 DB と paper_trading DB を分離して使用（paper_trading は `data/paper_trading.db` を既定）。
    - BrokerClientFactory によるブローカークライアント生成をサポート（paper_trading 時は Mock を想定）。
    - エンジン用 PID ファイル管理と停止フラグ（data/stop_requested.flag）監視による安全停止処理。
    - 起動時にプロセス優先度を "high" に設定。
    - duckdb 接続を分析用に併用。

- 監視プロセス
  - SystemMonitor 用起動スクリプト `run_monitoring.py` を追加（src/kabusys/run_monitoring.py）。
    - 環境に関係なく監視用は本番 sqlite_path（`data/monitoring.db`）を使用。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 停止フラグ検知でループを終了。例外時はログ出力して次ポーリングへ継続。
    - duckdb 併用、監視テーブルの初期化処理呼び出し（init_monitoring_db）。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順・同点時の tie-breaker を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
    - セクター別エクスポージャー計算（売却予定銘柄除外）、"unknown" セクターの扱い、レジーム別乗数（bull/neutral/bear のマップ）を実装。
  - 株数決定・リスク制限・単元丸め: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の割当方法サポート。
    - lot_size による丸め、max_position_pct・max_utilization・cost_buffer による上限適用、aggregate cap によるスケーリングと端数配分ロジックを実装。

- ロギング・ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定。
    - LOG_DIR / LOG_LEVEL の解決順や、ハンドラ二重登録の防止（既存ハンドラ削除）に対応。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS を抽象化して優先度（high/normal/low）を設定。
    - CPU affinity を最初 N コアに固定するヘルパーを提供。
    - 設定失敗時は警告を出してスキップ。

- Paper Trading 検証ツール
  - paper_trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）を集計。
    - CLI 引数で期間指定（--from, --to）と DB 指定（--db）をサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` も考慮。
    - Pass/Fail 判定基準（稼働率 99% 以上、注文成功率 90% 以上、送信率 95% 以上、P95 レイテンシ <= 200ms）を実装。

- データ分析基盤との統合
  - DuckDB を分析用に利用（duckdb 接続を各種コンポーネントで受け渡し）。
  - research パッケージの雛形を追加（src/kabusys/research/factor_research.py）。
    - モメンタム / ボラティリティ / バリュー等ファクター計算の設計を含む（関数 calc_momentum の一部含む、DuckDB を用いる設計）。

- その他
  - パッケージ API 結合ファイル（src/kabusys/portfolio/__init__.py）で主要関数を再エクスポート。
  - 多数のドキュメント文字列・使い方コメントを各モジュールに追加（CLI 使用例や設計メモ）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 現時点で特筆すべきセキュリティ修正はなし。
  - 注意点: .env は絶対にリポジトリにコミットしない旨を config_setup のヘッダに明示。

Migration notes / 注意事項
- 初回リリースのため、以下に留意して導入してください。
  - 必須環境変数:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必ず設定してください（validate_config で検出可能）。
  - .env の自動読み込みはデフォルトで有効です。テストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - Paper Trading を実行する場合、DB はデフォルトで `data/paper_trading.db` に分離されます。本番 DB と混同しないよう注意してください。
  - ロギングは既定で logs/ に出力され、日次ローテーション（30日保持）されます。ログディレクトリ作成に失敗した場合はコンソール出力のみとなります。
  - `MONITOR_POLL_INTERVAL` や `PAPER_FILL_MODE` 等の環境変数は入力値の妥当性チェックがあります。値が不正な場合は警告または例外が発生します。

既知の制限
- research/factor_research.py は設計と一部実装を含みますが（calc_momentum の開始部分など）、未完の可能性があります。実運用前に各関数の完全実装とテストを推奨します。
- position_sizing の lot_size は現状全銘柄共通の想定（将来的に銘柄別 lot_map へ拡張予定）。
- apply_sector_cap の価格フォールバックが未実装（price が欠損した場合の扱いがコメントで指摘されている）。

今後の予定（例）
- research モジュールの完成・テスト拡充
- ExecutionEngine / Monitoring のエンドツーエンドテスト追加
- 銘柄別 lot_size や手数料・スリッページモデリングの強化

ご質問・不明点があればお知らせください。