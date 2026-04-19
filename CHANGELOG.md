# Changelog

すべての重要な変更はこのファイルに記録します。形式は Keep a Changelog に準拠します。  

[未リリース]: https://example.com/compare/HEAD...unreleased

## [0.1.0] - 2026-04-19

初回リリース（コードベースから推測して記載）。

### 追加
- 基本パッケージ情報
  - パッケージのバージョンを `__version__ = "0.1.0"` として導入。

- 設定管理
  - Settings クラスによる環境変数ベースの設定管理を追加。
    - `KABUSYS_ENV`（development / paper_trading / live）や `LOG_LEVEL` 等を扱うプロパティを提供。
    - DB パス（DUCKDB_PATH / SQLITE_PATH）、PID/kill flag パス、監視しきい値（CPU/MEM/DISK）などを取得可能。
    - Paper Trading 用の挙動設定（`is_paper` / `paper_sqlite_path` / `paper_fill_mode`）をサポート。
  - 自動 .env ロード機能を実装。
    - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込み、OS 環境変数を保護するルールで環境変数をセット。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - 設定検証 CLI（kabusys.validate_config）を追加。
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスや config/*.yaml の存在チェック、ライブ環境向けの注意喚起など。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 環境設定ウィザード
  - `kabusys.config_setup` に対話式ウィザードを追加。
    - `.env` の初期作成／更新支援。対話入力、既存値の再利用、シークレットマスク表示、保存確認などを実装。
    - デフォルト値と項目説明を含むテンプレート生成。

- 実行/監視エントリポイント
  - `run_execution.py`
    - ExecutionEngine を起動するスクリプトを提供。
    - 起動時にプロセス優先度を "high" に設定。
    - Paper Trading 環境（`KABUSYS_ENV=paper_trading`）では Paper 用 SQLite（デフォルト: `data/paper_trading.db`）を使用して本番 DB と完全分離。Broker クライアントはファクトリ経由で環境に応じた実体（Mock 等）を生成する想定。
    - 実行中は `data/stop_requested.flag` により安全停止可能。PID ファイルのサポート。
    - リスク管理（RiskManager）初期化時に broker.get_available_cash() を用いた初期資産取得を行う設定。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを提供。
    - デフォルトポーリング間隔 60 秒。`MONITOR_POLL_INTERVAL` 環境変数で上書き可能（不正値は警告を出してデフォルトにフォールバック）。
    - 監視は常に本番用 `sqlite_path` を使用（環境に依存しない）。
    - 停止フラグ (`data/stop_requested.flag`) の検知によるループ終了、KeyboardInterrupt のハンドリング、DB 接続のクローズ処理を行う。

- ロギング & プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続するフォールバックあり。
    - ログレベル/ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
  - `kabusys.utils.process_priority`
    - Windows/Linux/macOS を吸収するプロセス優先度設定と CPU affinity 設定を提供。
    - 標準的な "high"/"normal"/"low" レベルを扱う。権限不足などで失敗した場合は警告を出してスキップする。

- ポートフォリオ構築ロジック（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - 未知レジームは 1.0 でフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`
    - allocation_method（"risk_based", "equal", "score"）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）、cost_buffer（手数料・スリッページ見積り）対応。
    - risk_based では risk_pct / stop_loss_pct に基づくポジションサイズ算出。
    - aggregate cap 適用時の再配分ロジック（残差に基づくlot追加配分）を実装。

- 研究用ファクター計算スケルトン
  - `kabusys.research.factor_research`
    - DuckDB 接続を受けて、Momentum / Value / Volatility / Liquidity 等のファクターを算出するための設計と Momentum 計算関数（calc_momentum）の雛形を追加（prices_daily / raw_financials テーブル参照想定）。
    - 各種計算窓幅やスキャンバッファ等の定数を定義。

- ペーパートレード検証ツール
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計してレポート出力する CLI を追加。
    - CLI 引数 `--from` / `--to` / `--db` をサポート。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定して PASS/FAIL 判定を出力。
    - DB のテーブル欠如（OperationalError）を想定したデフォルト値保護を実装。

- その他ユーティリティ
  - `kabusys.tools.__init__`、`kabusys.utils.__init__`、`kabusys.portfolio.__init__` 等に対するパッケージエクスポート整備。
  - 各モジュールは DB 参照を極力分離し、純粋関数としてユニットテストしやすい設計を志向。

### 既知の注意点 / TODO（コード中の注釈に基づく）
- apply_sector_cap における価格欠損時の扱い
  - price が欠損（0.0）の場合にエクスポージャーが過少評価され、不要に候補が許可される可能性がある点がコメントで指摘されている。将来的に前日終値や取得原価によるフォールバックを検討する必要あり。
- position_sizing の単元株処理の拡張予定
  - 現状は全銘柄共通 lot_size を想定。将来的に銘柄毎の lot_size を持つマスタを導入する拡張の余地あり（TODO コメントあり）。
- factor_research の実装は途中（calc_momentum の途中で切れている）
  - ファクター計算モジュールは設計方針と一部定数・関数の骨格があるが、完全実装は未完の部分がある。
- ログディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップして stdout のみでログを出力する仕様。運用時はログディレクトリの権限等を確認すること。
- プロセス優先度設定や CPU affinity は権限やプラットフォームに依存し、失敗時は警告を出してスキップする実装になっている。

### セキュリティ
- なし（初版）。運用時には `.env` の内容を絶対に Git 等にコミットしないことを README/運用手順で明示すること。

### テスト / 開発メモ（推測）
- 自動ロードされる `.env` の仕様により、テスト環境や CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化する想定。
- `validate_config` と `config_setup` によりローカル開発者の初期セットアップが容易になる。

---

（上記は提供されたコードベースの内容・コメントから推測して作成した CHANGELOG です。正確な差分履歴がある場合は、差分に基づいて具体的な追加・修正点・バグ修正を追記してください。）