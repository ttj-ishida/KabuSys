# KabuSys — 日本株自動売買システム (README)

本ドキュメントは、提供されたコードベース（src/kabusys/...）に基づく README.md です。日本語でプロジェクトの概要、機能、セットアップ、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な役割は以下です。

- データ加工・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（シグナル選定・重み付け・株数算出）
- 発注実行（本番 / ペーパートレード対応）
- 監視・リスク管理（監視ループ、Kill Switch）
- AI を用いたニュースセンチメント評価・市場レジーム判定
- ペーパートレード検証レポート生成

設計上の特徴：
- 環境変数（.env）で設定を管理
- paper_trading モードでは本番 DB と完全分離（data/paper_trading.db）
- DuckDB を分析向けに、SQLite を監視・トランザクションログ向けに利用
- OpenAI（gpt-4o-mini）との連携でニュース NLP / レジーム判定をサポート

---

## 機能一覧

- 設定ウィザード: .env を対話的に作成・更新（kabusys.config_setup）
- 設定検証: .env と config/*.yaml の事前チェック（kabusys.validate_config）
- Execution エンジン起動: 実際の発注処理（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading.db に記録
  - PID ファイル・停止フラグ管理あり
- Monitoring 起動: SystemMonitor のポーリングループ（kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL で間隔上書き可
  - System / Trade / Risk 各種監視、Kill Switch 評価、Alert 発行
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ（選定・重み付け・サイズ計算）
- 研究用ファクター計算・特徴量探索（kabusys.research）
- AI モジュール:
  - news_nlp: ニュース記事を LLM でスコアリングして ai_scores テーブルへ書込
  - regime_detector: MA200 とマクロニュースを統合して市場レジーム判定
- ユーティリティ:
  - ロギングの一元化（ログローテート）
  - プロセス優先度 / CPU affinity 設定
  - Monitoring 用 SQLite の初期化・マイグレーション

---

## 必要要件（依存関係）

- Python 3.9+（コードは型アノテーション、モダンなAPIを使用）
- 必須 Python パッケージ:
  - duckdb
  - psutil
  - openai
- 任意 / 機能により必要になるパッケージ:
  - PyYAML（config/*.yaml の内容検証に利用）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

インストール例（仮）:
```bash
python -m pip install duckdb psutil openai PyYAML
```
プロジェクト配布に requirements.txt が付属する場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン／展開
   - プロジェクトルートに src/ と .env などが配置される前提です。

2. 依存パッケージをインストール
   - 例: python -m pip install -r requirements.txt
   - 無ければ個別に duckdb, psutil, openai, PyYAML をインストール

3. 環境変数を準備（.env）
   - 対話式ウィザード: 
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは .env を直接作成。主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LOG_LEVEL, LOG_DIR 等
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
     - KILL_FLAG_CLEAR_ON_START: 0|1（本番は 0 推奨）

4. 設定検証（任意だが推奨）
   ```bash
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   - data/ や logs/ などは自動作成されますが、権限等で失敗することがあるため確認してください。

---

## 使い方

### ログ設定
- 全スクリプトは共通の setup_logging() を使用：
  - デフォルトは logs/<app_name>.log（毎日ローテート、30日保持）
  - 環境変数 LOG_DIR、LOG_LEVEL で変更可能

### ExecutionEngine を起動
- 本番／ペーパーの切替:
  - KABUSYS_ENV=paper_trading → MockBroker を使用し data/paper_trading.db に記録
  - KABUSYS_ENV=live → 実ブローカークライアント（kabuステーション等）を使用
- 起動コマンド:
  ```bash
  python -m kabusys.run_execution
  ```
- 動作:
  - execution はスレッドで run_session を実行し、data/stop_requested.flag を監視して停止
  - PID は data/execution.pid に書き込まれる
  - 起動時に KILL フラグ（data/kill.flag）がある場合は起動を中止する設定あり

### Monitoring を起動
- 起動コマンド:
  ```bash
  python -m kabusys.run_monitoring
  ```
- 挙動:
  - SystemMonitor、TradeMonitor、RiskMonitor を使いポーリング（デフォルト 60秒）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔（秒）を上書き可
  - 停止は data/stop_requested.flag を作成（このファイルが存在するとループを抜ける）
  - monitoring は監視用 DB（settings.sqlite_path）へ書き込む。環境にかかわらず本番 sqlite_path を使用する設計

### Kill Switch（外部から停止シグナル送る）
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る
- Kill 条件は RiskMonitor（ドローダウンやポジション上限）等が判断
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動で kill.flag を消す（本番では推奨しない）

### Paper Trading 検証レポート
- コマンド:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- オプション:
  - --db で SQLite DB のパス指定（なければ環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）
- 出力: 稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

### AI 機能（ニュース NLP / レジーム判定）
- 要: OPENAI_API_KEY
- news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date, APIキーを渡して使用
- エラーに対してフェイルセーフ（スコアを 0 にする等）を備えていますが、API 呼び出し回数やコストに注意してください

---

## 重要なファイル・フラグの説明

- data/kill.flag: Kill Switch（作成されると ExecutionEngine の停止トリガー）
- data/stop_requested.flag: run_* スクリプトのループ停止フラグ（存在するとループを終了）
- data/execution.pid: ExecutionEngine が起動時に書き出す PID ファイル
- logs/: ログファイル格納ディレクトリ（app_name によりファイル分け）

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- DUCKDB_PATH: data/kabusys.duckdb（分析 DB）
- SQLITE_PATH: data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用 DB）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- LOG_DIR: ログ格納ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定挙動）
- KILL_FLAG_CLEAR_ON_START: 0|1（起動時に kill.flag を自動クリア）

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主なファイルと役割です。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数／設定管理（.env 自動ロード含む）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py         — ログ初期化 / ファイルローテート
    - process_priority.py      — process priority / CPU affinity
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 初期化 / 永続化レイヤ
    - system_monitor.py        — システム監視（CPU/Memory/Disk/データ鮮度）
    - trade_monitor.py         — 発注・約定監視（滞留注文、約定異常等）※実装あり
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 管理
    - monitoring_engine.py     — 各 monitor を束ねる
    - alert_manager.py         — 通知（LINE 等）管理 ※実装あり
  - execution/
    - execution_engine.py      — 発注エンジン本体（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数決定・資金配分ロジック
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py   — 将来リターン計算、IC 等
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（MA200 + Macro sentiment）
  - data/                      — デフォルトの DB ファイル / フラグファイルが置かれる想定
  - logs/                      — ログファイル出力先（default）

（上記は抜粋です。実際の repo ではさらに多くのモジュール・ユーティリティが存在します）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定を慎重に扱ってください。誤って自動クリアすると Kill Switch の安全が損なわれます。
- paper_trading モードでは実ブローカへ発注されない設計ですが、設定ミスで本番 API 情報を流用しないよう .env を分離してください。
- OpenAI 経由の処理は API コストと呼び出し制限に注意してください。リトライやクリップ等のフェイルセーフは実装されていますが、運用ルールを設けてください。
- データ取り込み・prices_daily 等の品質が低いとリサーチ結果や発注判断に影響します。DuckDB のデータ整備とデータ鮮度チェックは必須です。

---

## サンプルコマンド一覧

- .env を対話的に作成:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- Execution 起動:
  ```bash
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
- Monitoring 起動（ポーリング間隔を 120 秒にする例）:
  ```bash
  MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
- AI スコア実行（スクリプト呼び出し例: 実装側で提供される関数を直接利用）:
  - OpenAI API キーを環境に設定してからモジュール内関数を呼ぶ（スクリプト化されている場合はそれを利用）

---

この README は提供されたコード断片を元に作成しています。実運用する際は実際のリポジトリの追加ドキュメント（設計書、運用手順、requirements.txt、config/*.yaml の説明等）を参照し、テスト環境で十分に検証してください。必要であれば、この README をベースにさらに「デプロイ手順」「運用チェックリスト」などを追記できます。