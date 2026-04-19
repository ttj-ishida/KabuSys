Keep a Changelog に準拠した CHANGELOG（日本語）

すべての重要な変更はここに記録します。フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に従います。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-19
初回リリース

### 追加
- 全体
  - プロジェクト初期版を公開。日本株自動売買システム「KabuSys」の基盤モジュール群を実装。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 設定・環境読み込み
  - 環境変数/ .env 読み込みモジュールを追加（`kabusys.config`）。
    - プロジェクトルートを .git または pyproject.toml から自動検出して .env/.env.local を読み込む（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースは export 形式、クォート、インラインコメント（一部）に対応。
    - .env.local は .env の上書き（OS 環境変数は保護）。
  - `Settings` クラスを実装し、主要な設定値をプロパティとして提供（J-Quants トークン、kabu API、DB パス、ペーパートレード設定、閾値、実行環境判定など）。
    - デフォルト値・バリデーションを多数実装（`KABUSYS_ENV` / `LOG_LEVEL` 等の妥当性チェック）。
    - Paper Trading 用 DB パス、`PAPER_FILL_MODE` の有効値チェック等を提供。

- 設定ツール（CLI）
  - 環境設定ウィザード（`kabusys.config_setup`）
    - 対話形式で .env を新規作成・更新するウィザードを実装。
    - シークレット項目は表示をマスクし、保存テンプレート（.env）を出力。
  - 設定検証ツール（`kabusys.validate_config`）
    - 起動前に必須環境変数や設定ファイル（config/*.yaml）の存在・簡易妥当性をチェック。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 起動スクリプト
  - 実行エンジン起動スクリプト（`kabusys.run_execution`）
    - プロセス優先度を起動直後に "high" に設定（`kabusys.utils.process_priority` を使用）。
    - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用して `data/paper_trading.db` に完全に分離して記録（本番 DB と分離）。
    - ExecutionEngine の組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等の起動）。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全に停止する機構を実装。実行時の PID をファイルに出力する仕組みを想定（`data/execution.pid`）。
  - 監視（Monitoring）起動スクリプト（`kabusys.run_monitoring`）
    - ポーリングループを提供し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計（監視データは本番 DB を想定）。
    - stop フラグを検知してループを終了。`check_once()` の例外はログに残して次ポーリングへ継続。

- DB / 分析
  - DuckDB を統合（複数スクリプトで duckdb 接続を使用）。デフォルトパスは `data/kabusys.duckdb`。
  - 監視テーブル初期化ユーティリティ `init_monitoring_db` を導入（冪等にテーブルを保証）。

- ロギング・プロセス制御ユーティリティ
  - ログ設定ユーティリティ（`kabusys.utils.logging_setup`）
    - コンソール（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時にはファイル出力をスキップし、コンソールのみで継続。
    - LOG_LEVEL / LOG_DIR / app_name による柔軟な設定。
  - プロセス優先度・CPU affinity ユーティリティ（`kabusys.utils.process_priority`）
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して nice / priority を設定。
    - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - psutil の権限エラー等はログに警告してスキップ。

- ポートフォリオ構築（純関数群）
  - 候補選定・重み計算（`kabusys.portfolio.portfolio_builder`）
    - select_candidates（スコア降順、タイブレーク条件）、等金額／スコア加重の重み計算を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - セクター集中制限・レジーム乗数（`kabusys.portfolio.risk_adjustment`）
    - apply_sector_cap：既存ポジションに基づきセクター上限（max_sector_pct）を超える場合、新規候補を除外するロジックを提供。未知セクターは除外しない。
    - calc_regime_multiplier：market regime に応じた資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック。
  - ポジションサイズ計算（`kabusys.portfolio.position_sizing`）
    - calc_position_sizes：risk_based / equal / score の allocation_method をサポート。ロット単位（lot_size）、コストバッファ（cost_buffer）を考慮した aggregate cap スケーリング、最大ポジション比率・利用率制限などを実装。
    - aggregate スケーリング時は端数処理を行い、残余資金で lot 単位を追加配分するアルゴリズムを提供。
    - 一部の処理で price が欠損した場合の TODO コメント等を残す（将来的なフォールバック価格の検討を注記）。

- リサーチ（部分実装）
  - ファクター計算モジュールの骨子（`kabusys.research.factor_research`）を追加。
    - Momentum / Value / Volatility / Liquidity に関する方針と定数を定義。
    - DuckDB を使った計算を想定した設計。いくつかの実装箇所は未完（コメントや TODO が残る）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）
    - Paper Trading DB（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（AVG / MAX / P95）等を集計してレポート出力。
    - 基準値（例: 稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ（--from / --to）、--db オプションをサポート。P95 は簡易実装で近似計算を行う。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 既知の問題・注意事項
- `kabusys.research.factor_research` はファイル末尾の実装が途切れており、完全な関数実装が未完（今後の実装予定）。
- position_sizing / risk_adjustment 内に価格欠損時のフォールバック戦略などの TODO コメントあり。価格データ欠損があると一部の計算でスキップされる。
- ログディレクトリの作成・ファイル書き込みに失敗した場合はコンソールログのみで継続する設計（運用環境でログパス権限を確認してください）。
- process priority / cpu affinity の設定は OS / 権限に依存するため、権限不足時には警告を出して動作をスキップする。

### セキュリティ
- `.env` ファイルは決してリポジトリにコミットしないでください（config_setup の説明でも注意喚起）。

---

今後の予定（例）
- factor_research の完全実装（DuckDB SQL + Python）とユニットテスト追加。
- Execution / Monitoring の統合テスト、Paper Trading のモック精度向上（PAPER_FILL_MODE 切替の検証）。
- 各モジュールに対するユニットテスト・ドキュメントの拡充。