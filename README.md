# KabuSys

日本株向けの自動売買システム（KabuSys）のリポジトリ内 README（日本語）。

本ドキュメントはソースコードを基に、導入手順・実行方法・ディレクトリ構成などをまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。主な要素は以下です。

- ExecutionEngine: 発注・注文管理・リスク管理を行うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文の監視、Kill Switch による安全停止
- Research: DuckDB 上でファクター計算・特徴量探索を行うモジュール
- Portfolio: 銘柄選定・重み付け・株数計算などのポートフォリオ構築ロジック
- AI: ニュースの NLP スコアリング（OpenAI を利用）や市場レジーム判定
- Tools: ペーパートレード検証レポートなどのユーティリティ
- Config ツール: 対話式設定ウィザード・設定検証 CLI

設計方針の一部:
- 本番 DB とペーパートレード DB を分離
- ログは統一インターフェース（コンソール + 日次ローテート）で出力
- OpenAI 呼び出しはリトライ等のフェイルセーフ実装あり
- ルックアヘッドバイアスを避ける設計（日時参照に注意）

---

## 主な機能一覧

- 環境管理
  - .env 読み込み（自動ロード）と対話式ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行エンジン（run_execution）
  - 本番 / paper_trading 切替
  - Broker クライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler の統合
  - PID ファイル管理・停止フラグ対応
- 監視（run_monitoring / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor の統合ポーリング
  - MonitoringDB（SQLite）への永続化
  - KillSwitch による ExecutionEngine 停止トリガー
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能
- 研究（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリ
- ポートフォリオ構築（portfolio）
  - 候補抽出、等重／スコア重み付け、ポジションサイズ計算、セクター制約、レジーム調整
- AI（ai）
  - ニュースを OpenAI で評価して ai_scores に書き込み（news_nlp）
  - マクロニュースと ETF MA 乖離から市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提／依存パッケージ

最低限必要なパッケージ（例）:

- Python 3.9+（ソース内の型ヒント等より想定）
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合）
- そのほか標準ライブラリ

インストール例:
```
pip install duckdb psutil openai PyYAML
```

※ 実際の運用では requirements.txt を整備してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 必要な Python パッケージをインストール（上記参照）
3. .env を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - もしくはプロジェクトルートに `.env` を手動作成（例は下記）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ準備（必要に応じて自動作成されますが手動で作ることも可能）
   - デフォルト DB パス: data/monitoring.db（SQLite）、data/kabusys.duckdb（DuckDB）
   - PID・フラグ: data/execution.pid、data/kill.flag、data/stop_requested.flag
6. OpenAI を使う場合は API キーを環境変数に設定:
   ```
   export OPENAI_API_KEY="sk-xxxx..."
   ```

.env のサンプル（抜粋）
```
# 必須
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here

# オプション / デフォルト
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Kill Switch 動作
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動・代表コマンド）

- Execution エンジンを起動:
  - 通常実行（環境変数で切替）
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、data/paper_trading.db に記録されます:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - エンジンは data/stop_requested.flag（プロジェクトルートの data 配下）を検知すると停止します。
  - 実行時に data/execution.pid が作成されます。

- Monitoring（監視）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可能:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - Monitoring は Settings.sqlite_path（通常 data/monitoring.db）を利用します（環境に関わらず本番 sqlite_path を使用する挙動）。
  - 停止フラグ: run_monitoring はプロジェクト data/stop_requested.flag を監視し、存在するとループを抜けます。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能
  - ニュース NLP / レジーム判定は OpenAI API キーが必要です（OPENAI_API_KEY）。
  - 該当関数:
    - kabusys.ai.score_news(...)
    - kabusys.ai.regime_detector.score_regime(...)

- 停止・Kill Switch
  - KillSwitch は risk モニタ等の条件で data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して停止します。
  - 開発・手動で停止する場合は data/stop_requested.flag を作成することで run_execution/run_monitoring を安全停止できます。

---

## ロギング

- ログ出力は kabusys.utils.logging_setup.setup_logging を通じて統一管理されます。
- デフォルト:
  - コンソール出力（stdout）
  - ファイル出力: logs/<app_name>.log（日次ローテーション・30 日分保持）
- 環境変数:
  - LOG_LEVEL（例: DEBUG / INFO / WARNING / ERROR）
  - LOG_DIR（ログ保存先ディレクトリ）

---

## 注意点 / 運用上のポイント

- run_monitoring は MonitoringDB（Settings.sqlite_path）に書き込むため、Monitoring は本番 DB を参照する設計になっています（環境に関わらず sqlite_path を使用）。ペーパートレードでは Execution 側のみ paper_sqlite_path を使用して DB を分離します。
- PID ファイルと stop/kill フラグはファイル存在チェックで実装されています。外部システムから停止命令や監視を行う際はこれらファイルを利用してください。
- OpenAI API 呼び出しに関しては 429 / ネットワーク断 / タイムアウト / 5xx 対応でリトライ実装がありますが、API キーやコストには注意してください。
- DuckDB の SQL 実行や executemany に関するバージョン依存の取り扱い（空リスト不可など）に注意しています。DuckDB のバージョン互換性に注意してください。
- 設定ファイル（config/*.yaml）や .env を Git にコミットしないでください（機密情報を含むため）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py       — （ファイル中で参照あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （ファイル中で参照あり）
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（上記はコードベースから抽出した代表的なモジュールです。詳細はソースコードを参照してください。）

---

## よくある操作メモ

- 強制停止 / 再起動運用フロー例:
  1. 停止を要求する場合:
     - プロジェクトルートの data/stop_requested.flag を作成（任意の内容）
  2. ExecutionEngine が停止したら stop フラグを削除する
  3. 再起動は通常通り python -m kabusys.run_execution を実行
- Kill Switch をクリアしたい（本番で慎重に）:
  - data/kill.flag を削除するか、設定で自動クリアを有効にした起動（KILL_FLAG_CLEAR_ON_START=1）を行う（本番では推奨しない）

---

## 参考 / 次のステップ

- .env を作成したら必ず:
  ```
  python -m kabusys.validate_config
  ```
  で検証してください。
- ペーパートレードで動作を確認後、本番（KABUSYS_ENV=live）へ移行することを推奨します。ライブ移行時は LINE 等の通知設定・Kill Switch 設定を十分に確認してください。

---

必要であれば README に以下を追加します:
- requirements.txt のサンプル
- systemd / Supervisor 用のサービス定義例
- よくあるトラブルシュート集（ログパス・DB マイグレーション等）

追加希望があれば教えてください。