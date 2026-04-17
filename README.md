# KabuSys

日本株向けの自動売買システム（ライブラリ/サービス群）の軽量実装。  
本リポジトリには、注文実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、ポートフォリオ構築・リスク制御、リサーチ（ファクター計算）、およびニュース NLP / レジーム判定のための AI モジュールなどが含まれます。

---

## プロジェクト概要

KabuSys は以下の機能を組み合わせて自動売買システムの運用を支援します。

- ExecutionEngine の起動・実行（本番 / ペーパートレード対応）
- 監視ループ（System / Trade / Risk モニタ）と Kill Switch
- 監視ログの永続化（SQLite）および分析用 DuckDB
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出、セクター上限）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- ニュースの NLP によるセンチメント評価（OpenAI を用いる）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、Paper Trading レポート生成）

設計方針として、ルックアヘッドバイアスの回避、冪等性（DB マイグレーション含む）、フェイルセーフ動作（API エラー時のフォールバック）を重視しています。

---

## 主な機能一覧

- run_execution: ExecutionEngine をスレッドで起動（KABUSYS_ENV に応じて MockBroker 使用）
  - KABUSYS_ENV=paper_trading 時は paper DB（data/paper_trading.db）に完全分離して記録
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）
  - 監視ログは常に本番 sqlite_path を使用（KABUSYS_ENV に依存しない）
- Monitoring:
  - SystemMonitor: CPU / メモリ / ディスク / PID ファイル / データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じて data/kill.flag を作成し ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
- Portfolio:
  - 候補選定（スコア順）、等重・スコア重み、セクター制限、ポジションサイズ算出（単元丸め）
- Research:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、ファクター統計
- AI:
  - news_nlp.score_news: OpenAI でニュースを集約し銘柄ごとにセンチメントを算出して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA200 乖離 + マクロニュースを LLM で評価し市場レジームを判定
- ツール:
  - .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

---

## 前提 / 必要環境

- Python 3.9+（型注釈や一部ライブラリの互換性を想定）
- 推奨パッケージ（requirements.txt が無い場合は以下を個別インストールしてください）
  - psutil
  - duckdb
  - openai
  - requests
  - PyYAML（config 検証でオプション）
- システム上での権限:
  - psutil の一部操作（nice, cpu_affinity 等）は権限が必要な場合があります。失敗時は警告を出してスキップします。

例（pip）:
```
pip install psutil duckdb openai requests PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Unix 系） / .venv\Scripts\activate（Windows）
3. 必要パッケージをインストール（上記参照）
4. 環境変数設定
   - .env を作成する方法（おすすめ）:
     - python -m kabusys.config_setup
     - 対話式で .env を生成します（.env は絶対に Git にコミットしないでください）
   - もしくは環境変数を直接設定してください。
5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付与（警告があれば exit(1)）

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH: 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db） ← run_monitoring は常にここを参照
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効。production では "0" 推奨）
- ペーパートレード関連
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector で使用
- その他
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方（コマンド例）

- .env ウィザード（推奨）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV に依存します
  - ペーパー: KABUSYS_ENV=paper_trading を指定すると MockBroker を使い paper DB に記録されます
  ```
  python -m kabusys.run_execution
  ```
  - スクリプトは data/stop_requested.flag を検知すると優雅に停止します。
  - 実行時、data/execution.pid に PID を書きます（設定に応じたパス）。

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に settings.sqlite_path（本番 sqlite_path）を参照します（KABUSYS_ENV にかかわらず）。
  - 停止は data/stop_requested.flag を作成するとループが終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ニュース NLP / レジーム判定（プログラムから呼び出す）
  - news_nlp:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```
  - regime_detector:
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,10), api_key="sk-...")
    ```

---

## 停止・Kill Switch

- 実行停止（優雅停止）
  - run_execution / run_monitoring はプロジェクトルート下の data/stop_requested.flag を検知すると終了します。
  - KillSwitch（監視経由）: リスク条件（ドローダウン超過やポジション上限超過）により data/kill.flag を書き込み、ExecutionEngine 側で検出して停止します。
- kill.flag の既存状態を自動クリアしたい場合は .env の KILL_FLAG_CLEAR_ON_START=1 を設定できますが、本番では推奨されません。

---

## データベース / ファイル（既定値）

- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- 実行 PID: data/execution.pid
- 停止フラグ: data/stop_requested.flag
- Kill Switch フラグ: data/kill.flag

---

## トラブルシューティング & 注意点

- psutil による優先度設定や CPU affinity は OS と権限に依存します。設定に失敗した場合は警告ログのみで継続します。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API エラー時はフェイルセーフとして処理をスキップまたはデフォルト値にフォールバックしますが、精度に影響します。
- run_monitoring は監視テーブルの初期化（init_monitoring_db）を行います。既存 DB に対するマイグレーションも組み込まれています（例: カラム追加）。
- config/*.yaml の内容検証には PyYAML が必要です。未インストール時は警告が出て検証はスキップされます。
- .env は機密情報を含むので絶対に VCS にコミットしないでください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py         — SQLite 永続層（テーブル初期化 / API）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                  — ExecutionEngine 関連（注文管理等、参照あり）
    - (OrderRepository, OrderManager, ExecutionEngine 等)
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
  - utils/
    - process_priority.py

（上記は本 README に含まれているソースコードファイルをもとに抜粋しています。実際のリポジトリではさらに補助スクリプトやモジュールが存在する可能性があります。）

---

## 開発者向けメモ

- テスト: 各モジュールは依存関係を極力限定しているためユニットテストが書きやすい設計です。OpenAI 呼び出し等は内部関数をパッチしてモック可能です（例: unittest.mock.patch）。
- ロギング: logging.basicConfig(level=logging.INFO) を多くの CLI が使っています。環境変数 LOG_LEVEL で変更可能です。
- DB マイグレーション: init_monitoring_db は簡易的なマイグレーションロジックを含みます。大きなスキーマ変更の際は注意してください。

---

この README はリポジトリ内の主要なモジュール（監視、実行、ポートフォリオ、研究、AI、ツール群）の使い方と設定項目をまとめたものです。詳細な実装や追加の CLI は各モジュールの docstring を参照してください。ご不明点があれば、どの機能についてさらに詳しく知りたいか教えてください。