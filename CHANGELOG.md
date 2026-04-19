# Changelog

すべての注目すべき変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

※ このリポジトリは初期リリースとしてバージョン 0.1.0 を含みます。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ構成と初期機能群を追加。
  - パッケージ情報
    - `src/kabusys/__init__.py` にバージョン情報 `__version__ = "0.1.0"` を追加。

- 実行スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視プロセスは常に本番用 `sqlite_path` を使用して監視データを保存。
    - 起動時にプロセス優先度を `high` に設定（`utils.process_priority.set_process_priority` を利用）。
    - 停止はプロジェクト直下 `data/stop_requested.flag` の存在で検知。
    - エラーはロギングに記録し、ループは継続。

  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動するスクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を利用し `data/paper_trading.db` に記録することで本番 DB と分離。
    - 起動時にプロセス優先度を `high` に設定。
    - paper_trading モードでは専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用。
    - 停止フラグ（`data/stop_requested.flag`）と PID ファイル（`data/execution.pid`）の取り扱いを実装。
    - Engine を別スレッドで実行し、フラグ検知で安全に停止。

- 設定・環境管理
  - `src/kabusys/config.py`
    - .env 自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 高度な .env 行パーサ（クォート、エスケープ、コメント処理対応、`export KEY=val` 対応）。
    - 環境変数の保護（OS 環境変数を上書きしない仕組み）。
    - `Settings` クラスを提供し、アプリケーションで使う設定値（DuckDB/SQLite パス、PID パス、閾値、env 判定等）をプロパティ経由で取得・検証。
    - `PAPER_FILL_MODE` の検証（有効値: "instant" | "partial" | "never" | "reject"）。
    - `KABUSYS_ENV`（`development` / `paper_trading` / `live`）および `LOG_LEVEL` の検証。
    - `settings = Settings()` の即時インスタンスをエクスポート。

  - `src/kabusys/config_setup.py`
    - .env 作成・更新の対話式ウィザードを追加。
    - 秘匿項目のマスク表示、選択肢サポート、既存 .env の読み込み・再利用機能。
    - 生成される .env に対してコミットしない旨のコメントを挿入。

  - `src/kabusys/validate_config.py`
    - 起動前チェック用 CLI を追加。
    - 必須環境変数チェック（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD` など）、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在確認（PyYAML がインストールされている場合はパース検証を実行）。
    - `--strict` オプションで警告も失敗に昇格できる。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`) と配分重み計算 (`calc_equal_weights`, `calc_score_weights`) を追加。
    - スコアが全て 0 の場合は等配分にフォールバックし、警告ログを出力。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクターキャップ適用 (`apply_sector_cap`)。
    - 市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`) を追加（"bull"/"neutral"/"bear" 対応、未定義はフォールバック）。
    - セクターが "unknown" の場合はキャップを適用しない形に設計。

  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出ロジックを実装（`allocation_method` として "risk_based" / "equal" / "score" をサポート）。
    - 単元株丸め、1 銘柄上限、利用可能現金に基づく aggregate cap とスケーリング、残余分の再配分ロジックなどを実装。
    - コストバッファ（スリッページ・手数料見積）に対応。

  - `src/kabusys/portfolio/__init__.py`
    - 上記関数をエクスポート。

- ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル / 出力先解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで動作。
    - stdout を用いることで cron 等でのログリダイレクト運用に配慮。

  - `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class、POSIX の nice 値）、CPU アフィニティ固定機能を追加。
    - 権限不足等はログ警告を出してフォールバック。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - デフォルト DB パス: `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`。
    - 指標と閾値:
      - 稼働率 (uptime) しきい値 99.0%
      - 注文成功率 (fill rate) しきい値 90.0%
      - 送信率 (send rate) しきい値 95.0%
      - P95 レイテンシしきい値 200 ms
    - CLI オプション: `--from`, `--to`, `--db`。
    - データ不足 / テーブル未存在時に graceful に N/A を返す実装。

- リサーチ（初期）
  - `src/kabusys/research/factor_research.py`
    - ファクター計算モジュールの骨組みと定数を追加。
    - モメンタム指標の計算（1M/3M/6M、MA200 乖離）を計画。ファイルは途中まで実装（未完）で、DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。

### Changed
- (初期リリースのため該当なし)

### Fixed
- (初期リリースのため該当なし)

### Security
- .env ファイルは Git にコミットしないことを README 等で明示することを推奨（`config_setup.py` にも同旨コメントを出力）。
- `config.py` の `_require()` は必須環境変数未設定時に ValueError を投げる。デプロイ時は必須環境変数の設定を忘れないこと。

### Notes / Migration
- 実行方法（例）
  - 監視ループ: python -m kabusys.run_monitoring
  - エンジン起動: python -m kabusys.run_execution
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

- 重要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABUSYS_ENV (development | paper_trading | live) — default: development
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
  - LOG_LEVEL — default: INFO
  - MONITOR_POLL_INTERVAL — 監視ポーリング秒数（run_monitoring 用、デフォルト 60）

- 動作上の注意
  - `set_process_priority` / `set_cpu_affinity` は psutil を利用するため、実行環境に psutil のインストールと適切な権限が必要。権限不足時は警告を出してスキップする。
  - `logging_setup` はログディレクトリの作成に失敗した場合、ファイル出力を行わずコンソールのみで継続する。
  - `validate_config` は PyYAML 未インストール時に YAML のパース検証をスキップする（警告出力）。

---

今後の予定（例）
- research/factor_research.py の完成（各ファクターの実装とユニットテスト）。
- execution/monitoring 系のユニットテストと E2E テスト追加。
- BrokerClient の具体実装（実ブローカー連携）とモックの拡充。