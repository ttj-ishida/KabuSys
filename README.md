# KabuSys

KabuSys は日本株向けの自動売買システムの一部実装（モジュール群）です。本リポジトリは、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI を用いたニュース評価などのコンポーネントを含みます。設計方針として「本番 DB とテスト（Paper Trading）を明確に分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しは明示的に制御」などが取られています。

主な対象読者：デプロイ／運用担当、開発者、検証者

---

## 主な機能

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（paper/live 切替対応）
  - OrderManager / OrderRepository による発注・状態管理
  - Reconciler による再起動後の自動リコンシリエーション

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - MonitoringDB（SQLite）による監視ログ永続化・簡易マイグレーション
  - KillSwitch による flag ファイルベースの停止シグナル
  - AlertManager による LINE への通知（クールダウン管理）
  - Streamlit ダッシュボード（監視可視化）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額 / スコア加重配分
  - セクター上限適用、レジーム乗数
  - 株数決定（risk-based / equal / score）、単元株丸め、aggregate cap

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン（forward returns）、IC（Information Coefficient）計算
  - ファクター統計サマリ

- AI（OpenAI 連携）
  - ニュース記事のセンチメント評価（gpt-4o-mini を想定）
  - 市場レジーム判定（MA200 と LLM による合成）
  - レスポンス検証、リトライ、部分成功時の DB 保護処理

- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report.py）

---

## 依存関係（代表例）

主な Python パッケージ例：

- python >= 3.9
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他：logging 等（標準ライブラリ）

pip の requirements.txt が無い場合は上記を手動でインストールしてください。

例：
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動。

2. 仮想環境作成・依存パッケージインストール（上記参照）。

3. データディレクトリ作成（デフォルトの DB/ファイル配置）:
```
mkdir -p data
```

4. 環境変数設定
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（起動時）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須（代表例）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token が必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（Settings.kabu_api_password が必須）

任意・重要な設定:
- OPENAI_API_KEY — OpenAI API を使う機能（AI モジュール）を使う場合必須
- KABUSYS_ENV — 実行環境: `development`（デフォルト） / `paper_trading` / `live`
- PAPER_FILL_MODE — Paper Trading の約定挙動: `instant`（デフォルト） | `partial` | `never` | `reject`
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス（デフォルト `data/paper_trading.db`）
- SQLITE_PATH — 監視ログ用 SQLite パス（デフォルト `data/monitoring.db`）
- DUCKDB_PATH — DuckDB ファイル（デフォルト `data/kabusys.duckdb`）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト `data/execution.pid`）
- KILL_FLAG_PATH — KillSwitch 用フラグ（デフォルト `data/kill.flag`）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

例 .env（簡易）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxxx
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

5. （任意）データベース初期化
   - 監視用 SQLite はスクリプト内で自動的に init_monitoring_db() によるテーブル作成・マイグレーションが実行されます。手動で作る必要は通常ありません。

---

## 使い方（主要コマンド）

- Execution Engine（実際の発注プロセス）を起動
  - 本番・Paper Trading の切り替えは環境変数 KABUSYS_ENV を設定します。
  - Paper Trading（Mock Broker を使用、DB を data/paper_trading.db に分離）:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 本番（注意: 本番設定・API キー等を確認してから）:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```

- Monitoring（監視ポーリング）を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード（ブラウザで監視可視化）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  起動引数 `--db` で代替パスを指定できます（既定: data/monitoring.db）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を指定:
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  環境変数 `PAPER_TRADING_SQLITE_PATH` により DB パスを指定できます。

- AI モジュール（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（env OPENAI_API_KEY）。
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り、ai_scores / market_regime 等のテーブルへ書き込みます。

---

## 監視（Monitoring）の設計メモ

- Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します。run_monitoring では KABUSYS_ENV にかかわらず本番の monitoring DB に書き込みます（意図的）。
- MonitoringDB.init_monitoring_db() は冪等で必要テーブルとインデックスを作成し、既存 DB にカラムがない場合は ALTER TABLE による簡易マイグレーションを行います。
- KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時にこのフラグをクリアする挙動を設定可能です（Settings.kill_flag_clear_on_start）。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内部の主なファイル・モジュール構成（src/kabusys）です。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 読み込みと Settings クラス
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースセンチメント評価（OpenAI）
    - regime_detector.py          — 市場レジーム判定（MA200 + LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite 永続化層（監視ログ）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (broker_factory / order_repository 等は別ファイルに存在)
  - utils/
    - __init__.py
    - process_priority.py         — プロセス優先度設定ユーティリティ

（※コードベースにより細かいファイルは他にも存在します）

---

## 運用上の注意・ヒント

- Paper Trading と本番 DB は分離されています。Paper Trading 実行時は Settings.is_paper により paper_sqlite_path が利用されるため、本番データに影響を与えません。
- run_monitoring は監視ログに常時書き込むため、監視用 DB のバックアップやローテーションを検討してください。
- OpenAI API を使用する処理はレート制限や一時的エラーに対してリトライ機構を備えていますが、大量コール時は課金・利用制限に注意してください。
- process priority / cpu affinity の設定は psutil を用いてプラットフォーム差分を吸収していますが、権限不足で設定に失敗する場合があります（警告でスキップされます）。
- .env の自動読み込みはプロジェクトルート（.git か pyproject.toml があるディレクトリ）を基準に行われます。テスト等で自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の POLL 間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（1 秒以上の正整数を指定）。

---

## 追加情報 / 参考

- 各モジュールの docstring に設計方針や注意点が記載されています。詳細な振る舞いやパラメータはソースコードのコメントを参照してください。
- Streamlit ダッシュボードは読み取り専用モードで SQLite を開くように実装しています（起動時に DB がない場合は警告を表示します）。
- Paper Verification レポートは uptime / fill rate / send rate / latency（P95）などの指標に基づいて PASS/FAIL を判定します。CLI 引数で集計期間を指定可能です。

---

README の内容や起動方法に不明点があれば、使用したいユースケース（例：ローカル検証 / Paper Trading / 本番デプロイ）を教えてください。必要に応じてサンプル .env テンプレートや systemd / supervisor 用の起動ユニット例も提供できます。