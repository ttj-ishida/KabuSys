# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システムの主要コンポーネント群を含みます。ポートフォリオ構築、ポジションサイズ算出、監視・リスク管理、ペーパートレード検証、LLM を使ったニュースセンチメント評価などの機能を備えています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 戦略（ファクター計算、特徴量探索）
- ポートフォリオ構築（銘柄選定・重み付け）
- ポジションサイズ計算（単元丸め、リスク制限、aggregate cap）
- 注文実行エンジン（本番・ペーパートレード切替）
- 監視（システム状態、注文・約定、リスクアラート、Kill Switch）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用用ユーティリティ（設定ウィザード・設定検証・ログ設定等）
- ペーパートレード検証レポート生成ツール

設計上の特徴:
- DuckDB / SQLite を用いたオンプレ/ローカル分析と監視ログの永続化
- 環境変数 / .env による構成（対話式ウィザードあり）
- ペーパートレードは本番 DB と分離（`data/paper_trading.db` がデフォルト）
- OpenAI を利用した NLP 機能はフェイルセーフ設計（API 失敗時は継続）

---

## 主な機能一覧

- 設定管理
  - .env ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行・監視
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用
    - ペーパートレード専用 SQLite に記録して本番 DB と分離
  - SystemMonitor / TradeMonitor / RiskMonitor をまとめる MonitoringEngine（`run_monitoring.py`）
    - `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視ログは SQLite（monitoring.db）へ保存
    - Kill Switch により安全に ExecutionEngine を停止可能（`data/kill.flag`）

- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分（`portfolio.portfolio_builder`）
  - セクター上限適用・レジーム乗数（`portfolio.risk_adjustment`）
  - 株数決定・aggregate cap・単元丸め（`portfolio.position_sizing`）

- リサーチ / ファクター
  - Momentum / Volatility / Value のファクター計算（DuckDB を使用）
  - 将来リターン／IC 計算、統計サマリー（Research モジュール）

- AI（OpenAI）
  - ニュース記事の銘柄別センチメントスコア化（`ai.news_nlp`）
  - ETF とマクロニュースを組み合わせた市場レジーム判定（`ai.regime_detector`）
  - OpenAI 呼び出しはリトライ・バックオフ・バリデーション・クリップ等を実装

- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必要要件（主な依存ライブラリ）

- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML（設定ファイルの内容検証に使用）
- そのほか標準ライブラリ

インストール例（仮の requirements がない場合）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. .env の作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   主要な環境変数（必須／説明）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
   - LOG_LEVEL / LOG_DIR — ログ設定
   - その他: LINE のトークンや Kill Switch 関連

4. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要 CLI / 実行例）

- 実行エンジン起動（Execution）
  - 通常起動:
    ```
    python -m kabusys.run_execution
    ```
  - 停止: プロセスは内部で `data/stop_requested.flag` を監視しています。停止フラグを置くか、Execution 側に設定される `kill.flag` を作成すると停止シーケンスが始まります。
    - 停止フラグ作成例:
      ```
      mkdir -p data
      echo "stop requested" > data/stop_requested.flag
      ```
    - Kill Switch 発動（監視が検出した場合）: `data/kill.flag` が書き込まれます。Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で削除する設定になり得ますが、本番では 0 を推奨します。

- 監視プロセス起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 注意: Monitoring は KABUSYS_ENV にかかわらず監視用の「本番 sqlite_path」を使用する実装になっています（run_monitoring の動作仕様）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート
  ```
  # デフォルト DB (data/paper_trading.db) を使う
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / レジーム判定等（モジュール呼び出し）
  - プログラム内から:
    ```py
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    # DuckDB 接続を作成して target_date を指定して呼ぶ
    ```
  - OpenAI API キーは引数で渡すか環境変数 `OPENAI_API_KEY` を使用します。

---

## 運用上の注意

- KABUSYS_ENV:
  - `development`：開発・テスト（発注なし）
  - `paper_trading`：ペーパートレード（MockBrokerClient を使用、DB は分離）
  - `live`：本番（実際に発注）
- ペーパートレードは本番 DB と分離（`PAPER_TRADING_SQLITE_PATH` を使用）
- ログ:
  - `kabusys.utils.logging_setup.setup_logging` により stdout と日次ローテートされたファイル（logs/*.log）へ出力
  - `LOG_LEVEL` / `LOG_DIR` を環境変数で設定可能
- Kill / Stop フラグ:
  - `data/kill.flag`：監視から Execution 停止を要求するためのフラグ
  - `data/stop_requested.flag`：run_monitoring / run_execution などのループを即時停止するための外部フラグ（手動停止用）
  - PID ファイル: `data/execution.pid`（Execution の PID を保持）

---

## ディレクトリ構成（主要ファイル説明）

（省略可能なファイルやテスト用スクリプトは除く、主要モジュールのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — 環境変数 / .env 自動ロード、Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py — ETF + マクロニュースで市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite を用いた監視ログ永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — （発注関連監視、コードベースに含まれる想定）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（flag ファイル書込）
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — （アラート送信ロジック、LINE など）

  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — ブローカークライアント生成（実 / Mock 切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行系の各コンポーネント

  - portfolio/
    - portfolio_builder.py — 候補選定、重み算出
    - position_sizing.py — 株数算出、aggregate cap 実装
    - risk_adjustment.py — セクター上限、レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

  - data/
    - pipeline.py, stats.py, ...（DuckDB 用データパイプライン・統計ユーティリティ）

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

- data/ — 実行時生成されるデータ（SQLite / DuckDB / flag / pid 等）
- logs/ — ログファイル（daily rotated）

---

## よくある質問 / トラブルシューティング

- Q: Monitoring が起動しているのに Execution が停止する（kill.flag が存在する）。
  - A: kill.flag は監視側が書き込みます。内容を確認し、意図的に停止させる場合は問題なし。解除するには `KILL_FLAG_CLEAR_ON_START=1` を設定して再起動するか、`data/kill.flag` を手動で削除してください（本番では自動クリアを無効にすることを推奨）。

- Q: OpenAI 呼び出しで JSON のパースエラーが出る
  - A: モデル応答のバリデーションは実装済みで、問題がある場合はそのチャンクをスキップして継続します。API キーやレスポンス内容を確認してください。

- Q: DuckDB / SQLite のテーブルが存在しないとき
  - A: 多くの初期化関数（例: `init_monitoring_db`）は冪等的にテーブルを作成します。まず監視スクリプト・Execution を起動して DB が自動生成されることを確認してください。

---

## 開発・コントリビュート

- コードは機能単位でモジュール化されています。新しい戦略やブローカープラグインは既存のインタフェース（broker factory, order repository 等）に従って追加してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。

---

README の内容は本リポジトリに含まれるコードのコメント・docstring を基に作成しています。より詳細な設計文書（PortfolioConstruction.md、StrategyModel.md 等）が別途存在する想定です。必要ならば各モジュールの使用例や API リファレンスを追加で生成します。