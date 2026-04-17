# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群をまとめた Python パッケージです。戦略のファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース解析などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されます：

- 日次・リアルタイムのファクター計算およびリサーチ（DuckDB を使用）
- ポートフォリオ構築（候補選定・重み計算・サイズ計算・セクター制限）
- ExecutionEngine（発注処理）: 実発注（kabuステーション）とペーパートレードを分離
- 監視 (Monitoring): システム稼働状況/注文滞留/リスク監視、Kill Switch によるエンジン停止
- AI モジュール: ニュースセンチメント（OpenAI）・市場レジーム判定
- ユーティリティ: .env ウィザード、設定検証、プロセス優先度設定 等
- 補助ツール: Paper Trading 検証レポート生成など

設計方針として、ルックアヘッドバイアスの排除、フェイルセーフ（API失敗時は安全側にフォールバック）、DB の明確な分離（paper_trading 用 DB と本番 DB）があります。

---

## 機能一覧（主要）

- コンフィグ管理
  - .env 自動読み込み（.env, .env.local、OS 環境変数優先）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 発注 / 実行
  - ExecutionEngine（実運用 / ペーパートレード分離）
  - BrokerClientFactory により実ブローカー or MockBroker を選択
  - 注文管理・リスク管理・照合（reconciler）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、プロセス存在チェック
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウンとポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ書き込み
  - MonitoringEngine: 複数 Monitor のポーリング、アラート送出
  - SQLite に監視ログ永続化（monitoring_db）
- リサーチ / ファクター
  - momentum / volatility / value ファクター計算（DuckDB）
  - 将来リターン・IC 計算・統計サマリー
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み、リスクベースのポジションサイズ計算
  - セクター制限、レジーム乗数適用
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini）でセンチメント評価して ai_scores に書込
  - マクロニュース + ETF MA による市場レジーム判定
  - API 呼び出しは冗長性（リトライ/バックオフ）対応
- ツール
  - Paper Trading 検証レポート生成（注文成功率・稼働率・レイテンシ等）

---

## セットアップ手順

前提:
- Python 3.9+（型ヒント・モジュール仕様に合わせる）
- 仮想環境の利用を推奨

1. リポジトリをクローンして仮想環境を有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）
   - 必須: duckdb, psutil, openai
   - 開発/オプション: PyYAML（設定検証の YAML 検査に使用）
   ```bash
   pip install duckdb psutil openai
   pip install PyYAML   # 任意（config YAML 検証用）
   ```

3. .env を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは手動でプロジェクトルートに `.env` を作成してください。
   - 必須環境変数例:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （本番で OpenAI を使う場合）OPENAI_API_KEY

4. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ
   - デフォルト DB・PID・フラグは `data/` に作られます:
     - DuckDB: data/kabusys.duckdb
     - SQLite monitoring: data/monitoring.db
     - Paper trading DB: data/paper_trading.db
     - PID / flags: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env でパスを上書きしてください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。

---

## 使い方

基本的な実行方法やツールの使い方を示します。

1. ExecutionEngine の起動（発注エンジン）
   - 本番・ペーパートレードは KABUSYS_ENV に依存します。
   - ペーパートレードの場合、MockBrokerClient が使用され、data/paper_trading.db に記録されます。
   ```bash
   # 実行例（プロジェクトルートで）
   python -m kabusys.run_execution
   ```
   - 起動時に PID を data/execution.pid に書き込みます。停止は kill.flag により行います（KillSwitch 経由）。監視側が stop_requested.flag を書くと停止します。

2. Monitoring の起動（ポーリング）
   - デフォルトポーリング間隔: 60 秒。環境変数で上書き可能:
     - MONITOR_POLL_INTERVAL=30
   ```bash
   # 監視ループを開始
   python -m kabusys.run_monitoring
   ```
   - Monitoring は環境（KABUSYS_ENV）に関わらず本番用 sqlite_path を使用して監視ログを記録します。
   - 停止はプロジェクトルートの `data/stop_requested.flag` を作成することでループを抜けます。

3. .env の作成 / 更新（対話式）
   ```bash
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```bash
   python -m kabusys.validate_config
   ```

5. Paper Trading 検証レポート
   - Paper Trading の SQLite を指定して過去期間のレポートを生成します。
   ```bash
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # デフォルト DB パスは data/paper_trading.db。別パス指定:
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   ```

6. AI 機能（ニュース NLP / レジーム判定）
   - モジュール関数を呼び出して利用します（CLI ラッパーは無し）。
   - 必要: 環境変数 OPENAI_API_KEY または引数経由で API キーを渡す。
   - 例（Python スクリプト内部で）:
   ```py
   from openai import OpenAI
   import duckdb
   from kabusys.ai.news_nlp import score_news
   conn = duckdb.connect("data/kabusys.duckdb")
   score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
   ```
   - OpenAI 呼び出しはリトライ/バックオフを行い、失敗時は安全側（スコア無し / 0.0）で継続します。

7. 停止とフラグ
   - 監視ループや ExecutionEngine の停止にはフラグファイルを使用します。
     - 停止要求ループ用: data/stop_requested.flag
     - Kill Switch（ExecutionEngine 停止）: data/kill.flag
   - kill.flag は KillSwitch により書き込まれます（冪等）。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされますが、本番では 0 を推奨します。

---

## 主要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject (ペーパートレード時の約定モード)
- LOG_LEVEL (デフォルト: INFO)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START

詳細は kabusys.config.Settings のプロパティや config_setup.py を参照してください。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src 以下がパッケージ）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env ロード / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/                   — 発注エンジン関連（OrderRepository, Engine 等）
  - monitoring/
    - monitoring_db.py           — SQLite 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (アラート送出ロジック)
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 発注株数計算
    - risk_adjustment.py         — セクター制限・レジーム乗数
  - research/
    - factor_research.py         — momentum / volatility / value 等
    - feature_exploration.py     — IC / 将来リターン / 統計
  - ai/
    - news_nlp.py                — ニュースセンチメント（OpenAI）
    - regime_detector.py         — マクロセンチメント + MA によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証用レポート
  - data/                        — 実行時に生成されることが想定される（DB / PID / flag）

その他:
- config/*.yaml                  — 各種設定テンプレート（システム/データ/戦略/リスク 等）
- .env.example                   — サンプル環境変数（存在する場合）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では LINE 通知、KILL_FLAG_CLEAR_ON_START 等の設定を十分に確認してください。validate_config は本番向けの追加チェックを行います。
- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。実データが混ざらないよう注意してください。
- OpenAI を利用する機能は API キーが必要です。利用制限やコストを考慮して下さい。
- run_monitoring/run_execution はプロセス優先度を 'high' に設定しますが、環境によっては権限不足で設定に失敗する場合があります（警告のみ）。
- フラグファイルによる停止は手軽ですが、CI/監視の仕組みと合わせて適切に運用してください。

---

必要に応じて README に追記します。特定の機能（例: ExecutionEngine の詳細、OrderRepository API、AI モジュールのテスト方法）について追記を希望する場合は教えてください。