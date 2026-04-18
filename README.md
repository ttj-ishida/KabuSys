# KabuSys

日本株自動売買システム（ライブラリ & 起動スクリプト群）

この README はコードベース（src/kabusys 以下）に基づくプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能を提供する Python パッケージです。

- データ取得・集計（DuckDB ベース）
- ファクター計算・リサーチ（モメンタム、ボラティリティ、バリュー等）
- ポートフォリオ構築（候補選定・重み計算・サイズ算出）
- Execution Engine（発注管理・リスク管理） — 本番 / ペーパートレード切替対応
- Monitoring（システム監視、トレード監視、Kill Switch）
- AI 支援（ニュース NLP による銘柄センチメント、レジーム判定）
- 各種ツール（ペーパートレード検証レポート等）
- 環境設定ウィザード / 設定検証 CLI

設計方針の一部:
- DuckDB を分析基盤に利用、SQLite を監視 / 発注ログに利用
- 本番とペーパートレードの DB を分離
- LLM 呼び出し（OpenAI）は安全なリトライ・バリデーションを実装
- ルックアヘッドバイアスを避ける実装（日時参照に注意）

---

## 主な機能一覧

- 環境設定
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- 実行コンポーネント
  - Execution Engine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
  - Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
    - ポーリングで System / Trade / Risk Monitor を実行、Kill Switch 評価
- モジュール
  - portfolio: 候補選定、重み計算、株数計算、セクター制限、レジーム乗数
  - research: ファクター計算（momentum, volatility, value）、特徴量探索（IC 等）
  - ai: ニュース NLP（OpenAI を使った銘柄スコア付与）、レジーム判定
  - monitoring: DB 永続化、監視ロジック、アラート、Kill Switch
  - utils: ロギング設定、プロセス優先度設定 等
- ツール
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発環境）

以下は一般的なセットアップ例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必須パッケージをインストール（requirements.txt があればそれを使うことを推奨）
   必要な主な外部依存：
   - duckdb
   - psutil
   - openai
   - PyYAML（設定検証で任意）
   例（pip）:
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合は `.env.example` を参照して `.env` を作成してください（このコードベースは自動で .env を読み込みます）。
   - 自動ロードはプロジェクトルートが `.git` または `pyproject.toml` を基準に検出される場合に有効です。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 設定の検証
   ```
   python -m kabusys.validate_config
   # 警告をエラーとして扱う場合:
   python -m kabusys.validate_config --strict
   ```

注意:
- OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定してください。
- 本番で使用する重要環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は必須です。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで必要）
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1 はクリア）

---

## 使い方（主要スクリプト）

### 環境設定ウィザード
対話式に .env を作成・更新します。
```
python -m kabusys.config_setup
```

### 設定検証
起動前に必須変数やパス、config/*.yaml を確認します。
```
python -m kabusys.validate_config
# strict モード（警告も失敗扱い）
python -m kabusys.validate_config --strict
```

### Execution Engine 起動
ExecutionEngine を起動します。KABUSYS_ENV により挙動が変わります。
- 本番（live）や development では設定に従って実際のブローカークライアントが使用されます。
- paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db を使います。
```
python -m kabusys.run_execution
```
停止方法:
- 同スクリプトは data/stop_requested.flag を監視し、存在すればエンジンを停止します。
- Kill Switch（risk により発動）で data/kill.flag が書き込まれると安全に停止します。

### Monitoring 起動
System / Trade / Risk Monitor を定期実行するプロセスです。MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒、デフォルト 60）。
```
# デフォルト（60秒）
python -m kabusys.run_monitoring

# ポーリング間隔を 30 秒に上書き（環境変数）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
注意:
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。

### Paper Trading 検証レポート
ペーパートレードの検証レポートを生成します。
```
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11
```
--db を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH`、さらに省略すると `data/paper_trading.db` が使われます。

### AI モジュール（プログラム呼び出し）
- ニュース NLP（銘柄スコア更新）
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - OpenAI API キーは `api_key` 引数または `OPENAI_API_KEY` 環境変数を使用
- レジーム判定
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

（これらはモジュール関数なのでスクリプトから import して呼び出すか、別途 CLI を用意して使用します）

---

## ロギング

- ログ設定ユーティリティ: `kabusys.utils.logging_setup.setup_logging(app_name, log_dir=None, level=None)`
- デフォルト: ログは stdout に出力され、ファイルは `logs/<app_name>.log`（日次ローテート、30日保持）に出力されます（ログディレクトリは自動作成を試みます）。

---

## 停止フラグ / Kill Switch

- プロセスを外部から停止したい場合や ExecutionEngine に停止を伝えたい場合、プロジェクト内 `data/stop_requested.flag` を作成してプロセスに検知させます（run_execution, run_monitoring はこのファイルを監視します）。
- Kill Switch はリスク条件（ドローダウン、ポジション上限など）により `data/kill.flag` を書き込みます。これにより ExecutionEngine は安全に停止されます。
- `KILL_FLAG_CLEAR_ON_START` が `1` の場合は起動時に `kill.flag` を自動クリアします（本番環境では `0` を推奨）。

---

## ディレクトリ構成（主要ファイル・モジュール）

src/kabusys の主要構成:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（自動 .env ロードロジック含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring 起動スクリプト
  - execution/                 — 発注エンジン関連（broker, engine, order_manager 等）
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py               — OpenAI を用いたニュースセンチメント
    - regime_detector.py        — レジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                       — 実行時に使う DB / フラグファイル（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）

（上記は主要ファイルの抜粋です。細かい補助モジュールや実装ファイルはソースを参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `.env` の秘匿情報を厳重に管理し、`.env` を Git にコミットしないでください。
- `LOG_DIR` の書き込み権限や DB（DuckDB / SQLite）ファイルのバックアップ方針を事前に確認してください。
- OpenAI を使う処理はコストが発生し得ます。利用頻度とバッチサイズを考慮してください。
- Monitoring は常に本番の監視 DB を参照します。テスト・開発時は環境設定（SQLITE_PATH 等）に注意してください。
- Kill Switch と `KILL_FLAG_CLEAR_ON_START` の設定は本番では慎重に（自動クリアは危険）してください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  ```
- Execution 起動:
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

何か追加で README に含めたい情報（例: 依存関係の正確なバージョン、デプロイ手順、systemd サービス定義例、CI 設定など）があれば教えてください。必要に応じて追記・調整します。