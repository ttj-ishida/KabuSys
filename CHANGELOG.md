# CHANGELOG

すべての重要なリリースノートはこのファイルに記録します。フォーマットは "Keep a Changelog" を準拠しています。  
バージョンは semantic versioning（MAJOR.MINOR.PATCH）に従います。

## [Unreleased]

- （現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-17
初回リリース — KabuSys の基本機能を実装しました。日本株自動売買システムのコアユーティリティ、実行/監視ランチャー、設定管理、ポートフォリオ構築、リサーチ集計、ペーパートレード検証ツールなどを含みます。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `src/kabusys/__init__.py` に定義: `__version__ = "0.1.0"`。

- 実行・監視ランチャー
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス優先度を高（"high"）に設定して起動。
    - KABUSYS_ENV が `paper_trading` の場合、MockBroker を使用し `data/paper_trading.db` に分離して記録（本番 DB と完全分離）。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）の仕組みを実装。
    - スレッドでエンジンを実行し、停止フラグ検知で安全に停止。

  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番 `sqlite_path` を使用する設計（監視 DB の初期化含む）。
    - 停止フラグ検出でループ終了、例外発生時はログ出力して次回ポーリングへ継続。

- 設定管理・ウィザード・検証
  - Settings クラス: `src/kabusys/config.py`
    - .env 自動ロード（プロジェクトルート検出、`.env` → `.env.local` の優先順、OS 環境変数の保護）。
    - 多数の設定プロパティを提供（DB パス、API トークン、paper trading DB、監視閾値、ログレベル等）。
    - `PAPER_FILL_MODE` 等の値検証と有効値チェックを実装。
    - 起動時に自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - 環境設定ウィザード: `src/kabusys/config_setup.py`
    - 対話式で .env を初期作成・更新するウィザードを追加。デフォルト値・選択肢・シークレット入力をサポート。
    - .env 書き込みテンプレートと注意書きを含む。
  - 設定検証 CLI: `src/kabusys/validate_config.py`
    - 必須環境変数・KABUSYS_ENV・ログレベル・DB パスや config/*.yaml の存在チェックを実装。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- .env パーサー強化
  - `src/kabusys/config.py` に .env 読み込みロジックを実装。
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの値に対するインラインコメント解析（`#` 前にスペースがある場合をコメント扱い）に対応。
    - ファイル読み込み時に既存 OS 環境変数を保護する仕組みを追加。

- ポートフォリオ構築ライブラリ
  - portfolio_builder: `select_candidates`, `calc_equal_weights`, `calc_score_weights`（`src/kabusys/portfolio/portfolio_builder.py`）
    - シグナル選定、等金額配分、スコア加重配分（スコア全て 0 の場合はフォールバック）を実装。
  - risk_adjustment: `apply_sector_cap`, `calc_regime_multiplier`（`src/kabusys/portfolio/risk_adjustment.py`）
    - セクター集中上限チェック（当日売却予定の除外、"unknown" セクターは制限免除）。
    - 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
  - position_sizing: `calc_position_sizes`（`src/kabusys/portfolio/position_sizing.py`）
    - risk_based / equal / score の allocation 方法を実装。
    - lot_size（単元株）丸め、max_position_pct、max_utilization 等の制約を適用。
    - aggregate cap 超過時のスケーリングと残差処理（lot 単位での再配分）、cost_buffer（スリッページ・手数料の保守的見積）に対応。

- 実行時ユーティリティ
  - process_priority: `src/kabusys/utils/process_priority.py`
    - クロスプラットフォームでプロセス優先度（high/normal/low）を設定。
    - Windows の priority class、POSIX の nice 値を適切に使い分け。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity` を実装（対応外 OS では警告を出してスキップ）。
    - 権限不足等で失敗した場合は警告ログでフォールバック。

- リサーチ / ファクター計算
  - factor_research: `src/kabusys/research/factor_research.py`
    - DuckDB 接続を受け取り、prices_daily / raw_financials を用いてモメンタム／ボラティリティ等のファクターを計算する機能を実装。
    - 計算内容: 1M/3M/6M リターン、200日移動平均乖離、20日 ATR、20日平均売買代金など。
    - データ不足時は None を用いる設計。

- ペーパートレード検証ツール
  - paper_verification_report: `src/kabusys/tools/paper_verification_report.py`
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）から集計して検証レポートを出力。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率、P95 レイテンシ、リスク却下数など。
    - パス/フェイル基準を定義（例: uptime >= 99%、fill_rate >= 90%、P95 latency <= 200ms）。
    - コマンドライン引数で期間指定（--from/--to）と DB パス上書き可能。

- DB/分析連携
  - DuckDB 接続サポート（run_execution/run_monitoring で利用）。
  - 監視 DB 初期化呼び出し `init_monitoring_db` の呼び出しを実装して冪等に監視テーブルを保証。

### 変更 (Changed)
- N/A（初回リリースのため既存変更なし）

### 修正 (Fixed)
- N/A（初回リリースのため修正履歴なし）

### 既知の注意点・運用メモ
- run_monitoring は説明の通り監視用に本番 sqlite_path を常に使用します（環境にかかわらず）。用途に応じて .env の `SQLITE_PATH` を適切に設定してください。
- .env の自動読み込みはプロジェクトルート検出に依存します。プロジェクトルートが特定できない場合は自動ロードをスキップします。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- process_priority / set_cpu_affinity は権限やプラットフォームにより適用不可となる場合があります。その場合はログに警告が出力され、処理は継続されます。
- position_sizing や risk_adjustment は現状「全銘柄共通 lot_size=100」を前提としています。将来的には銘柄別単元対応に拡張予定です（TODO コメントあり）。
- paper_verification_report の P95 計算は単純集合に基づく実装です。データ量/サンプリング方法により結果が変動する可能性があります。

### マイグレーション / 設定手順
- 初回セットアップ手順の例:
  1. .env を作成（`python -m kabusys.config_setup` を推奨）。
  2. `python -m kabusys.validate_config` で設定を検証。
  3. DB（DuckDB / SQLite）の格納先が存在するか確認または親ディレクトリを作成。
  4. 実行: 監視 `python -m kabusys.run_monitoring`、エンジン `python -m kabusys.run_execution`。
  5. Paper 検証: `python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD`。

### セキュリティ
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup の注意書きに明記）。

---

（補記）
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートはリポジトリ運用方針に従って調整してください。