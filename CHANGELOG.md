# Changelog

すべての注目すべき変更をここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-04-23
初回公開リリース（推定）。コードベースから推測される主要機能・改善点・修正をまとめています。

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - パッケージ情報: kabusys/__init__.py（バージョン 0.1.0）
- 環境設定・管理
  - Settings クラス（src/kabusys/config.py）を追加。環境変数経由でアプリ設定を一元化。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env パーサーで以下に対応:
    - export プレフィックス
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - コメントの扱い（クォート有無に応じた細かな挙動）
  - 環境自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- 対話式環境設定ウィザード
  - src/kabusys/config_setup.py により .env の初期作成/更新を対話式で支援（デフォルト項目とマスク表示を含む）。
- 設定検証 CLI
  - src/kabusys/validate_config.py: 必須環境変数/パス/設定ファイルの存在や形式を検証。--strict オプションで警告をエラー扱いにできる。
- 実行系（Execution）起動スクリプト
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動ロジック、BrokerClientFactory を利用したブローカー切替（paper_trading の場合は MockBrokerClient を使用し DB を分離）。
    - paper_trading 用 DB を分離（デフォルト: data/paper_trading.db）。
    - PID ファイル管理（data/execution.pid 指定）。
    - 停止フラグ（data/stop_requested.flag）による安全停止機構。
    - 起動時にプロセス優先度を "high" に設定。
- 監視系（Monitoring）起動スクリプト
  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（monitoring テーブル等の冪等初期化）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する方針。
    - 停止フラグ検知によるループ終了。
- ロギングユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - LOG_LEVEL / LOG_DIR / app_name に基づく設定。ログディレクトリ作成に失敗した場合はファイル出力を自動で無効化してフォールバック。
- プロセス優先度 & CPU affinity ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収する set_process_priority(level) 実装（high/normal/low）。
    - set_cpu_affinity(cpu_count) によるプロセスピンニング（安全に例外をハンドリング）。
    - 権限不足や未対応 OS に対する安全なフォールバックとログ出力。
- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等重み・スコア重み計算（calc_equal_weights / calc_score_weights）。
    - スコア全てが 0 の場合に等重みへフォールバックする警告。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有を考慮したセクター別エクスポージャー算出）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear と未知レジームのフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジック（risk_based / equal / score 対応）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）超過時のスケーリングと残差配分アルゴリズム、cost_buffer を考慮した保守的見積り。
- 研究用ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py
    - モメンタム/MA/ATR/出来高等のファクター計算方針と定数を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数のインターフェースを用意（calc_momentum） — 実装は途中（ファイル末尾で切れている）。
- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード SQLite（PAPER_TRADING_SQLITE_PATH）から稼働率・注文成功率・送信率・レイテンシ等を集計してレポートを出力する CLI を追加。
    - P95 計算、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定。
- 依存 DB 初期化ヘルパー呼び出し
  - 監視・実行スクリプトから monitoring DB の初期化関数 init_monitoring_db を呼び出してテーブル存在を保証（冪等処理）。

### 変更 (Changed)
- -（初回リリースのため該当なし）-

### 修正 (Fixed)
- ロギング設定やプロセス優先度設定で発生しうる環境依存の失敗（ディレクトリ作成失敗、権限不足、未サポート OS）の扱いを堅牢化:
  - 失敗時は警告ログを出力して機能を無効化する（アプリの致命的停止を回避）。
- .env 読み込み時の入出力例外を警告に変換し、処理継続するよう改善。
- calc_score_weights において全スコア 0.0 のケースで等金額配分へフォールバック（警告ログ）。

### 廃止 (Deprecated)
- -（初回リリースのため該当なし）-

### 削除 (Removed)
- -（初回リリースのため該当なし）-

### セキュリティ (Security)
- -（特記事項なし）-

---

## 重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先ディレクトリ、デフォルト: logs/）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 を設定すると .env 自動ロードを無効化）

## マイグレーション / 運用上の注意
- run_monitoring は監視用に常に本番の sqlite_path を使用する設計になっているため、ペーパートレード環境で監視を分離したい場合は sqlite_path を明示的に切り替えること。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_trading 用 SQLite を使う（本番 DB と分離）。
- .env は絶対にリポジトリへコミットしないこと（config_setup のヘッダにも注意書きあり）。
- 本番 (KABUSYS_ENV=live) 設定時は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_SWITCH 関連の設定を確認すること。validate_config の --strict モードで事前チェック可能。

---

（注）本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートが存在する場合は、それに合わせて適宜編集してください。