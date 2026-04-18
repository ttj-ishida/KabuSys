# Changelog

すべての注目すべき変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  

リリース日付はコードベースから推測した最初のリリース（0.1.0）を 2026-04-18 として記載しています。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 全体
  - 初期パブリック実装を追加。モジュール構成、CLI、ユーティリティ、ポートフォリオ構築、研究（ファクター計算）、実行・監視エンジンの起動スクリプト等を提供。
  - バージョン情報を `kabusys.__version__ = "0.1.0"` として定義。

- 設定・環境読み込み
  - .env ファイル自動読み込み機能を実装（プロジェクトルートの検出をベースに .env と .env.local を読み込む。環境変数は OS 環境変数を保護）。
  - 高機能な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの挙動を考慮）。
  - Settings クラスを追加し、アプリケーションの各種設定（J-Quants トークン、kabu API、DB パス、Paper Trading 用設定、監視しきい値、実行環境判定 等）をプロパティ経由で取得可能に。

- 設定支援 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成・更新する CLI を追加（項目定義、既存値の読み込み、シークレットマスク表示、保存確認など）。
  - `kabusys.validate_config`：.env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パス存在チェック、YAML のパースチェック（PyYAML が利用可能な場合）や本番環境向けの警告を出力。--strict オプションで警告を失敗扱いにできる。

- 実行・監視起動スクリプト
  - `run_execution.py`：ExecutionEngine を起動するエントリポイントを追加。起動時にプロセス優先度を "high" に設定し、Paper Trading 環境では専用 (分離された) SQLite DB を使用する挙動を実装。停止は data/stop_requested.flag によるフラグで制御。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する仕様。

- ブローカー / 実行関連
  - BrokerClientFactory（抽象化されたブローカクライアント生成）を導入し、paper_trading 環境では MockBrokerClient を利用する想定（コードから挙動を推測）。
  - ExecutionEngine の起動方法およびセッションスレッド化、停止時の安全なシャットダウン処理を実装。

- 監視 / モニタリング
  - 監視用 DB 初期化ユーティリティ（`init_monitoring_db`）を追加し、起動時に監視テーブルの存在を保証（冪等）。
  - SystemMonitor の単発チェック `check_once()` をループで呼び出し、例外はキャッチしてログ出力後に次回まで待機する堅牢化を実装。

- ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading の検証レポート生成スクリプトを追加。指定期間の稼働率、注文成功率、送信率、P95 レイテンシ等を SQLite データから集計し PASS/FAIL を判定する。P95 計算、日付フィルタ、テーブル不存在時のフォールバック処理を実装。
  - `kabusys.tools` パッケージエントリを追加。

- ポートフォリオ構築（純関数群）
  - `portfolio.portfolio_builder`：候補選定（スコア降順、タイブレーク）、等金額配分、スコア加重配分（全てのスコアが 0 の場合は等金額にフォールバック）を実装。
  - `portfolio.risk_adjustment`：セクター集中制限（セクター別エクスポージャ計算と候補除外）と市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング）を実装。
  - `portfolio.position_sizing`：allocation_method（risk_based / equal / score）に基づく株数算出を実装。単元株（lot_size）丸め、1 銘柄上限、投下資金合計（aggregate cap）超過時のスケーリングと残差処理（lot 単位での追加配分）を実装。手数料・スリッページ見積りのための cost_buffer パラメータを考慮。

- 研究（ファクター計算）
  - `research.factor_research`：DuckDB を用いたファクター計算（モメンタム：1M/3M/6M、MA200乖離、ボラティリティ：ATR20、流動性指標 等）を実装。スキャンウィンドウ、ウィンドウ不足時の None 返却、SQL ベースでの集計ロジックを実装。

- ユーティリティ
  - `utils.process_priority`：プラットフォーム差分を吸収するプロセス優先度設定関数を実装（Windows と POSIX を考慮）。`set_cpu_affinity`（最初の N コアへピンニング）も追加。失敗時は警告を出してスキップする堅牢化。

