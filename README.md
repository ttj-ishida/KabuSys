# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ内 README。  
以下はリポジトリ内の主要コンポーネント、セットアップ方法、起動手順、ディレクトリ構成の概要です。

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境変数（主要項目）
- 使い方（起動 / 実行例）
- ディレクトリ構成（主要ファイルの説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。  
主な責務は以下の通りです。

- ExecutionEngine：発注エンジン（live / paper_trading の切替対応）
- Monitoring：実行プロセスとシステム状態を監視し、アラート／Kill Switch を発動
- Portfolio：銘柄選定、配分、ポジションサイズ計算（純粋関数）
- Research：DuckDB を用いたファクター計算・特徴量探索
- AI：ニュースセンチメント（OpenAI）を用いたスコアリング・レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティ
- 設定管理：.env の対話式セットアップ、検証ツール

設計方針として、本番データベースとペーパートレード用 DB を分離すること、外部 API 呼び出しは明示的に行うこと、ルックアヘッドバイアスを防ぐことが重視されています。

---

## 主な機能一覧

- 実行（Execution）:
  - 実際のブローカークライアントまたは MockBrokerClient（paper_trading）で注文管理
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
  - OrderManager / Reconciler による注文追跡と再整合

- 監視（Monitoring）:
  - CPU / メモリ / ディスク使用率、Execution プロセス存否、データ鮮度の監視
  - RiskMonitor によるドローダウン・ポジション上限検出
  - KillSwitch による停止フラグ生成（data/kill.flag）
  - AlertManager 経由での通知（LINE 等の統合は設定による）

- ポートフォリオ構築:
  - 候補選定（スコア降順）、等金額配分、スコア重み配分
  - セクター上限適用、レジーム乗数計算
  - ポジションサイズ計算（lot 単位丸め、aggregate cap スケーリング）

- リサーチ:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI:
  - ニュース記事のセンチメントを OpenAI（gpt-4o-mini）で評価し ai_scores に格納
  - ETF（1321）ベースの MA とマクロニュースの LLM スコアを組み合わせた市場レジーム判定

- ツール:
  - Paper Trading 検証レポート生成（成功率、レイテンシ、稼働率等）

- 設定:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）

---

## 前提条件

- Python 3.10 以上（型記法（|）を使用しているため）
- 推奨ライブラリ（環境ごとに調整してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証に必要、なくても動作可）
- SQLite（標準ライブラリ）を利用
- ネットワークからの API 呼び出しには該当 API キーが必要（OpenAI 等）

---

## セットアップ手順

1. リポジトリをクローン：
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成（推奨）：
   ```
   python -m venv .venv
   source .venv/bin/activate      # Linux / macOS
   .venv\Scripts\activate.bat     # Windows
   ```

3. 必要パッケージをインストール（requirements.txt がある場合）：
   ```
   pip install -r requirements.txt
   ```
   もし requirements.txt が無い場合、最低限次を入れてください：
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. ディレクトリ準備（data, logs 等）：
   ```
   mkdir -p data logs
   ```

5. .env の初期作成（対話式ウィザード）：
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや Kabu API パスワード等を対話的に聞いて .env を生成します。

6. 設定検証：
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

7. （任意）Paper Trading DB の初期化などはドキュメントやスクリプトに従って行ってください。

---

## 環境変数（主要項目）

主要な環境変数とデフォルト値 / 説明：

- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI の API キー（AI モジュールで必要）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を消すか（0/1）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）※ run_monitoring で参照

詳細なキーは `kabusys/config.py` と `kabusys/config_setup.py` を参照してください。

---

## 使い方（起動 / 実行例）

エントリスクリプトはモジュールとして実行できます。プロジェクトルートで以下を実行してください。

- ExecutionEngine（実行エンジン）起動：
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録されます。
  - 起動前に `data/stop_requested.flag` が存在すると起動を行いません。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンに停止シグナルが送られます。

- Monitoring（監視ループ）起動：
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（秒、デフォルト 60）。
  - 監視は常に production 用の sqlite_path（Settings.sqlite_path）を使用します。

- .env 対話的セットアップ：
  ```
  python -m kabusys.config_setup
  ```

- 設定検証：
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- Paper Trading 検証レポート（ツール）：
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB パスは `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要ファイルと概要です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数読み込み・Settings クラス
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - Execution に関する実装（発注・リスク管理・ログ）

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と永続化レイヤ
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 発注ログの整合性・遅延監視（ファイル内にあり）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の作成/クリア
  - monitoring_engine.py — 各モニタを統合して周期実行
  - alert_manager.py — 通知のラッパ（LINE 等の統合用）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・スコア並べ替え
  - position_sizing.py — 発注株数計算（risk_based / equal / score）
  - risk_adjustment.py — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ

- src/kabusys/ai/
  - news_nlp.py — ニュースの LLM によるセンチメントスコアリング（ai_scores 書込）
  - regime_detector.py — ETF MA とマクロニュースを組み合わせてレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- src/kabusys/utils/
  - logging_setup.py — ロギング初期化（コンソール + 日次ローテートファイル）
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他、config/*.yaml（システム/データ/戦略等のテンプレート）が想定されています。`validate_config.py` はこれら YAML の存在・パースチェックを行います（PyYAML がある場合）。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）での動作は慎重に行ってください。validate_config は live 環境向けの追加警告を出します。
- Kill Switch（data/kill.flag）や stop_requested.flag, execution.pid などはファイルベースでプロセス間制御を行います。これらファイルの操作によりエンジンの停止や起動制御を行えます。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離されます。ペーパートレード用 DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用します。
- OpenAI API を使用する機能（news_nlp, regime_detector）は `OPENAI_API_KEY` が必要です。API 呼び出しはリトライやフォールバック（失敗時は安全側のデフォルト）を組み込んでありますが、コストやレート制限に注意してください。
- logging はデフォルトで `logs/<app_name>.log` に日次ローテーションで出力します。ログディレクトリの権限やディスク容量管理に注意してください。

---

何か追加で README に載せたい項目（例：具体的な設定例、開発用のユニットテスト手順、CI 設定など）があればお知らせください。必要に応じてサンプル .env テンプレートやコマンドのより詳細な実例も作成します。