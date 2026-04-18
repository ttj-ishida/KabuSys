# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

現在のパッケージバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- 初期リリース。日本株自動売買システム KabuSys の主要モジュール・CLI・ユーティリティを追加。
- 起動スクリプト:
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は KABUSYS_ENV に関わらず本番の sqlite_path を使用する設計。  
    - プロセス優先度を起動時に "high" に設定（utils/process_priority を使用）。  
    - 停止用フラグファイル（data/stop_requested.flag）を検知して安全にループを終了。
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用（Mock）ブローカークライアントを使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録して本番 DB と完全に分離。  
    - ExecutionEngine をデーモンスレッドで起動し、停止フラグで安全に停止。PID ファイルを扱う仕組みを備える。  
    - デフォルトでプロセス優先度 "high" を適用。
- 設定関連:
  - config.py — 環境変数/設定管理クラス `Settings` を追加。  
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）、.env.local が .env を上書き。  
    - 多数のプロパティを提供（J-Quants/JQUANTS_REFRESH_TOKEN、kabu API、DuckDB/SQLite パス、paper trading 用パス、監視閾値、KABUSYS_ENV 判定など）。  
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL のバリデーションを実施。
  - config_setup.py — 対話式 .env ウィザードを追加。  
    - 秘匿項目はマスク表示、既存 .env の読み込みと上書き、.env ファイルへの安全な書き出し（.env を Git にコミットしない旨のヘッダ）を実装。
  - validate_config.py — 起動前設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パス・config/*.yaml の存在確認（PyYAML がない場合はスキップ）や本番用警告など。  
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築ライブラリ (純関数群):
  - portfolio/portfolio_builder.py — 候補選定と等配/スコア加重の重み計算を追加。  
    - 同点時のタイブレーク（signal_rank）などのソートルールを実装。
  - portfolio/risk_adjustment.py — セクター集中抑制（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。  
    - unknown セクターの扱いや、レジームが未知の場合のフォールバック挙動を定義。
  - portfolio/position_sizing.py — 株数決定ロジックを追加。  
    - allocation_method に応じて "risk_based" / "equal" / "score" をサポート。  
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金を超えるとスケーリング）、cost_buffer（手数料/スリッページ見積）を考慮した配分、残差処理による追加配分ロジックを実装。
  - portfolio/__init__.py で上記 API をエクスポート。
- 研究・ファクター計算:
  - research/factor_research.py — DuckDB を用いたファクター計算モジュールを追加。  
    - Momentum（1M/3M/6M/MA200乖離）、Volatility（20日 ATR 等）、流動性指標等を計算。  
    - DuckDB の SQL を用いて、prices_daily テーブルのみ参照する安全な実装。
- ツール:
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等の指標を計算し、PASS/FAIL を判定（閾値はスクリプト内に定義）。  
    - --from / --to / --db オプションを提供。
- ユーティリティ:
  - utils/process_priority.py — プロセス優先度および CPU affinity 設定ユーティリティを追加。  
    - Windows（psutil の優先度クラス）／POSIX（nice 値）双方を吸収し、AccessDenied 等の例外を安全に扱う。  
    - set_cpu_affinity によるコア固定機能を提供（未サポート OS では警告出力）。
- 監視 DB 初期化:
  - monitoring/monitoring_db.py（参照されているがファイル省略）を初期化呼び出しで利用し、監視テーブルが存在することを保証する（冪等）。

### Changed
- n/a（初期リリースのため変更履歴はなし）

### Fixed
- n/a（初期リリースのため修正履歴はなし）

### Security
- 環境設定ウィザードにて ".env は絶対に Git にコミットしないこと" の注意を明示。  
- 設定読み込みでは OS 環境変数が優先され、.env の自動上書きを制御可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Implementation details
- .env パーサーはクォート内のバックスラッシュエスケープやインラインコメント処理に対応し、一般的な .env フォーマットの落とし穴に配慮している。
- run_execution/run_monitoring は停止フラグ（data/stop_requested.flag）や PID ファイルを使った安全停止メカニズムを備え、長時間デーモン運用に配慮した設計。
- Execution 側の RiskManager のデフォルト設定（max_position_pct=0.20、max_utilization=0.80 など）や Rate limit / Circuit breaker 関連の初期値が設定されている。
- DuckDB / SQLite のパスは Settings 経由で取得し、paper_trading 環境では監視 DB と紙トレード DB を分離する設計（データ汚染防止）。

---

今後のリリース案:
- ログ周りのレベル設定反映（Settings.log_level を logging 設定に適用）
- stocks マスタの導入による銘柄別 lot_size 対応
- monitoring_db / SystemMonitor / ExecutionEngine の更なる堅牢化（リトライ・テレメトリ強化）
- テストカバレッジと CI の追加

（必要に応じてこの CHANGELOG を更新してください）