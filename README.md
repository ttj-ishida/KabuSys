# KabuSys — 日本株自動売買システム

本リポジトリは日本株自動売買システム「KabuSys」の実装です。戦略・ポートフォリオ構築、発注実行、監視、研究用ファクター計算、AI（ニュース NLP / レジーム判定）などの主要コンポーネントを含みます。

注意: .env に API キー等の機密情報を格納する設計です。.env は決してバージョン管理にコミットしないでください。

---

## プロジェクト概要

- 自動発注（ExecutionEngine）と監視（Monitoring）を分離して実装
- Paper Trading（全データ・発注挙動を本番と分離）をサポート
- DuckDB / SQLite を用いたデータ解析・ログ保存
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- ポートフォリオ構築・リスク制御・ポジションサイズ計算の純粋関数群（テスト容易）
- 監視ループから Kill Switch を発動して ExecutionEngine を安全に停止可能

---

## 主な機能一覧

- ExecutionEngine
  - 本番/ペーパートレードを切り替え（KABUSYS_ENV）
  - ブローカークライアント抽象化（Mock/実装）
  - リスク管理（ポジション上限・オーバーシュート等）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセス監視
  - TradeMonitor: 注文状態の整合性や滞留注文チェック（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション数監視、dashboard 更新・risk_logs 登録
  - KillSwitch: 条件で data/kill.flag を書き込み ExecutionEngine に停止シグナルを送信
  - AlertManager 経由で通知（LINE 等の設定を利用）
- データベース
  - DuckDB: 時系列価格やファクター算出用（config にパス指定）
  - SQLite: 監視ログ・トレードログ（monitoring.db）、ペーパートレードは別 DB
- 研究・ツール
  - factor_research / feature_exploration: モメンタム・ボラティリティ・バリュー等の計算、IC 等の評価
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成
- AI
  - news_nlp: ニュース記事を集約して OpenAI でセンチメント評価、ai_scores に保存
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して市場レジーム判定を行う

---

## 前提条件 / 依存関係

主な実行に必要な Python ライブラリ（2026 時点のコード参照）:

- Python 3.9+（型注釈などを利用）
- duckdb
- psutil
- openai (OpenAI Python SDK)
- （オプション）PyYAML — config/*.yaml の検証に使用

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実運用では requirements.txt を用意して `pip install -r requirements.txt` することを推奨します。

---

## 初期セットアップ

1. 仮想環境作成・依存パッケージをインストール（上記参照）。
2. .env を作成
   - 対話式ウィザードを利用:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは .env.example を参考に手動で作成（.env は Git にコミットしない）。
3. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告もエラーにしたい場合:
   python -m kabusys.validate_config --strict
   ```
4. データディレクトリ（data/）やログディレクトリ（logs/）が自動的に作成されますが、権限に注意してください。

---

## 環境変数（主なもの）

（Settings クラスから抜粋。括弧内はデフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境・動作切替
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — Paper Trading の約定モード（デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH — Paper トレード用 SQLite（デフォルト: data/paper_trading.db）
- DB / ログ / ファイルパス
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db)
  - PID_FILE_PATH (data/execution.pid)
  - KILL_FLAG_PATH (data/kill.flag)
  - LOG_LEVEL (INFO)
  - LOG_DIR (logs/)
- その他
  - OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）

実行時の追加（短時間のポーリング間隔上書き）:
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されデフォルトへフォールバック。

停止関連:
- run_* スクリプトはプロジェクト内 data/stop_requested.flag ファイルを検出するとループを終了します。
- Kill Switch は data/kill.flag を書き込んで ExecutionEngine に停止を促します。

---

## 実行方法（主なスクリプト）

- 監視ループ起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）。
  - 監視は常に settings.sqlite_path を使用（環境に依らず本番監視 DB を見る設計）。

- 実行エンジン起動（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、Paper トレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag があれば起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンは停止処理を行います。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（プログラム内呼び出し）
  - ニュース NLP スコア生成:
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) で生成した接続
    count = score_news(duckdb_conn, target_date, api_key="your_openai_key")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="your_openai_key")
    ```

---

## ロギング

- setup_logging によりルートロガーへ
  - コンソール出力（stdout）
  - 日次ローテーションファイル（logs/<app_name>.log、デフォルト 30日分保持）
- LOG_LEVEL / LOG_DIR 環境変数で調整可能
- ログディレクトリ作成に失敗した場合はコンソールのみで継続

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ（スキーマ・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — trade_logs を用いたトレード異常検出（滞留・価格異常等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 実装（data/kill.flag 書き込み）
    - monitoring_engine.py — モニターを束ねるループ
    - alert_manager.py — 通知管理（LINE 等、実装箇所参照）
  - execution/
    - execution_engine.py — ExecutionEngine の本体
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの補助
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・合計キャップ・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py — 将来リターン・IC 等
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリング、ai_scores へ書き込み
    - regime_detector.py — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

補助ファイル:
- data/ — 実行時生成される DB / PID / flag 等（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag）
- logs/ — ログファイル（デフォルト）

---

## 運用上の注意

- .env に機密情報を格納するため、リポジトリに含めないでください。
- 本番（KABUSYS_ENV=live）では kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨。
- Monitoring は監視用 DB（settings.sqlite_path）を参照します。監視は環境設定に関わらず本番の sqlite_path を使用する設計になっています（注意）。
- Paper Trading は本番 DB とは分離され、settings.paper_sqlite_path を使用します。
- OpenAI を利用する機能は API コストが発生します。API キー管理・レート制御に注意してください。
- process_priority.set_process_priority はプラットフォームにより挙動が異なります。権限不足で設定できない場合は警告が出ます。

---

## 開発者向けメモ

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml のある場所）を起点に `.env` / `.env.local` を読み込みます。
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで有用）。
- テスト・デバッグ
  - 各純粋関数群（portfolio/*、research/*）は外部副作用が少なくユニットテストが書きやすい設計です。
  - OpenAI API 呼び出し部分は内部で呼び出しラッパーを用いているため、テスト時はモック化しやすくなっています（例: unittest.mock.patch）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は起動時に冪等的にテーブルを作成し、足りないカラムの追加（ALTER TABLE）も行います。

---

以上が README の概要です。必要であれば、運用手順書（デプロイ手順、systemd / supervisor 用のサービス定義、モニタリング・アラートの具体的設定例）や requirements.txt、サンプル .env.example を追加で作成できます。どの情報を優先して追加しますか？