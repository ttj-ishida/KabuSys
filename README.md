# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ README。  
この README はコードベースから自動生成的にまとめたドキュメントです。開発者向けにプロジェクト概要、主要機能、セットアップ手順、基本的な使い方やディレクトリ構成を日本語で記載しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。  
主な目的は以下です:

- シグナルに基づく銘柄選定とポジション配分
- 発注・約定の管理（ExecutionEngine）
- システム稼働状況・注文状況・リスク監視（Monitoring）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を使った時系列集計）
- Paper Trading（ペーパートレード）モードのサポート（本番 DB と分離）
- ニュースを利用した AI（OpenAI）ベースのセンチメント評価や市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード等）

設計方針としては、DB（DuckDB / SQLite）を用いたデータ処理、外部 API は必要に応じて抽象化、フェイルセーフ（API失敗やデータ欠損時は安全側で継続）を重視しています。

---

## 機能一覧（主要コンポーネント）

- execution
  - ExecutionEngine: 実際の発注処理（本番/ペーパートレード対応）
  - BrokerClientFactory: 実行時に適切なブローカークライアントを組み立て
  - OrderManager / OrderRepository / Reconciler / RiskManager: 発注管理・再整合・リスク管理
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - TradeMonitor: 注文の滞留・約定の異常検出（ソースにより詳細実装あり）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 上記モニタを束ねるポーリングエンジン、KillSwitch と AlertManager 連携
  - monitoring_db: SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- portfolio
  - 銘柄選定・重み算出（等配分 / スコア加重）
  - セクター集中制限、レジーム乗数、株数決定（ロット単位丸め、資金スケーリング）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）解析、ファクター統計サマリ
- ai
  - news_nlp: OpenAI を使ったニュースセンチメントの銘柄別スコア化（ai_scores へ書込み）
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- utils
  - logging_setup: 一貫したロギング設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- 設定まわり
  - config_setup: .env を対話式で作成・更新するウィザード
  - validate_config: .env と config/*.yaml の起動前チェック CLI

---

## 前提 / 必要環境

- Python 3.10 以上（コードの型アノテーションで | 演算子を使用）
- duckdb
- sqlite3（標準ライブラリ）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML 検証を行う場合、任意）

パッケージはプロジェクトに requirements.txt がない場合、最低限以下をインストールしてください（例）:

```
pip install duckdb psutil openai pyyaml
```

（お使いの環境に合わせて仮想環境を作成することを推奨します）

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境作成（推奨）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux / macOS
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール:
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. .env の作成（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   - ここで JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABUSYS_ENV（development / paper_trading / live）などを設定します。
   - 本番環境では KABUSYS_ENV=live、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要に応じてデータディレクトリ作成（default）:
   - DuckDB: `data/kabusys.duckdb`
   - Monitoring SQLite: `data/monitoring.db`
   - Paper Trading SQLite (paper_trading 環境): `data/paper_trading.db`
   - ログディレクトリ: `logs/`（logging_setup が自動作成を試みます）

注意: AI 機能（news_nlp / regime_detector）を使う場合は `OPENAI_API_KEY` を環境変数に設定してください（.env に記載可）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 専用 DB（デフォルト: data/paper_trading.db）に記録します。production/live では本番 DB を使用します。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - エンジン実行中に停止させたい場合は `data/stop_requested.flag` を作成するか、Kill Switch を用いて `data/kill.flag` を書き込む仕組みがあります。
  - ExecutionEngine の PID は `data/execution.pid` に保存されます（設定により変更可）。

- Monitoring（監視ループ）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書きできます（整数、1 以上）。
  - Monitoring は常に本番 sqlite_path（.env の SQLITE_PATH）を使用して監視ログを書きます。
  - 停止検知用フラグファイル: `data/stop_requested.flag` を検出するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示的に指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```
  - デフォルト DB: `PAPER_TRADING_SQLITE_PATH` 環境変数または `data/paper_trading.db`
  - 出力は標準出力（稼働率、注文成功率、レイテンシ等）

- AI（ニューススコア / レジーム判定）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（date オブジェクト）を与えて実行。`OPENAI_API_KEY` を利用。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続、target_date を与えて market_regime テーブルへ書き込み。
  - これらはスクリプトとして直接実行できるインターフェースはなく（モジュール関数）、運用の中で呼び出されます。API キー未設定時は ValueError を送出します。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するか（開発用）

---

## 停止・kill フラグ（運用上の注意）

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止トリガーとして使用。存在を検知すると起動ループを終了します（daemon スレッドに対しても停止要求を送る実装あり）。
- data/kill.flag
  - KillSwitch（監視ロジック）によって書き込まれると ExecutionEngine に「停止要求」を送るためのファイルです。実運用では本番で容易に自動クリアされないよう注意してください（KILL_FLAG_CLEAR_ON_START=0 推奨）。
- PID ファイル
  - ExecutionEngine は PID を `data/execution.pid` に書きます（設定により変更可）。

本番環境での kill_flag 自動クリアは危険です。validate_config は `KILL_FLAG_CLEAR_ON_START` が本番で `1` の場合警告を表示します。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主なファイル/ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文監視（ソースに依存）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch ロジック
    - monitoring_engine.py — モニタを束ねる実行エンジン
    - alert_manager.py — アラート送信管理（LINE などを想定）
  - portfolio/
    - portfolio_builder.py — 候補選定、重み計算
    - position_sizing.py — 株数・リスク制約計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py — 将来リターン、IC、統計サマリ等
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - monitoring_db、execution 等の詳細なモジュールがさらに実装されています

（上記は現状の実装ファイルを要約したものです。実際のコードベースにはさらに多くの補助モジュールや抽象層が存在します）

---

## 運用上の注意事項

- 本番環境では KABUSYS_ENV=live を指定し、設定値（APIキー等）や Kill Switch の挙動を慎重に確認してください。
- .env は機密情報が含まれるため Git にコミットしないでください（config_setup にもその旨の注記があります）。
- AI（OpenAI）による自動判定は補助的な情報源として扱い、実際の発注ロジックでは慎重に設計してください。API 使用時はコスト・レート制限に注意。
- Paper Trading は本番 DB と分離されますが、本番運用に切り替える前には validate_config で設定チェックを十分に行ってください。
- データの鮮度・欠損時の動作が設計に含まれているものの、DB（DuckDB/SQLite）やデータ投入フローは別途整備が必要です。

---

## よく使うコマンド一覧（まとめ）

- .env ウィザード:
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

この README はコードのヘッダコメント／関数ドキュメントを基に作成しています。より詳細なアーキテクチャや運用手順、設定ファイル（config/*.yaml）の内容は別途ドキュメントや `config/` 下のサンプルファイルを参照してください。必要であれば、特定モジュールの詳細ドキュメント（API 仕様、例、ユースケース）も作成できますので指示ください。