### 変更 (Changed)
- DB の役割分離を明確化
  - DuckDB を分析用（prices_daily 等の時系列分析に使用）、SQLite を監視・トレードログ用に利用する設計を明確化。
  - Paper Trading 環境は専用の SQLite（`PAPER_TRADING_SQLITE_PATH` / default `data/paper_trading.db`）を使って本番 DB と完全に分離するように実行スクリプトを構成。

- 起動時の安全対策
  - `run_execution` / `run_monitoring` いずれも起動直後にプロセス優先度を "high" に設定する処理を追加（重要処理優先のため）。
  - 停止リクエストはプロジェクト内の `data/stop_requested.flag`（および execution.pid 等）を用いたファイルベースのフラグで制御する共通の挙動を採用。
  - `run_monitoring` は MONITOR_POLL_INTERVAL を環境変数で上書き可能に（不正な値はデフォルト 60 秒にフォールバックする）。

- 設定検証の強化
  - `validate_config` のチェックを強化：必須環境変数チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在とパースチェック（PyYAML 利用時）を実施。KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険設定指摘）を実装。

- .env ファイルハンドリング
  - .env 読み書きロジックを改善し、既存値の読み込み/表示（シークレットはマスク）や .env の書式で保存する `config_setup` を実装（.env を誤って Git にコミットしない旨のヘッダを追加）。

### 修正 (Fixed)
- .env パースの耐性向上
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント処理などの不正パースによる誤設定を回避する実装に修正。
  - 自動ロード時にプロジェクトルートが見つからない場合はスキップするよう安全化。

- 監視ループの健全性向上
  - monitor.check_once() の例外をキャッチしてログ出力後に次ループへ継続するようにし、監視プロセスが例外で停止しないようにした。
  - ポーリング間隔に 0 以下を設定すると time.sleep で ValueError となる可能性があるため、不正値はデフォルト（60 秒）にフォールバックする処理を追加。

- Paper 検証レポートの堅牢化
  - 対象 DB のテーブルが存在しない場合に sqlite3.OperationalError を捕捉してフォールバックすることで、テーブル欠如時もレポート生成が完全に失敗しないようにした。
  - P95 計算、日付範囲の ISO8601 変換、NULL 値ハンドリングを強化。

- ポートフォリオ計算の安全弁
  - `calc_score_weights`：全銘柄のスコア合計が 0 の場合、等金額配分にフォールバック（警告ログ出力）するようにし、ゼロ除算を回避。
  - `apply_sector_cap`：sector が未登録（"unknown"）の場合はセクター上限の除外対象とせず、不要なブロックを回避する。
  - `calc_position_sizes`：価格欠損や price <= 0 の銘柄をスキップ、aggregate cap スケーリング後の端数配分アルゴリズムで単元株（lot_size）を尊重する実装に改良。

### 既知の制約・注意点 (Known issues / notes)
- 一部の処理は外部モジュール（psutil、duckdb、PyYAML 等）に依存しており、未インストール時は機能制限や警告が出ます（例：YAML 検証のスキップ、プロセス優先度設定の失敗など）。
- `apply_sector_cap` は price_map に欠損（0.0）があるとエクスポージャが過小評価され、ブロックが外れる可能性がある旨の TODO コメントあり。将来的に前日終値等のフォールバック価格を導入することを想定。
- レジーム乗数 (`calc_regime_multiplier`) は未知のレジーム値で 1.0 にフォールバックし、警告を出します。Bear レジームは戦略上 BUY シグナルが出ない設計のため、乗数は中間的な安全弁としての役割に留まる。

---

もし CHANGELOG に追記したいリリース日やフォーカスポイント（例：セキュリティ修正、パフォーマンス改善、互換性破壊の情報）があれば指定してください。それに合わせて内容を調整します。