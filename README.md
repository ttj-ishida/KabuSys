# KabuSys

日本株自動売買システムの一部を抜粋したコードベース向け README（日本語）。

この README はリポジトリに含まれる主要モジュールの概要、機能一覧、セットアップ手順、実行例、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主に次の機能を提供します。

- システム監視（プロセス生存確認、CPU/メモリ/ディスク監視、データ鮮度確認）
- ExecutionEngine（発注ロジック、リスク管理、オーダー管理）
- Paper Trading（ペーパートレード用のモックブローカー、実DBと分離）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リスク制御（ドローダウン監視、ポジション上限）
- AI連携（ニュースのセンチメント解析、マクロセンチメントを用いたレジーム判定）
- リサーチ用ファクター計算（Momentum／Value／Volatility 等）
- 運用補助ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）
- 永続化層（SQLite を用いた監視ログ / トレードログ）

設計上のポイント:
- 本番環境とペーパートレードの DB は分離（ペーパートレードでは data/paper_trading.db を使用）
- OpenAI 等外部 API 呼び出しは失敗した場合フェイルセーフで続行する設計
- 自動ロード可能な .env による設定管理（config_setup による対話式生成、validate_config による検証）

---

## 主な機能一覧

- 環境設定
  - .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行 / 監視
  - Execution 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に書き込む
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は本番の sqlite_path を使用（KABUSYS_ENV に依らず）
  - Kill Switch: data/kill.flag を書き込むことで ExecutionEngine を停止させる仕組み

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重重み計算
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイズ計算（risk_based / equal / score）

- AI（OpenAI）連携
  - ニュースセンチメント解析（kabusys.ai.news_nlp.score_news）
  - マクロ+ETF 指標を使った市場レジーム判定（kabusys.ai.regime_detector.score_regime）
  - OpenAI API キーが必須（環境変数 OPENAI_API_KEY または関数引数）

- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）等の統計ツール

- ツール
  - Paper Trading の検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 必要環境 / 依存関係

推奨 Python バージョン: 3.10+

主な Python ライブラリ（代表）:
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合）
- sqlite3（標準ライブラリ）

注意: requirements.txt はリポジトリに含まれていない場合があるため、上記パッケージを適宜インストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   - 例: git clone <repo-url>

2. 仮想環境作成と依存ライブラリのインストール
   - Python 3.10+ を用意し仮想環境を作る
   - 必要なパッケージを pip でインストール（上記参照）

3. .env の準備（環境変数設定）
   - 対話式ウィザードを使うのが簡単:
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要に必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - その他: LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）

4. ディレクトリ作成（logs / data 等）
   - ログディレクトリは自動作成されるがパーミッション確認を推奨
   - data ディレクトリは stop フラグや pid ファイルの格納先

5. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（コマンド例）

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視（Monitoring）起動
  - デフォルトは 60 秒間隔（環境変数 MONITOR_POLL_INTERVAL で上書き）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 停止方法: data/stop_requested.flag を作成するか Ctrl-C（KeyboardInterrupt）

- 実行エンジン（Execution）起動
  - KABUSYS_ENV によって挙動が変わる（paper_trading では MockBroker）
  ```bash
  python -m kabusys.run_execution
  ```
  - stop フラグ: data/stop_requested.flag を置くと起動しない / 実行中に検出して停止する

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（ライブラリ関数として利用）
  - ニューススコア生成（プログラム内から呼ぶ）
    from kabusys.ai.news_nlp import score_news
  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
  - これらは DuckDB 接続（kabusys.data で作る）と target_date、API キーを受け取る

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時のフィルモード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- PID_FILE_PATH: execution.pid 等の PID ファイルパス

---

## 動作上の注意 / トラブルシューティング

- SQLite / DuckDB のファイルパスの親ディレクトリが存在しない場合、警告が出ますが起動時に自動作成されることがあります。権限に注意してください。
- psutil を使ったプロセス優先度・CPU affinity 設定は OS に依存し、権限不足で失敗することがあります（警告ログが出ます）。
- OpenAI 呼び出しはネットワーク障害や API 制限が発生します。該当処理はリトライやフェイルセーフ（0.0 でフォールバック）を備えていますが、API キー・レート制限に注意してください。
- Monitoring は KABUSYS_ENV に関係なく sqlite_path（本番監視 DB）を使用します。テストで別 DB にしたい場合は該当コードを確認してください。
- kill.flag / stop_requested.flag / execution.pid の扱いについて:
  - KillSwitch は条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）を書き込み Execution 停止を促します。
  - run_execution.py と run_monitoring.py は data/stop_requested.flag を存在検査して起動／ループ停止を行います。
- DuckDB の executemany に空リストを渡せない歴史的な互換性制約を考慮した実装が一部にあります。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なファイル・モジュール（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings クラス、自動 .env ロード機能
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 起動前設定検証ツール
  - run_monitoring.py              — Monitoring ポーリングスクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py             — SQLite 監視 DB 永続化層
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — （トレード監視、滞留注文・約定異常検知等）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の管理
    - monitoring_engine.py         — 各 Monitor を束ねる
    - alert_manager.py             — （LINE 等への通知管理）
  - execution/
    - broker_factory.py            — ブローカークライアント生成（Mock/実ブローカー）
    - execution_engine.py          — Execution エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・上限・丸め
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py           — Momentum/Volatility/Value 等の計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py           — マクロ + ETF によるレジーム判定
    - __init__.py

（※ 上記はコードベースの抜粋であり、実際のリポジトリにはさらにファイルやサブモジュールが存在する可能性があります）

---

## 開発・テストのヒント

- unit テストやスクリプト単体実行には monitoring_engine.run_once、各モジュールの pure function（portfolio/*）が使いやすいです。
- DuckDB へは接続オブジェクト（kabusys.data.pipeline 等で生成）を渡して計算関数を呼び出します。データがない場合は None を返す設計の箇所が多いので呼び出し側でハンドリングしてください。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で検出します。テスト時に自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

この README はコードベースの説明に重点を置いています。追加で導入手順の自動化（requirements.txt / docker-compose 等）や詳細な API リファレンス、運用ガイド（systemd ユニット例、ログローテーション方針、バックアップ）を希望する場合は、その内容に合わせて追記できます。必要があれば教えてください。