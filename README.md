# KabuSys

日本株向けの自動売買・リサーチ基盤（ライブラリ兼実行スクリプト群）。  
ポートフォリオ構築、ポジションサイジング、リスク監視、発注エンジン（実運用 / ペーパートレード切替）、監視デーモン、LLM ベースのニュースセンチメント評価などを含みます。

---

## 概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。  
主な設計方針は以下の通りです。

- モジュール化された純粋関数や軽量なクラス群で構成（テストしやすい）
- 本番データベースとペーパートレード DB の分離
- ロギング、プロセス優先度、Kill Switch（フラグファイル）等の運用機能を備える
- DuckDB を用いた分析・リサーチ、SQLite を用いた運用ログ永続化
- OpenAI API を活用したニュース NLP / レジーム判定（オプション）

---

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - 実際のブローカー API または MockBrokerClient（KABUSYS_ENV=paper_trading）での発注
  - リスク管理（Rate limit / Drawdown / Position limit など）
  - OrderRepository / OrderManager / Reconciler 等の管理コンポーネント

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、PID チェック等
  - TradeMonitor: 発注ログの滞留・約定異常検出（trade_logs）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: リスク条件で stop フラグ（data/kill.flag）を作成

- Portfolio モジュール
  - 銘柄選定、等配分・スコア加重配分、ポジションサイズ計算、セクター制約、レジーム乗数

- Research（リサーチ）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ

- AI 関連
  - news_nlp: OpenAI を利用したニュースのセンチメントスコア付与（ai_scores へ書込み）
  - regime_detector: MA200 とマクロニュースを組み合わせた市場レジーム判定

- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 環境・設定の事前検証 CLI
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## 前提 / 必要環境

- Python 3.10+
- 必須 Python パッケージ（主なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
- （開発用）PyYAML は `validate_config` の YAML 検証で使用

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai
# 開発向けに requirements.txt があればそれを利用
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンしてワークツリーに移動:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化し、必要パッケージをインストール（上記参照）。

3. 初期 .env の作成（対話式ウィザード）:
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは `.env` を作成します。重要な必須項目:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、PAPER_TRADING 時）
     - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合は --strict
   python -m kabusys.validate_config --strict
   ```

5. 必要ディレクトリの作成（自動作成されるが確認しておくと安心）:
   - data/
   - logs/

6. （オプション）Kill Flag のクリア動作:
   - Settings により KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## 簡単な使い方

- Execution（発注エンジン）起動:
  - 本番 / development / paper_trading は KABUSYS_ENV で切替
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードでは専用 DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient が使われます。

- Monitoring（監視ループ）起動:
  ```
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します（または Ctrl+C）。
  - Monitoring は Settings.env に関わらず本番 sqlite_path を参照して監視情報を記録します。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI（ニューススコア / レジーム判定）:
  - OpenAI API キーが必要:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - news_nlp を呼んで ai_scores に書き込む（スクリプト経由で実行するユーティリティが利用可能）:
    - 直接呼び出す場合の Python API:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key="...")
    - regime_detector:
      from kabusys.ai.regime_detector import score_regime
      score_regime(duckdb_conn, target_date, api_key="...")

- ログ:
  - デフォルトでコンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。
  - ログディレクトリは環境変数 LOG_DIR または引数で指定可能。

---

## 主要ファイル / ディレクトリ構成

（ルート: src/kabusys 以下）

- __init__.py
- config.py
  - Settings クラス（環境変数 / .env の読み込みと解決）
- config_setup.py
  - .env の対話式生成ウィザード
- validate_config.py
  - 起動前チェック CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で制御）

- execution/
  - 発注エンジン周り（BrokerFactory、ExecutionEngine、OrderManager 等）※詳細は該当ディレクトリ参照

- monitoring/
  - monitoring_db.py        — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — CPU / メモリ / データ鮮度 / PID チェック
  - trade_monitor.py        — 発注ログ監視（滞留・約定異常など）
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — data/kill.flag 書込による停止トリガー
  - monitoring_engine.py    — 各モニタを束ねるループ
  - alert_manager.py        — 通知（LINE 等の実装想定）

- portfolio/
  - portfolio_builder.py    — 候補選定・重み計算
  - position_sizing.py      — 発注株数計算・単元丸め・aggregate cap
  - risk_adjustment.py      — セクター制約・レジーム乗数

- research/
  - factor_research.py      — モメンタム / ボラティリティ / バリュー計算（DuckDB）
  - feature_exploration.py  — 将来リターン・IC・統計サマリ

- ai/
  - news_nlp.py             — ニュースに対する LLM センチメント評価（ai_scores へ書込）
  - regime_detector.py      — MA200 とマクロニュースでレジームを判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- utils/
  - logging_setup.py        — 統一ロギング設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU アフィニティ設定ユーティリティ

- data/
  - （実行時に DB / PID / フラグファイルが置かれるデフォルト領域）
  - デフォルトファイル:
    - data/kabusys.duckdb
    - data/monitoring.db
    - data/paper_trading.db (ペーパートレード用)

---

## 重要な運用・注意点

- KABUSYS_ENV
  - development / paper_trading / live のいずれかを設定
  - paper_trading では MockBrokerClient を使用し、本番 DB と分離された PAPER_TRADING_SQLITE_PATH に記録する

- Kill Switch / Stop Flags
  - KillSwitch は重大リスク（大きなドローダウン等）で data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - run_execution / run_monitoring は data/stop_requested.flag の存在を見てループを優雅に終了します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除（本番では 0 推奨）

- DB マイグレーション
  - monitoring_db.init_monitoring_db は必要なテーブルとインデックスを冪等に作成します。既存 DB に対する簡単なマイグレーション（カラム追加）も含む

- AI / OpenAI
  - OPENAI_API_KEY が未設定の状態で AI 機能を呼ぶと例外になります。AI 機能は必須ではありません
  - API 呼出し失敗時はフェイルセーフでスコアをスキップまたは中立にフォールバックする実装です

- ログ/フォールト
  - 起動スクリプトはプロセス優先度を "high" に設定しようとしますが、権限不足や未対応 OS の場合は警告が出ます
  - 監視ループ内でのチェック例外はキャッチされ、次のポーリングで継続します（監視の堅牢性確保）

---

## サンプル .env（最小例）

以下はチュートリアル用途の最小例（実際は秘密情報は入力して保存しないでください）:

```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 開発・拡張のヒント

- 新しい機能を追加する場合は pure function / small class を心がけ、ユニットテストを書きやすくする
- DuckDB を用いた処理は接続を受け取り副作用を最小化する設計になっています
- OpenAI 連携部はリトライやレスポンス検証の実装例として参考になります

---

この README はコードベースの主要な機能・使い方・運用上のポイントをまとめたものです。実際の運用では .env と config/*.yaml（存在する場合）を適切に設定し、validate_config でチェックした上で起動してください。質問や追加項目があれば教えてください。