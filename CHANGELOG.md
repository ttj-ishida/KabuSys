# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の仕様に従います。  
このプロジェクトの初回公開リリースを記録しています。

注: 日付はこのリリース時点のものです。

## [0.1.0] - 2026-04-18

### Added
- 初期リリース。KabuSys 自動売買システムのコアユーティリティ・モジュールを追加。
- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV が `paper_trading` の場合は専用のペーパートレード用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離する動作を実装。
    - 実行中は PID ファイル（data/execution.pid）を扱い、停止フラグ（data/stop_requested.flag）を監視して安全に停止可能。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して記録する設計。
- 設定管理
  - `config.py`
    - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - .env パース機能（コメント・クォート・export 形式に対応）。
    - 各種プロパティ経由の設定取得（DB パス、API トークン、環境判定、監視しきい値など）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化のサポート。
  - `config_setup.py`
    - .env を対話的に生成・更新するウィザード CLI を追加。
    - デフォルト値・選択肢表示やシークレット入力をサポートし、.env のテンプレート書き出しを行う。
  - `validate_config.py`
    - 起動前の設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML があれば検証）などを実施。`--strict` オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに対して stdout StreamHandler と日次ローテート FileHandler（logs/<app>.log）を統一設定するユーティリティを追加。ログレベル / ログディレクトリは環境変数または引数で制御可能。
  - `utils/process_priority.py`
    - Windows/Linux/macOS を吸収するプロセス優先度設定・CPU affinity ユーティリティを追加。権限不足時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純関数群）
  - `portfolio/portfolio_builder.py`
    - シグナルのソーティング・候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を追加。
  - `portfolio/risk_adjustment.py`
    - セクター集中除外ロジック (`apply_sector_cap`) と市場レジームに基づく投下資金乗数 (`calc_regime_multiplier`) を追加。
  - `portfolio/position_sizing.py`
    - 複数の配分方式（`risk_based`, `equal`, `score`）に対応する株数計算ロジックを追加。lot（単元）丸め、per-stock 上限、aggregate cap スケーリング、手数料/スリッページバッファ考慮を実装。
  - `portfolio/__init__.py`
    - 上記機能を公開 API としてエクスポート。
- 研究/分析ツール
  - `research/factor_research.py`（ファクター計算モジュール）
    - DuckDB の `prices_daily` / `raw_financials` を用いたモメンタム・バリュー・ボラティリティ等の定量ファクター計算を追加（設計方針と定義を含む）。
- 運用ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード結果の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計し PASS/FAIL 判定を出力。
    - CLI 引数で期間指定（--from/--to）と DB パス指定（--db）が可能。環境変数 `PAPER_TRADING_SQLITE_PATH` を優先して参照。
- パッケージメタ情報
  - `__init__.py` にバージョン `0.1.0` を追加。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Removed
- （初回リリースにつき該当なし）

### Security
- 機密情報（API トークン等）は .env に保持する設計とし、`config_setup.py` の出力ヘッダで .env を Git にコミットしないよう注意喚起を明示。

### Notes / Important details
- DB 周り
  - DuckDB（分析用）と SQLite（監視 / 履歴用）を併用する設計。パスは環境変数で上書き可能（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。
  - 監視（monitoring）は環境にかかわらず sqlite_path を使用して記録するため、設定に注意すること。
- 実行制御
  - 停止操作はプロジェクトルートの data/stop_requested.flag（止める）や KILL フラグなどファイルベースで行う設計。`KILL_FLAG_CLEAR_ON_START` により起動時の自動クリア挙動を制御可能（本番では 0 推奨）。
- エラーハンドリング
  - 実行中の例外はログ記録後にポーリング待機へフォールバックするなど頑健化されている（monitoring のループ等）。
- ローカル開発向け
  - `KABUSYS_ENV=paper_trading` を利用することで発注ロジックをモック化し、実際の発注を分離して検証できる。
- 未完 / TODO
  - `portfolio/risk_adjustment.py` の apply_sector_cap 内で price が欠損（0.0）の場合のフォールバック価格取得は TODO コメントあり。
  - position sizing の将来的拡張として銘柄別 lot_size を持たせる設計の注記あり。
  - `research/factor_research.py` はファイル末尾で未完の箇所が見られる（スニペット切断）。本番投入前に追加テスト・完成が必要。

---

今後のリリースでは、テストカバレッジの追加、ドキュメント整備、factor_research の完成、実運用での挙動確認に基づくチューニングを予定しています。詳細な差分や導入手順が必要であれば追って CHANGELOG に追記します。