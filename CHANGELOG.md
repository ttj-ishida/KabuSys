# CHANGELOG

すべての重要な変更をこのファイルで管理します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョンポリシー: 0.x 開発中 — 後方互換性は将来のメジャーリリースで変更される可能性があります。

## [Unreleased]

（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-04-17

初回公開リリース。以下の主要機能と CLI ツールを実装しました。

### 追加
- 全体
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - デフォルトのデータファイル配置:
    - DuckDB: data/kabusys.duckdb
    - SQLite (監視 DB): data/monitoring.db
    - Paper trading SQLite: data/paper_trading.db
    - PID / フラグファイル: data/execution.pid, data/stop_requested.flag など

- 設定管理
  - Settings クラスを実装（kabusys.config）。環境変数から各種設定を取得し、値検証を行う。
    - KABUSYS_ENV（development / paper_trading / live）
    - PAPER_FILL_MODE（instant / partial / never / reject）検証
    - 各種パス、しきい値、ログレベル等をプロパティで提供
  - .env 自動読み込み機能を追加（プロジェクトルートの .env、.env.local を読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーは export プレフィックス、クォート、コメント、エスケープをサポート。

- 設定ユーティリティ / CLI
  - 環境設定ウィザード（kabusys.config_setup）
    - 対話式に .env を作成・更新するウィザードを提供
    - 秘匿項目はマスク表示、デフォルト値・選択肢をサポート
    - .env 作成時に保存前確認を行う
  - 設定検証ツール（kabusys.validate_config）
    - 起動前チェック（必須環境変数、KABUSYS_ENV 値、DB パスの親ディレクトリ、config/*.yaml の存在と YAML パース（PyYAML あれば））
    - --strict モードで警告を FAIL 扱いにできる

- 実行・監視ランナー
  - Execution エンジン起動スクリプト（kabusys.run_execution）
    - プロセス優先度を High に設定して起動
    - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して paper_trading 用 SQLite を使用
    - BrokerClientFactory 経由でブローカークライアントを作成
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行（スレッド実行）
    - 停止フラグ（data/stop_requested.flag）検知で安全停止処理
    - デフォルトの RiskManager 設定（max_position_pct=0.20 等）を定義
  - Monitoring ポーリングループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒、無効値はデフォルトへフォールバック）
    - 監視は常に本番 sqlite_path を使用（環境にかかわらず）
    - SystemMonitor を用いた単発チェック（check_once）を定期実行、例外はログに記録して次ポーリングへ継続
    - 停止フラグ検知でループ終了

- ポートフォリオ構築（pure functions）
  - kabusys.portfolio パッケージを実装
    - portfolio_builder:
      - select_candidates（スコア降順 + tie-breaker）
      - calc_equal_weights（等金額）
      - calc_score_weights（スコア正規化、ゼロスコア時に等配分へフォールバック）
    - risk_adjustment:
      - apply_sector_cap（セクター集中制限、売却予定銘柄の除外、"unknown" セクターは上限適用外）
      - calc_regime_multiplier（market regime に応じた投下資金乗数: bull/neutral/bear）
    - position_sizing:
      - calc_position_sizes（allocation_method: risk_based / equal / score をサポート、lot_size 単位丸め、aggregate cap によるスケールダウンと切り上げロジック）
      - 手数料・スリッページを考慮する cost_buffer 引数を提供
      - 将来の拡張メモ（銘柄別 lot_size など）はコード内に TODO を残す

- ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）
    - set_process_priority(level: "high" | "normal" | "low")：Windows / POSIX の差分を吸収
    - set_cpu_affinity(cpu_count: int | None)：先頭 N コアへ固定（未対応 OS や権限不足時は警告を出しスキップ）
    - 権限不足や未対応 OS に対する安全ハンドリングを実装

- リサーチ / ファクター計算
  - kabusys.research.factor_research（DuckDB ベース）
    - モメンタム系（1M/3M/6M リターン、MA200 乖離）計算（prices_daily テーブル参照）
    - ボラティリティ / 流動性系（ATR20、avg turnover、volume ratio）計算（SQL ウィンドウ関数利用）
    - DuckDB 接続を受け取り外部 API に依存しない設計
    - 出力は日付・銘柄単位の dict リスト

- ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite から指標を集計しレポートを生成
    - 指標: 稼働率（uptime）、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg, max, P95）
    - 閾値による PASS/FAIL 判定を実装（例: 稼働率 >= 99%、P95 <= 200 ms など）
    - CLI オプションで期間（--from, --to）と DB パス指定（--db）に対応

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の制約 / 注意点
- apply_sector_cap: price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性があり、将来的に前日終値等のフォールバックを検討する旨を注記。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム依存で動作しない場合があり、その場合は警告を出して処理をスキップする。
- .env は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも記載）。
- monitoring は監視用 DB を常に sqlite_path（本番設定）で使用するため、paper_trading 環境で監視のみを分離したい場合は注意が必要。

### 将来の改善案（メモ）
- position_sizing: 銘柄別 lot_size をサポートするための lot_map 導入
- apply_sector_cap: 価格欠損時のフォールバックロジック追加
- 実行系のより詳細なメトリクス収集・テレメトリ統合
- config/*.yaml のより厳密なバリデーションスキーマ導入

---

（以降のバージョンはここに記載されます）