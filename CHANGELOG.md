# Changelog

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載します。  
このリポジトリの初回リリース情報を以下に示します。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装
  - パッケージバージョンを設定: `kabusys.__version__ = "0.1.0"`。
- 設定管理
  - `kabusys.config.Settings` クラスを追加。環境変数から各種設定値（DB パス、API トークン、環境種別、ログレベル等）を取得する。
  - 自動 .env ロード機能を実装。プロジェクトルートの検出は `.git` または `pyproject.toml` を基準に行う（テスト等のため `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
  - .env パースの強化（export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いなど）。
- 環境設定ウィザード CLI
  - `kabusys.config_setup` を追加。対話式に `.env` を作成/更新するウィザードを提供（`--env-file` オプション対応）。シークレット項目はマスク表示。
  - 生成される `.env` に注記を含め、誤って Git にコミットしないよう注意を促すテンプレート生成機能を実装。
- 設定検証 CLI
  - `kabusys.validate_config` を追加。必須/任意環境変数、KABUSYS_ENV、ログレベル、DB パス、`config/*.yaml` の存在とパース（PyYAML がある場合）などをチェック。`--strict` オプションで警告を FAIL 扱いにできる。
  - `KABUSYS_ENV=live` の場合の追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START 設定）を実装。
- 実行/監視プロセス起動スクリプト
  - `kabusys.run_execution` を追加。プロセス起動時にプロセス優先度を設定し、SQLite / DuckDB に接続、Broker クライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて `ExecutionEngine` を起動する。paper_trading 環境時は専用の SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と完全分離する設計。
  - `kabusys.run_monitoring` を追加。`SystemMonitor` を初期化してポーリングループを実行。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。監視は環境に関係なく本番用 `sqlite_path` を使用している点に注意。
  - 両スクリプトとも停止判定にデータディレクトリの stop flag (`data/stop_requested.flag`) を用い、PID ファイルの扱いを行う。
  - 起動直後にプロセス優先度を "high" に設定する仕組みを共通で実行。
- 実行系コンポーネント骨格
  - Broker クライアント生成のための `BrokerClientFactory` を導入（paper_trading 時は MockBrokerClient を利用する方針）。
  - `ExecutionEngine`、`OrderManager`、`OrderRepository`、`RiskManager`、`Reconciler` といった実行周りの依存コンポーネントを組み合わせる設計を追加（デフォルトの RiskConfig 値を設定）。
  - ExecutionEngine を別スレッドで実行し、stop フラグまたは外部要因で安全に停止できる仕組みを実装。
- 監視周り
  - 監視 DB 初期化ユーティリティ `init_monitoring_db` の呼び出しを導入。`SystemMonitor.check_once()` を定期実行し例外ハンドリングでループの安定化を図る。
- ツール: Paper Trading 検証レポート
  - `kabusys.tools.paper_verification_report` を追加。ペーパートレードの SQLite（デフォルト `data/paper_trading.db`）から以下を集計してレポート出力:
    - システム稼働率（uptime）、エラー数
    - 注文成功率（Filled/Created）、送信率（Sent/Created）
    - リスクによる却下数（risk_logs）
    - レイテンシ（平均/最大/P95） — P95 計算ロジックを実装
  - デフォルトしきい値を定義し、PASS/FAIL 判定を行う（稼働率、成功率、送信率、P95 レイテンシ等）。
  - コマンドラインオプションで期間フィルタ（--from/--to）および DB パス（--db）を指定可能。
- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - シグナル選定 `select_candidates`（スコア降順、タイブレークに signal_rank）を実装。
    - 等金額配分 `calc_equal_weights`、スコア加重 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - `kabusys.portfolio.position_sizing`:
    - position size 計算 `calc_position_sizes`（allocation_method: "risk_based" / "equal" / "score"）を実装。単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer（手数料/スリッページ見積）適用等を実装。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap` を実装（既存保有からセクター別エクスポージャー計算し上限超過セクターの新規候補を除外）。"unknown" セクターは制限を適用しない。
    - レジームに応じた資金乗数 `calc_regime_multiplier` を実装（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知レジームは 1.0 にフォールバック）。
- リサーチ / ファクター計算
  - `kabusys.research.factor_research` を追加。DuckDB 接続を受け取り prices_daily 等のテーブルから以下のファクターを計算する設計を実装:
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離）を計算する SQL 実装（データ不足時は None）。
    - ボラティリティ / 流動性: ATR（20日）、相対 ATR、20日平均売買代金、出来高比率などを計算する SQL 実装（ウィンドウ計算、true_range の NULL 伝播考慮を導入）。
  - 設計方針として、外部 API へのアクセスは行わず DuckDB + SQL/Python で完結することを明記。
- ユーティリティ
  - `kabusys.utils.process_priority` を追加。Windows と POSIX 系 (Linux/Mac/FreeBSD) の差分を吸収してプロセス優先度（"high" / "normal" / "low"）および CPU affinity を設定するユーティリティを実装。`psutil` を利用し、権限不足等は警告でフォールバック。
- パッケージ初期公開用の __all__ エクスポートを整備（portfolio モジュール等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- `.env` ファイルに API トークンやパスワードなどの機密情報が含まれるため、生成される `.env` の Git コミットを明示的に禁止する注記を追加。
- config_setup の対話でシークレット項目はマスク表示。

### Notes / Known limitations / TODO
- position_sizing の単元株（lot_size）は現状グローバルで固定（デフォルト 100）。将来的には銘柄別 lot_size マスタを導入する旨を TODO コメントで記載。
- risk_adjustment のセクターエクスポージャー計算は価格欠損時にエクスポージャーが過小評価される可能性がある（将来的に前日終値や取得原価でフォールバックする案を検討中）。
- `factor_research` の計算は prices_daily / raw_financials に依存。DuckDB に必要なテーブルが存在しない場合は適切にハンドリングする必要がある。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、失敗時は警告でフォールバックする仕様。
- 監視ループ（run_monitoring）は MONITOR_POLL_INTERVAL に 0 以下を指定すると警告してデフォルトにフォールバックするよう保護している。

---

今後のリリースでは以下を予定しています（例）:
- ExecutionEngine の詳細実装と Broker 実装（kabuステーション実装）の追加
- 戦略ロジック（シグナル生成・StrategyModel）の実装
- テストおよび CI の整備、ドキュメントの拡充

（この CHANGELOG はコードベースから推測して作成しています。実装済み機能とドキュメントの差異がある場合はリポジトリのソースを基準に調整してください。）