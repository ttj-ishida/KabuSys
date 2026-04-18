# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群をまとめたリポジトリ用 README（日本語）。

概要・使い方・セットアップ手順・ディレクトリ構成などを簡潔にまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・調査・監視を目的としたモジュール群です。  
主な機能は次のとおりです。

- データパイプライン / DuckDB を用いたファクター計算（research）
- ポートフォリオ構築、ポジションサイズ計算（portfolio）
- 実際の注文処理を行う ExecutionEngine（execution）
  - `paper_trading` 環境では MockBroker を利用して本番 DB と分離
- 監視コンポーネント（system/trade/risk）と Kill Switch（monitoring）
- ニュースを LLM（OpenAI）で評価する AI モジュール（ai）
- 簡易レポート生成ツール（tools）
- .env ウィザード・設定検証ツール（config_setup / validate_config）

設計方針として、DB への書き込みは明示的で安全なトランザクションを使い、外部 API 呼び出しはフェイルセーフで扱います（例：OpenAI 呼び出し失敗時は代替動作）。

---

## 主な機能一覧

- ExecutionEngine 起動（run_execution）
  - 本番/ペーパートレードを環境変数 `KABUSYS_ENV` で切替
  - paper_trading では専用 SQLite（data/paper_trading.db）を使用
- 監視ループ（run_monitoring）
  - システムリソース、データ鮮度、プロセス生存、トレード状況、リスクを定期チェック
  - Kill Switch（条件を満たすと data/kill.flag を作成して Execution を停止）
- 環境設定ウィザード（config_setup）
  - 対話式で .env を生成 / 更新
- 設定検証 CLI（validate_config）
  - .env や config/*.yaml の整合性を事前にチェック
- Paper Trading 検証レポート（tools/paper_verification_report）
  - ペーパートレード DB を解析し Pass/Fail を判定
- AI モジュール
  - ニュースセンチメント算出（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- ポートフォリオ構築ユーティリティ（portfolio）
  - 候補選定、重み計算、セクターキャップ、ポジション数計算など

---

## 前提（必須 / 推奨依存ライブラリ）

少なくとも以下をインストールしてください（バージョンは仕様に合わせて適宜）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を行う場合、任意）

例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がない場合は上記を参考に必要パッケージをインストールしてください。）

---

## 環境変数 / .env

主要な環境変数（必須や重要なもの）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution の実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）

自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env を対話式で作る:
```bash
python -m kabusys.config_setup
```

作成後、設定を検証:
```bash
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

---

## セットアップ手順（推奨）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（duckdb/psutil/openai/pyyaml 等）
4. .env を作成
   - 対話式: python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（`.env.example` を参照）
5. 設定検証: python -m kabusys.validate_config
6. data/ ディレクトリやログディレクトリが自動で作成されます（logging_setup が生成）

---

## 起動 / 使い方

以下は主要なコマンド例です。プロセスはログに出力されます（デフォルト logs/<app>.log）。

- 監視ループ起動（Monitoring）
  - デフォルトポーリング間隔 60 秒。環境変数で上書き可。
  - 例:
    ```bash
    # ポーリング間隔を 30 秒に設定して起動
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に本番の sqlite_path を参照（環境に関わらず monitoring 用 DB はデフォルトの SQLite を使う設計）。

  - 停止方法:
    - プロジェクトルートの `data/stop_requested.flag` が存在するとループを抜けます（スクリプトが確認）。
    - kill.flag は ExecutionEngine への停止シグナル（Execution 側で読み取り）として使用されます（data/kill.flag）。

- ExecutionEngine 起動
  - paper_trading 環境は MockBrokerClient を使い `data/paper_trading.db` に記録して本番 DB と分離されます。
  - 例（ペーパートレード）:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 例（本番）:
    ```bash
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - 実行中は `data/execution.pid` が作成され、`data/stop_requested.flag` の存在を監視して停止します。
  - Kill Switch を有効にすると `data/kill.flag` が書き込まれ、起動中の ExecutionEngine に停止を促します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB 指定: `--db PATH` または環境変数 `PAPER_TRADING_SQLITE_PATH`

- AI 関連（OpenAI キー必要）
  - ニューススコアやレジーム判定は `OPENAI_API_KEY` を環境変数に設定するか、関数呼び出し時に API キーを渡します。
  - 例（Python REPL）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
    ```

ログ:
- デフォルトログディレクトリ: `logs/`
- アプリごとに `logs/<app_name>.log`（例: execution.log, monitoring.log）として日次ローテーションで保存されます。

---

## 重要な制御ファイル / パス

- data/stop_requested.flag — run_*.py が定期的に確認する停止フラグ（存在するとスクリプトが終了）
- data/kill.flag — Kill Switch が作成するファイル（ExecutionEngine を停止する意図）
- data/execution.pid — ExecutionEngine の PID ファイル（run_execution が使用）
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb
  - Monitoring (SQLite): data/monitoring.db
  - Paper trading (SQLite): data/paper_trading.db

---

## 開発者向け: API の簡単な呼び出し例

- ポートフォリオユーティリティ:
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_equal_weights(candidates)
  ```

- リサーチ（DuckDB 接続が必要）:
  ```python
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026,4,11))
  ```

---

## 注意事項 / 運用上の留意点

- `KABUSYS_ENV=live` のときは本番設定です。LINE 通知等の設定を必ず確認してください（validate_config は live 時に追加警告を表示します）。
- `.env` は機密情報を含むため、絶対に Git 等にコミットしないでください。
- OpenAI API を利用する機能は API コスト・レートリミットに注意してください。リトライ・バックオフ実装はありますが、呼び出しの設計に注意が必要です。
- psutil によるプロセス優先度変更は OS 権限・環境に依存します。失敗してもワーニングで継続します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — 監視ループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - data/ (実行時に生成される想定)
  - logs/ (ログディレクトリ)
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート処理)
  - execution/ (ExecutionEngine / order 管理等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は代表的なファイル一覧です。実装によりサブモジュールがさらに存在します。）

---

## 最後に

まずは .env を作成して設定検証を行い、monitoring と execution をローカルの `development` や `paper_trading` モードで動かして挙動を確認することを推奨します。運用に移す際は `KABUSYS_ENV=live` の設定と `validate_config` 実行を必ず行ってください。

不明点や追加で README に載せたい内容があれば教えてください。必要に応じて動作フロー図やコマンドのトラブルシューティングも追記できます。