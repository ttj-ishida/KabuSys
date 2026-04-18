# CHANGELOG

すべての重要な変更はこのファイルに記載します。  
このプロジェクトは Keep a Changelog の様式に準拠しています。  

※ この CHANGELOG はコードベースの内容から推測して作成した初期リリース向けの要約です。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 全体
  - 初期パッケージ構成を実装。モジュール群（config / execution / monitoring / portfolio / utils / research / tools 等）を含む基本機能を提供。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定関連
  - Settings クラスを実装し、環境変数経由で各種設定（J-Quants / kabuAPI / DB パス / ログレベル / 環境種別など）を取得可能に。
  - .env 自動読み込み機能を実装（プロジェクトルートの `.env` と `.env.local` を適宜読み込む）。OS 側の既存環境変数は保護される。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動読み込みを無効化可能。
  - .env パースの堅牢化（export プレフィックス対応、クォート内のバックスラッシュ・エスケープ対応、インラインコメント処理等）。

- 設定ツール
  - 対話式の環境設定ウィザード `kabusys.config_setup` を実装。`.env` の初期作成・更新を支援。
  - `.env` の既存読み込み・マスク表示・保存機能を提供。

- 設定検証
  - CLI の `kabusys.validate_config` を実装。
  - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在・パース（PyYAML があれば内容検証）などを行う。
  - `--strict` オプションで警告も失敗扱いにできる。

- 実行 / 監視ランタイム
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper trading SQLite DB（`data/paper_trading.db`）を使用し、本番 DB から分離。
    - BrokerClientFactory 等を用いて Engine を組み立て、スレッドで実行。停止はプロジェクトの stop フラグファイルで制御。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ検知、例外ハンドリング、適切なリソースクローズを実装。

- ログ / プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout への StreamHandler（標準出力）と日次ローテーション（TimedRotatingFileHandler、30日保持）のファイルハンドラをルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル解決優先順 (関数引数 > 環境変数 LOG_LEVEL > デフォルト) を実装。
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX (Linux, macOS 等) の差分を吸収し、プロセス優先度 (high/normal/low) を設定。
    - CPU affinity を最初の N コアに固定する機能を提供。権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築
  - `kabusys.portfolio` パッケージを実装（純粋関数群）。
    - 候補選定: select_candidates（スコア降順、signal_rank によるタイブレーク）
    - 重み計算: calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバック）
    - リスク調整: apply_sector_cap（セクター集中上限適用）、calc_regime_multiplier（bull/neutral/bear の乗数）
    - ポジションサイズ算出: calc_position_sizes
      - risk_based, equal, score の配分方式をサポート
      - 単元株（lot_size）丸め、1 銘柄上限、総投下上限（available_cash）でスケールダウン処理
      - 手数料・スリッページ考慮の cost_buffer、残余配分アルゴリズムを実装

- リサーチ / ファクター
  - `kabusys.research.factor_research` を追加（モメンタム / マイナーファクター計算の土台）。
    - DuckDB 接続を受け取り、prices_daily / raw_financials を参照してモメンタム、MA200 乖離、ATR、出来高等を計算する設計（関数シグネチャと定数を含む）。

- ツール
  - `kabusys.tools.paper_verification_report` を追加。
    - Paper Trading 用 SQLite DB（環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）からデータを集計して検証レポートを生成。
    - 指標: 稼働率 (uptime)、注文成功率（fill）、送信率（send）、リスク却下数、レイテンシ（avg/max/P95）など。
    - 閾値を定義し、PASS/FAIL 判定を行う。

- データベース初期化
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を run スクリプトで呼び出して冪等にテーブルを保証する設計を採用。

### 変更 (Changed)
- ログハンドラの挙動
  - stdout を用いることで cron / Task Scheduler 等で stdout/stderr をまとめてリダイレクトする運用を考慮。

- 環境変数パースの挙動改善
  - クォート付文字列内のエスケープ処理やインラインコメント判定を改善し、より現実的な .env 設定に対応。

### 修正 (Fixed)
- エラー回復性の向上
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループ継続するように例外捕捉とログ出力を追加。
  - run_execution のスレッド運用で停止フラグ検知時に安全に engine.stop() を呼ぶ処理を追加。

### 注意 (Notes)
- セキュリティ / 運用
  - `.env` は絶対にリポジトリにコミットしない旨を config_setup の生成コメントで明示。
  - 本番環境（KABUSYS_ENV=live）では LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険な設定を validate_config で警告するガードを用意。
- 未実装 / TODO
  - price の欠損時のフォールバック（前日終値等）に関する TODO コメントを残している箇所がある（将来的な拡張）。
  - factor_research の一部関数（ファクター計算の実装の続き）はコード途中で終わっているため、完全実装が必要。

### 破壊的変更 (Removed)
- なし（初期リリースのため該当なし）。

### セキュリティ (Security)
- なし（既知のセキュリティ修正は含まれない）。

---
この CHANGELOG は現行コードから推測して作成したものであり、実際のコミット履歴とは異なる場合があります。追ってコミット単位の詳細な履歴を作成することを推奨します。