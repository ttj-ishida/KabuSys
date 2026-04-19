# KabuSys

日本株自動売買システムのコアライブラリ・起動スクリプト群です。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を使ったニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を想定したモジュール群で構成されています。

- 実行エンジン（ExecutionEngine）：ブローカークライアントと連携して注文発行・管理を行う
- 監視（Monitoring）：システム稼働状況・注文状況・リスク監視を定期ポーリングしてログ／アラート・キルスイッチを制御
- ポートフォリオ構築：候補選定・重み付け・ポジションサイジング等の純粋関数群
- リサーチ：DuckDB 上の market/prices データからファクター計算・特徴量解析
- AI (OpenAI) モジュール：ニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等
- ツール：Paper Trading 検証レポート生成など

---

## 主な機能一覧

- 環境管理
  - 対話式 .env ウィザード（python -m kabusys.config_setup）
  - 起動前設定検証（python -m kabusys.validate_config）
- 実行（Execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - Paper Trading 時は MockBroker を使用し DB を分離
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセスの稼働チェック
  - 注文の滞留、約定異常、データ鮮度の監視
  - Kill Switch の実装（ファイルによる停止シグナル）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア重み、リスクベースのポジションサイジング
  - セクター制限・レジーム乗数適用
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込み
  - マクロニュースと ETF MA を使って市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（期間指定可）

---

## 必要環境（推奨）

- Python 3.10+
- 以下の Python パッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に推奨だが必須ではない）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（本番で API を使用する場合）

（requirements.txt が無い場合は上記を個別にインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境の作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 対話式 .env 作成
   ```
   python -m kabusys.config_setup
   ```
   - このウィザードは .env を生成／更新します。秘密情報（API トークン等）はマスク入力できます。
5. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱いになります。

注意:
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- KABUSYS_ENV は `development` / `paper_trading` / `live` のいずれか
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動の .env 読み込みを無効化できます（テスト時等）

---

## 起動方法（使い方）

- 実行エンジン（ExecutionEngine）
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db（または env の PAPER_TRADING_SQLITE_PATH）に記録します。
    - `_EXECUTION_PID`（data/execution.pid） を使って PID 管理します。
    - data/stop_requested.flag が存在すると起動／ループ中に停止します。

- 監視ループ（Monitoring）
  - 起動:
    ```
    python -m kabusys.run_monitoring
    ```
  - 挙動:
    - デフォルト 60 秒間隔でポーリング（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
    - 監視は本番 sqlite_path（Settings.sqlite_path）を常に使用します（環境にかかわらず）
    - data/stop_requested.flag を監視して停止します

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

- ライブラリ API（簡単な例）
  - ポートフォリオ関数:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```
  - AI スコアリング（ニュース）:
    ```
    from kabusys.ai import score_news
    # duckdb_conn: DuckDB 接続, target_date: datetime.date, api_key: str（省略時は OPENAI_API_KEY 環境変数）
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
- データベース
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: デフォルト logs/
- AI / OpenAI
  - OPENAI_API_KEY: OpenAI API キー
- 監視／操作
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（"1" の場合）
  - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で取得可能
- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject

詳しい扱いは kabusys.config.Settings クラスのプロパティを参照してください。

---

## 設定・運用上の注意

- KABUSYS_ENV=live（本番）の場合、設定ミスによる誤発注を防ぐために validate_config の警告を重視してください。
- Kill Switch: RiskMonitor が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止させる仕組みがあります。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動でクリアされるため）。
- 監視ループは Monitoring の SQLite DB（Settings.sqlite_path）を使用します。監視と Execution の DB が分離されている設計に注意してください（paper_trading は実行エンジン側で別 DB を使用）。
- ログはデフォルトで logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリ作成に失敗した場合はコンソールのみ出力されます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下中心の抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・Settings
    - config_setup.py                # .env ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py # Paper Trading レポート生成
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
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py (not listed fully here)
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py (実装に依存)
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                      # 実行ロジック（OrderManager 等）
    - data/                           # データディレクトリ（logs/.env ではない）
    - config/                         # yaml 設定テンプレート（system_config.yaml 等）

※ 上の構成は抜粋です。詳細はソースツリーを参照してください。

---

## 開発者向けメモ

- 自動で .env を読み込むロジックは config.py 内に実装されています。テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ設定は kabusys.utils.logging_setup.setup_logging を使用して統一してください（Stream + 日次ファイルローテーション）。
- プロセス優先度や CPU affinity は psutil に依存します。権限不足や未対応 OS の場合は警告を出してスキップされます。
- OpenAI 呼び出し部分はネットワークエラーや 5xx を考慮して指数バックオフ等のリトライロジックを実装しています。テスト時は内部の _call_openai_api をモックしてください。

---

## よくある操作コマンド（まとめ）

- .env を対話作成:
  ```
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```
- 監視ループ起動:
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README に「Docker による起動」「systemd サービス定義」「CI / テストの実行方法」などの追加セクションを追記します。どの情報を追加しますか？