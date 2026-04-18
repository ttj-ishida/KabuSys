# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

現在のリリースポリシー: まず初回リリース 0.1.0 を記録しています（コードベースから推測して作成）。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーション骨格を実装
  - パッケージ名: `kabusys`
  - バージョン: `__version__ = "0.1.0"`

- 起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite(DB) を使用して本番 DB と完全分離。
    - 実行用 PID ファイル管理（`data/execution.pid`）と停止フラグ (`data/stop_requested.flag`) による制御を実装。
    - 背景スレッドで engine を実行し、停止フラグ検知で安全に停止。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化を保証（monitoring 用テーブルの作成）。
    - 停止フラグの検知でループを終了。

- 環境設定 / 検証ツール
  - `config_setup.py`
    - 対話式ウィザードで `.env` を生成・更新するツールを実装（秘密値のマスク表示、選択肢サポートなど）。
    - 書き出し用テンプレートを提供。
  - `validate_config.py`
    - 起動前の設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- 設定・環境読み込み
  - `config.py`
    - .env 自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - `.env` と `.env.local` の読み込み順序と上書き規則（OS 環境変数の保護）を実装。
    - .env のパースは export、クォート（シングル/ダブル）、エスケープ、コメント処理に対応（より堅牢な解析）。
    - `Settings` クラスを実装し、アプリケーション設定をプロパティ経由で取得可能。各種検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を含む。
    - paper trading 用 DB パスや pid/kill flag 等のパス設定プロパティを提供。

- ログ / プロセスユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに StreamHandler (+ stdout) と TimedRotatingFileHandler（日次ローテーション、30日保存）を設定する共通ユーティリティを実装。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル決定順や log_dir 決定順をドキュメント化。
  - `utils/process_priority.py`
    - psutil を使ったプロセス優先度設定（Windows/POSIX 抽象化）を実装。
    - CPU affinity を最初の N コアに固定するユーティリティを提供（権限やプラットフォーム不足時は警告でスキップ）。

- ポートフォリオ構築ライブラリ
  - `portfolio/portfolio_builder.py`
    - シグナル候補の選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等金額配分にフォールバック（Warning）。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限の適用 (apply_sector_cap) を実装。既存ポジションのセクター別エクスポージャーを計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear マップとフォールバック挙動）。
  - `portfolio/position_sizing.py`
    - 各銘柄の発注株数計算 (calc_position_sizes) を実装。
    - allocation_method による振る舞い: "risk_based" / "equal" / "score" をサポート。
    - lot_size（単元）丸め、1銘柄上限、全体投下資金のスケーリング、残差に基づく追加配分ロジック、cost_buffer による保守的見積りを実装。
    - 価格欠損時のスキップやログ出力あり。

- 研究・ファクター計算の基盤
  - `research/factor_research.py`
    - DuckDB を利用したモメンタム等ファクター計算モジュールの骨格を実装（計算対象やウインドウ長を定義）。
    - モメンタム計算（calc_momentum）等の関数インターフェースを定義（DuckDB 接続 + target_date）。

- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成 CLI を実装（--from, --to, --db オプション対応）。
    - 指標: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計。
    - 判定基準（閾値）を定義して PASS/FAIL 判定を出力。
    - P95 計算、latency 統計、注文イベントの集計クエリ実装。

- DB 関連
  - DuckDB と SQLite の併用を想定する設計（duckdb_path / sqlite_path）。
  - 監視用 DB 初期化ユーティリティ呼び出し（init_monitoring_db）が起動スクリプトに組み込まれているため監視テーブルの整合性を保証。

### 変更 (Changed)
- なし（初回リリース相当のため）

### 修正 (Fixed)
- なし（初回リリース相当のため）

### 注意点 / 実装上の設計メモ
- 自動 .env ロードはプロジェクトルートが検出できないとスキップされる。テスト環境等で自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用可能。
- `Settings` のプロパティは多くの環境変数を必須とするため、起動前に `validate_config.py` でチェックすることを推奨。
- `process_priority.set_process_priority` と `set_cpu_affinity` は権限不足や未対応プラットフォームで失敗する可能性があり、その場合はログ警告でスキップされる設計。
- `portfolio.position_sizing.calc_position_sizes` は価格データが欠損している銘柄をスキップする。将来的にフォールバック価格の導入を検討する旨コメントあり。
- `run_monitoring` は監視 DB に対して常に production の sqlite_path を使用する（KABUSYS_ENV に依存しない挙動）。

### セキュリティ (Security)
- なし（公開コードからは具体的なセキュリティ修正は推測できません）

---

今後のリリース案（推奨）
- テストカバレッジの追加（特に position sizing、sector cap、env パーサー）
- DuckDB ベースのファクター計算の完全実装とベンチマーク
- ロギング・監視のメトリクス export（Prometheus 等）やより細かな運用アラート設計
- 単体テスト／CI 設定の導入

（この CHANGELOG は与えられたソースコードからの推測に基づき作成しています。実際の変更履歴やリリース日付はリポジトリの履歴に従ってください。）