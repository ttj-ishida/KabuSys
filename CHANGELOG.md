# CHANGELOG

すべての notable な変更点を Keep a Changelog のフォーマットで記載します。  
この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

フォーマット:
- Unreleased（作業中）
- バージョンごとに日付付きで主要な追加・変更・修正点を列挙

---

## [Unreleased]

特になし。

---

## [0.1.0] - 2026-04-20

初回リリース — 基本的な自動売買フレームワークのコア機能を実装。

### Added
- 全体構成
  - パッケージメタ情報を `__version__ = "0.1.0"` として定義。
  - DuckDB / SQLite を用いたデータ管理（分析用 DuckDB、監視/履歴用 SQLite）。

- 設定・環境変数関連
  - Settings クラス（`kabusys.config`）を実装し、環境変数から各種設定（API トークン、DB パス、閾値等）を取得。
  - 自動 `.env` ロード機構を実装（プロジェクトルート検出: `.git` または `pyproject.toml`）。優先順位は OS 環境 > .env.local > .env。必要に応じて自動ロードを無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
  - `.env` パーサを強化:
    - `export KEY=val` 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの正しい扱い（クォート有無で振る舞いを分岐）
  - `config_setup.py` による対話式環境設定ウィザードを追加（.env の初期作成・更新を支援）。
  - `validate_config.py` による設定検証 CLI を追加（必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と簡易パース確認等）。`--strict` オプションで警告も失敗として扱える。

- 実行関連スクリプト
  - `run_execution.py`:
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を高く設定して起動。
    - `KABUSYS_ENV=paper_trading` では MockBrokerClient を利用し、paper_trading 用の専用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory を使用して実行環境に応じたブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler 等の依存コンポーネントを組み立て、ExecutionEngine のセッションをスレッドで実行。停止フラグ（`data/stop_requested.flag`）を検知すると安全に停止。
    - PID ファイル管理（`data/execution.pid`）を利用。
    - RiskManager の初期設定において `initial_portfolio_value` を broker.get_available_cash() から動的に取得。
  - `run_monitoring.py`:
    - SystemMonitor のポーリングループ起動スクリプトを追加。デフォルトポーリング間隔は 60 秒。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（不正値はワーニングを出してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用して監視テーブルを管理。
    - 停止フラグの存在でループ終了、例外はロギングして次のポーリングへ継続。

- 監視 / データベースユーティリティ
  - `monitoring_db.init_monitoring_db` を通じて監視テーブルの初期化を行い、起動時に冪等に存在確認を実施。

- ロギング・プロセス制御ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を持ち、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - 既存ハンドラは一度 flush/close してから再設定（重複防止）。
  - `kabusys.utils.process_priority` を追加:
    - Windows と POSIX（Linux/macOS/FreeBSD）での優先度設定を吸収（nice 値 / Windows priority class のフォールバックを利用）。
    - CPU affinity を最初の N コアに固定する機能を提供（設定失敗時は警告を出してスキップ）。

- ポートフォリオ構築
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定（score 降順、同点時は signal_rank でタイブレーク）。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）— 全スコアが 0 の場合は等配分にフォールバックして WARNING を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限を適用する apply_sector_cap（既存保有のセクター比率が上限を超えるセクターの新規候補を除外）。"unknown" セクターは制限対象外。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をマップ、未知の値は警告を出して 1.0 にフォールバック）。
  - `kabusys.portfolio.position_sizing`:
    - position size 計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - 単元株（lot_size）で丸め、1 銘柄上限・aggregate 上限を考慮。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的なコスト推定と、投資額が available_cash を超える場合のスケーリング（残差に基づく lot 単位での追加配分ロジックを実装）。

- 分析・検証ツール
  - `kabusys.tools.paper_verification_report`:
    - Paper Trading 用の検証レポート生成 CLI を追加。SQLite（デフォルト `data/paper_trading.db`）からデータを集計し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出して Pass/Fail 判定を出力。
    - デフォルト基準値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from/--to）をサポート。DB が存在しない場合のエラーメッセージを実装。
    - SQL の実行エラー（テーブルが存在しない等）に対して単独指標を N/A 等でフォールバックしてレポート可能。

- 研究モジュール（実装開始）
  - `kabusys.research.factor_research` の骨組みを実装（モメンタム等ファクター計算の方針・定数・calc_momentum のシグネチャと説明を含む）。DuckDB を入力として prices_daily / raw_financials を参照する設計。ファクター計算の詳細実装はファイル末尾で未完（部分実装）。

### Changed
- （初回リリースのため過去の変更なし）

### Fixed
- （初回リリースのため過去の修正なし）

### Notes / 運用上の注意
- .env は絶対に Git にコミットしないこと。`config_setup.py` によりローカルで生成・更新可能。
- `KABUSYS_ENV` によって挙動（本番 / ペーパー）を切り替えるが、監視（monitoring）は環境にかかわらず本番用の SQLite パスを使用する設計になっている点に注意。
- ログディレクトリ作成やプロセス優先度／CPU affinity の設定は権限不足などで失敗する可能性があり、その場合は警告を出してスキップする実装となっている。
- `calc_position_sizes` や `apply_sector_cap` は価格データが欠損する（0 や None）場合に保守的にスキップする振る舞いがあり、将来的にフォールバック価格を追加する余地がある。

---

今後の改善提案（参考）
- factor_research の完成（Momentum / Value / Volatility / Liquidity の完全実装）。
- テストスイート（ユニットテスト）および CI 設定の追加。
- 各コンポーネントのログ・メトリクス出力（監視やアラート連携の充実）。
- 銘柄毎の lot_size をマスタで管理して position sizing に反映。
- DuckDB による定期バッチ／分析パイプラインの整備。

---