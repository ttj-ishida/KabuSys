# KabuSys

日本株向け自動売買システム（ライブラリ / バッチツール群）。

このリポジトリは取引エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント）等の主要コンポーネントを含むモジュール群です。設計方針として「本番 DB とテスト／ペーパートレード DB の分離」「ルックアヘッドバイアス回避」「外部API呼び出しのフェイルセーフ化」などが組み込まれています。

---

## 主な機能

- ExecutionEngine（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - Broker クライアント抽象化（実口座 / Mock）
  - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て

- Monitoring（run_monitoring.py / monitoring package）
  - システムリソース監視（CPU / メモリ / ディスク）
  - Execution の PID / data 鮮度チェック
  - 注文滞留・約定異常の監視
  - ドローダウン / ポジション上限の監視と Kill Switch（data/kill.flag）発行
  - アラート通知（LINE など、AlertManager 経由）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定・重み計算（等分配・スコア加重）
  - セクター上限の適用
  - ポジションサイズ計算（ロット丸め・集計キャップ）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI モジュール（kabusys.ai）
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores へ保存
  - マクロニュース + ETF MA に基づく市場レジーム判定（regime_detector）

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 必須・推奨依存パッケージ（抜粋）

- duckdb
- psutil
- openai（AI機能を使う場合）
- PyYAML（config の YAML 検証を行う場合）
- （その他：標準ライブラリのみで動作するモジュールも多い）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```
（requirements.txt がある場合は `pip install -r requirements.txt`）

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 仮想環境を作成し依存をインストール（上記参照）。

3. 環境変数設定（.env）
   - 対話式ウィザードで .env を生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 任意 / 推奨設定:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 時の専用 DB; デフォルト: data/paper_trading.db)
     - OPENAI_API_KEY（AI機能使用時）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知）

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. 必要ディレクトリ（data 等）が無ければ作成:
   ```bash
   mkdir -p data
   ```

---

## 使い方（よく使うコマンド）

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV で本番/ペーパー切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中は data/execution.pid が作成されます。
  - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）を送る。

- Monitoring を起動（ポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を参照します（monitoring DB は環境に依存しない）。

- Kill Switch（Execution を停止させる）:
  - KillSwitch は data/kill.flag に理由テキストを書き込みます。ExecutionEngine はこのファイルの有無を見て安全に停止します。
  - KillFlag をクリアするには:
    ```bash
    rm -f data/kill.flag
    ```
  - Settings.KILL_FLAG_CLEAR_ON_START が '1' の場合、Execution 起動時に自動クリアされる可能性があります（本番では 0 推奨）。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーを環境変数に設定:
    ```bash
    export OPENAI_API_KEY=sk-...
    ```
  - スコアを生成するにはアプリ内 API（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を呼び出すか、専用スクリプト（将来的に提供）を利用します。
  - 注意: API 呼び出しはレート制限・一時失敗に対してリトライ実装がありますが、APIキーは必須です。

---

## 主要環境変数の一覧（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（data/paper_trading.db）
- OPENAI_API_KEY — OpenAI 利用時必須
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — paper_trading 時のフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

詳細は `kabusys.config.Settings` を参照してください。

---

## フラグ / PID ファイル（運用注意）

- data/execution.pid — ExecutionEngine の PID
- data/stop_requested.flag — run_execution / run_monitoring の停止トリガー（存在すると起動ループが停止）
- data/kill.flag — KillSwitch による強制停止フラグ（Execution 側で検出される）
- これらファイルは手動で作成・削除できますが、本番運用では自動化されたワークフローを検討してください。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI

  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / paper 切替）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - execution/ (発注系コンポーネント; OrderManager, BrokerFactory 等)
    - (各ファイルは発注ロジック、OrderRepository, RiskManager, Reconciler, ExecutionEngine など)

  - monitoring/
    - monitoring_db.py — SQLite 監視ログ層（テーブル作成・CRUD）
    - system_monitor.py — システムリソース / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み / 判定ロジック
    - monitoring_engine.py — 監視ループの統合／アラート発行
    - alert_manager.py — アラート送信管理（LINE 等） ※実装詳細はコード参照

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算（ロット丸め・集計キャップ）
    - risk_adjustment.py — セクターキャップ・レジーム倍率

  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算（DuckDB ベース）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー

  - ai/
    - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定

  - data/ (運用時に生成されるディレクトリ)
    - monitoring.db（または環境変数で指定された sqlite ファイル）
    - paper_trading.db（paper_trading 用 DB）
    - kabusys.duckdb（DuckDB ファイル）
    - kill.flag / stop_requested.flag / execution.pid など

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト

---

## 運用上の留意点

- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離され、PAPER_TRADING_SQLITE_PATH を使用します。安全に検証できます。
- OpenAI 等外部 API 呼び出しは失敗時にフォールバック（スコア 0.0 やスキップ）する設計ですが、APIキー・コスト・レート制限には注意してください。
- monitoring は監視 DB（sqlite）へメトリクスやリスクイベントを永続化します。DB のバックアップ・保全を検討してください。
- Kill Switch（data/kill.flag）を書き込むと ExecutionEngine を停止させるため、本番では慎重に扱ってください。
- process priority / cpu affinity の設定はプラットフォーム依存で失敗する場合があるため、ログを確認してください。

---

## 開発者向け

- 単体モジュールは外部副作用（DB 書き込みや API コール）を最小化する設計です。ユニットテスト用に依存注入（DuckDB 接続、OpenAI クライアントのラップ等）しやすく実装されています。
- LLM 呼び出し箇所にはリトライ・バリデーション・クリッピング等の安全対策を組み込んであります。テスト時は内部の API 呼び出し関数をモックして検証してください（コード中に patch 用の記述あり）。

---

必要であれば README に導入図・ER 図・API 使用例やデプロイ手順（systemd / Docker / k8s）を追加できます。どの情報を補足したいか教えてください。