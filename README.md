# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などを含む自動売買プラットフォームのコア部分です。

## 概要

- ExecutionEngine（実売買／ペーパートレード）とそれを補助する各コンポーネント（注文管理、リスク管理、再整合など）。
- Monitoring（system/trade/risk の監視）、Kill Switch（条件に応じた停止）、アラート連携。
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング・セクター制限など）。
- リサーチ用ファクター計算＆特徴量解析（DuckDB を利用）。
- AI モジュール（OpenAI を用いたニュース NLP / 市場レジーム判定）。
- ユーティリティ：環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定 等。

## 主な機能

- 実行エンジン（paper_trading / live / development モードの切替）
  - paper_trading 時は MockBrokerClient を利用し、本番 DB と分離して `data/paper_trading.db` に記録
  - PID ファイル・停止フラグにより安全停止をサポート
- 監視（Monitoring）
  - システム状態（CPU/MEM/DISK）、Execution プロセス状態、データ鮮度を定期記録
  - トレードログやリスクログの収集
  - Kill Switch による自動停止（ドローダウンやポジション上限超過など）
- ポートフォリオ構築（純粋関数）
  - 候補選定、等金額／スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC 計算、ファクター統計サマリー
- AI
  - ニュース記事のセンチメントスコアリング（OpenAI）
  - マクロニュースとETF MA を組み合わせた市場レジーム判定
- 開発支援ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

## 要件（例）

最低限必要な Python パッケージ（プロジェクトに含まれている機能を使うには）：

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能利用時)
- PyYAML（設定ファイル検証で YAML を使う場合。任意）

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt は本リポジトリに含まれていないため、実行環境に応じて必要パッケージをインストールしてください。

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. 仮想環境を作成して必要パッケージをインストール
3. 環境変数設定
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env` を手動で作成（.env.example を参考に）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も失敗にしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ（data/）やログディレクトリ（logs/）が自動作成されますが、権限や配置を事前に確認してください。

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live (default: development)
- OPENAI_API_KEY: OpenAI 利用時に必須
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視 DB のデフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト `data/paper_trading.db`）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant, partial, never, reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト `logs/`）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルト `data/execution.pid`, `data/kill.flag`
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

## よく使うコマンド（実行例）

- ExecutionEngine 起動（モードは KABUSYS_ENV に依存）:
  ```
  python -m kabusys.run_execution
  ```
  - paper_trading の場合は .env で KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し `data/paper_trading.db` に記録されます。

- Monitoring 起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

## 停止・管理

- 実行／監視プロセスの停止には以下が使われます:
  - data/stop_requested.flag: run_monitoring / run_execution が定期的に存在をチェックし、存在すると安全にループを抜けます（stop フラグ）。
  - Kill Switch（kill.flag）: 監視ロジックにより条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止を促します。
- ExecutionEngine は起動時に `data/execution.pid` を書きます。デバッグや外部からプロセス監視に使用可能です。

## モジュール説明（ディレクトリ構成）

リポジトリの主要ファイル / ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視 DB 層（スキーマ定義・CRUD ユーティリティ）
    - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス存在チェック
    - trade_monitor.py — （トレード監視、滞留注文・約定異常検出 等）※詳細ファイル参照
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 複数モニタを束ねる実行ループ（テスト用 run_once / 本番用 run）
    - alert_manager.py —（アラート送信ロジック。LINE など）
  - execution/
    - execution_engine.py — 実行エンジン本体（セッション管理、注文ライフサイクル）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 実行に必要なコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数決定・資金割当ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計要約
  - utils/
    - logging_setup.py — 共通ログ設定（コンソール + 日次ローテートファイル）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記以外のファイルも多数あり。各モジュールの docstring に設計と挙動の説明があります）

## 注意点 / 運用上のポイント

- Monitoring は常に本番の SQLite（Settings.sqlite_path）を参照します。環境変数にかかわらず監視 DB は本番ファイルを使う想定です。
- Execution（発注）と Monitoring の DB を分離するため、paper_trading モードでは発注関連データは `PAPER_TRADING_SQLITE_PATH` に保持します。
- AI 機能（news_nlp / regime_detector）を使うには OpenAI API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライやフォールバックを実装していますが、API 利用料やレート制限に注意してください。
- ログはデフォルト `logs/` に出力され、日次ローテート（30日保持）されます。権限とディスク容量に注意してください。
- stop/kill フラグはフラグファイル方式を採用しており、運用者が直接ファイルを作成／削除してプロセス制御を行えます。KILL_FLAG_CLEAR_ON_START 環境変数が有効だと起動時に自動で kill.flag をクリアします（本番では 0 を推奨）。

## トラブルシューティング

- ログが出力されない / ファイルが作成されない
  - LOG_DIR 環境変数、または実行ユーザーのファイル書き込み権限を確認してください。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- Execution がすぐ終了する / 起動しない
  - `data/stop_requested.flag` や `data/kill.flag` の存在を確認してください。
  - validate_config で必須環境変数が満たされているか確認してください。
- AI 関連が失敗する
  - OPENAI_API_KEY が設定されているか。ネットワーク・レート制限によりリトライやフォールバック（0.0）する実装です。

## 開発・拡張ポイント（簡単メモ）

- DuckDB を通じたリサーチ関数は DB 接続を受け取り純粋関数を返す設計。テストが容易です。
- portfolio/*.py は外部 DB 参照を持たない純粋関数群なので単体テストを作りやすいです。
- OpenAI 呼び出し部分はテスト時に差し替え（patch）可能なように設計されています。

---

詳細な API/内部実装や各モジュールの使用例は、各ファイルの docstring とコード中コメントを参照してください。必要であれば README を拡張して、起動例やデプロイ手順（systemd / docker / cron）を追加します。どの情報を追加したいか教えてください。