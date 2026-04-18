# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群を含むリポジトリの README（日本語）。

以下はこのコードベース（`src/kabusys` 以下）の概要・セットアップ・使い方・ディレクトリ構成のまとめです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したシステムコンポーネント集です。主な責務は次の通りです。

- 注文実行エンジンの起動・管理（実際の発注またはペーパートレード）
- 監視（システム状態・注文状況・リスクの定期チェック）と Kill Switch（危険時に安全停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- リサーチ（ファクター計算・将来リターン・IC 計算）
- AI ベースのニュース解析（OpenAI を用いたニュースセンチメント -> ai_scores）
- 各種ツール（ペーパートレード検証レポート等）
- 設定管理（`.env` ウィザード、検証 CLI）

設計方針として、DB（DuckDB / SQLite）や外部 API 呼び出しを明示的に分離し、テスト容易性・フェイルセーフ性を重視しています。

---

## 主な機能一覧

- run_execution: ExecutionEngine を起動（環境に応じて実ブローカー or MockBroker）
- run_monitoring: SystemMonitor をポーリングして system_status 等を記録
- monitoring:
  - SystemMonitor (CPU/メモリ/Disk、データ鮮度、プロセス生存監視)
  - TradeMonitor (注文滞留 / 約定異常などの監視)
  - RiskMonitor (ドローダウン・ポジション上限監視)
  - KillSwitch（リスクトリガーで停止フラグを書き込む）
  - MonitoringEngine（各 Monitor を束ねる）
- portfolio:
  - 候補選定、等金額・スコア重み計算
  - セクター制約適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap、risk-based 配分）
- research:
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン、IC 計算、統計サマリー
- ai:
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント計算・ai_scores 書き込み
  - regime_detector: ETF(1321) の MA とマクロニュースを組合せたレジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB から検証レポート生成
- config:
  - Settings クラス（環境変数ラッパ）
  - config_setup.py（.env 対話式ウィザード）
  - validate_config.py（起動前チェック CLI）

---

## 前提条件 / 推奨環境

- Python 3.10+
- pip / 仮想環境（venv）利用を推奨
- 主要依存パッケージ（一例）:
  - duckdb
  - psutil
  - openai  （AI 機能を使う場合）
  - PyYAML（`validate_config` で YAML 内容を検証したい場合）
- OS: Linux / macOS / Windows（process priority の一部は OS 依存で挙動差あり）

---

## インストール（ローカル開発向け）

例:

1. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 依存パッケージをインストール（requirements があればそちらを利用）
   ```bash
   pip install duckdb psutil openai PyYAML
   ```

3. プロジェクトルートに移動（`pyproject.toml` や `.git` を基準に自動でプロジェクトルートを特定する実装があります）

---

## 環境設定（.env）

- `.env` または環境変数で設定を与えます。自動読み込みはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
- 対話式ウィザードで `.env` を生成できます:

  ```bash
  python -m kabusys.config_setup
  ```

- ウィザードで作成後、内容を検証します:

  ```bash
  python -m kabusys.validate_config
  # --strict を付けると警告も失敗扱いになります
  python -m kabusys.validate_config --strict
  ```

### 主な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時の専用 DB
- KABUSYS_ENV: development | paper_trading | live (default: development)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (AI 機能利用時に必要)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート通知用、任意)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（Kill Switch 関連）
- MONITOR_POLL_INTERVAL（run_monitoring 起動時のポーリング間隔を秒で上書き可能、デフォルト 60）

サンプル minimal `.env`:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

注意: `.env` を絶対にリポジトリにコミットしないでください（機密情報を含むため）。

---

## 初期ディレクトリ準備

ログや DB を保存するために `data/` や `logs/` が必要です。通常は自動作成されますが、手動で作る場合:

```bash
mkdir -p data logs
```

---

## 使い方（起動スクリプト・ツール）

1. ExecutionEngine を起動（本番またはペーパートレード）
   - 本番: `KABUSYS_ENV=live`（注意して使用）
   - ペーパー: `KABUSYS_ENV=paper_trading`（MockBroker を使用し `data/paper_trading.db` に記録）

   起動:
   ```bash
   python -m kabusys.run_execution
   ```

   特記事項:
   - 起動時にプロセス優先度を High に設定しようとします（失敗しても続行）。
   - `data/stop_requested.flag` が存在すると起動しない / 実行中に検知すると停止します。
   - ペーパートレードは本番 DB と分離されます。

2. Monitoring を起動（ポーリング・ログ保存・Kill Switch 判定）
   ```bash
   # ポーリング間隔を変更したい場合:
   export MONITOR_POLL_INTERVAL=30   # 秒
   python -m kabusys.run_monitoring
   ```

   特記事項:
   - Monitoring は Settings の sqlite_path（デフォルト `data/monitoring.db`）を使用してログを残します（環境にかかわらず本番 sqlite を使用する実装）。
   - `data/stop_requested.flag` を検知してループを終了します。

3. Paper Trading 検証レポート生成ツール
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # DB パスを明示する場合
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```

4. AI 機能（ニュース NLP / レジーム判定）
   - 実行前に `OPENAI_API_KEY` を環境変数または関数引数で設定してください。
   - AI 呼び出しは OpenAI の SDK を使用します。API の制限・エラーに対してはリトライ・フェイルセーフ動作があります。

---

## トラブルシューティング（よくある注意点）

- 必須環境変数が未設定 → `validate_config` で事前検出可能。
- OpenAI API キー未設定 → AI 機能は ValueError を送出します。AI 機能を使わない場合はキー不要。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合は警告（多くは起動時に自動作成されます）。
- `KILL_FLAG_CLEAR_ON_START=1` は本番環境では危険（Kill Switch を自動クリアするため）。
- ログディレクトリ作成失敗時はコンソール出力のみで継続します（ファイル出力は無効化されます）。
- process priority / cpu affinity の設定は OS と権限によって失敗することがあります（警告ログのみ）。

---

## ディレクトリ構成（主要ファイルのみ抜粋）

プロジェクトルート（src/kabusys）を想定した主要構成:

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 自動ロードロジック
  - config_setup.py          — `.env` 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py       —（監視ロジック; コードベースに依存）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       —（通知管理: LINE 等、実装に依存）
  - execution/               — Execution 関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

- データ/ログ（実行環境に作成される）
  - data/ (default)
    - monitoring.db
    - paper_trading.db
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/
    - execution.log
    - monitoring.log
    - ... 日次ローテーション（TimedRotatingFileHandler）

---

## 開発メモ / 注意

- DuckDB 接続を受け取って SQL と Python を組合せて大量データを処理する設計です（research / ai モジュール等）。
- AI モジュールは API 呼び出しで不確実性があるため、リトライ・バックオフ・バリデーション・部分書き込み（部分失敗時に既存データ保護）等の対策を組み込んでいます。
- Settings（config.py）はプロジェクトルートを `.git` や `pyproject.toml` を基準に探索して `.env` を自動読み込みします。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使うと自動ロードを抑止できます。
- 本番運用時は `KABUSYS_ENV=live` の設定に十分注意し、LINE 通知や Kill Switch 設定を確実に確認してください。

---

必要であれば、README に追加してほしい項目（例えば詳細な環境変数表、systemd / supervisor 用の起動例、CI/CD の設定例、ユニットテスト実行手順など）を教えてください。