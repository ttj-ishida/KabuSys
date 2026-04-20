# KabuSys — 日本株自動売買コンポーネント集

このリポジトリは日本株の自動売買システム（KabuSys）のコンポーネント群を含みます。取引エンジン、監視モジュール、ポートフォリオ構築、リサーチ用ファクター計算、AI によるニュースセンチメント評価、ユーティリティなどがまとめられています。

> 注: この README はソースコード（src/kabusys 以下）に基づいて作成しています。実行環境や外部依存のバージョンにより動作が異なる場合があります。

---

## 概要（Project Overview）

KabuSys は以下の機能群を提供します：

- Execution Engine：ブローカークライアントを通して発注・注文管理を行う実行系（本番 / ペーパートレード切替対応）。
- Monitoring：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を監視し、Kill Switch（停止フラグ書き込み）やアラートを行う。
- Portfolio Construction：候補選定、重み計算、ポジションサイズ算定、セクター集中制御などの純粋関数群。
- Research：DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析（IC 等）。
- AI モジュール：OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価・市場レジーム判定。
- ツール：ペーパートレード検証レポート生成などの CLI ユーティリティ。
- 設定管理：.env 作成ウィザード（config_setup）・設定検証（validate_config）等。
- 共通ユーティリティ：ログ設定、プロセス優先度設定、DB 初期化など。

設計方針として、リサーチ／AI モジュールは本番発注系（kabuAPI 等）に直接アクセスしないようになっており、DuckDB や SQLite をデータソース／永続化に使用します。

---

## 主な機能一覧（Features）

- 環境別動作：
  - KABUSYS_ENV による `development` / `paper_trading` / `live` 切替
  - `paper_trading` 時は専用の paper DB を使用し、本番 DB と分離
- 監視（Monitoring）：
  - CPU/メモリ/ディスク使用率、Execution プロセス存否、データ鮮度チェック
  - リスク監視（ドローダウン、ポジション上限）と永続化（SQLite）
  - Kill Switch（data/kill.flag）による安全停止
- 実行系（ExecutionEngine）：
  - ブローカークライアント抽象化（テスト用 Mock を含む想定）
  - リスクマネージャ、注文管理、照合処理を統合
- ポートフォリオ構築：
  - シグナルの候補選択、スコア/等分配重み、ポジションサイズ算出（単元株丸め等）
  - セクターキャップ、レジーム乗数等のリスク調整
- リサーチ：
  - モメンタム / ボラティリティ / バリューファクター計算（DuckDB）
  - 将来リターン、IC（スピアマンランク相関）や統計サマリ
- AI（OpenAI）:
  - ニュース集合を集約して LLM による銘柄別センチメント評価（ai_scores へ保存）
  - マクロセンチメントと ETF MA を合成した市場レジーム判定（market_regime へ保存）
  - API 呼び出しはリトライ、エラー耐性、JSON バリデーションを実装
- ツール:
  - ペーパートレード検証レポート生成スクリプト（成功率・稼働率・レイテンシ等を集計）
- 設定支援:
  - .env 作成ウィザード（対話式）
  - 設定検証 CLI（必須環境変数 / config/*.yaml / DB パス等のチェック）
- 共通ユーティリティ:
  - ログ初期化（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity セット

---

## 前提・依存（Prerequisites）

最低限の依存（実行に必要な代表例）：

- Python 3.9+
- ランタイムライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 内容検証時に利用。必須ではない）
- SQLite は標準で利用

実際のプロジェクトでは requirements.txt / pyproject.toml を参照して依存をインストールしてください。

例（開発環境想定）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順（Setup）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化する。
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai pyyaml
   ```

2. .env を作成する（対話式ウィザード推奨）。
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは J-Quants トークンや kabuAPI パスワードなどの入力を促します。生成された `.env` ファイルは絶対に Git にコミットしないでください。

3. 設定確認（自動検証）。
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告があると非成功（exit code 1）になります。

4. データディレクトリ（デフォルト：data/）やログディレクトリ（デフォルト：logs/）が必要な場合は作成されますが、パーミッション等を事前に確認してください。

5. OpenAI を利用する機能を使う場合は環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に明示的に API キーを渡してください。

---

## 主要環境変数（抜粋）

（コード中で参照されている重要な環境変数とデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時に使用）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

---

## 使い方（Usage）

### 監視プロセスの起動（Monitoring）
監視ループを起動します。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能。監視はデフォルトで production（本番）用の sqlite_path を使用します。

```
python -m kabusys.run_monitoring
# 例: 10秒間隔に設定
MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
```

監視プロセスはプロセス優先度を高く設定し、`data/stop_requested.flag` が存在するとループを終了します。

### 実行エンジンの起動（Execution）
ExecutionEngine を起動します。KABUSYS_ENV によって本番または paper_trading 動作を切り替えます。paper_trading の場合は MockBrokerClient を使用し、データは `data/paper_trading.db`（PAPER_TRADING_SQLITE_PATH）に保存されます。

```
python -m kabusys.run_execution
```

起動時に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。実行中に `data/stop_requested.flag` を作成するとエンジンは安全に停止します。

### .env の作成（ウィザード）
対話式で .env を作成／更新します。

```
python -m kabusys.config_setup
```

作成後、設定検証を実行してください：
```
python -m kabusys.validate_config
```

### ペーパートレード検証レポート生成
ペーパートレード DB（デフォルト: data/paper_trading.db）から期間を指定して検証レポートを生成します：

```
# 全期間（存在するデータ範囲）:
python -m kabusys.tools.paper_verification_report

# 期間指定:
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB 指定:
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

出力内容: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）など。閾値に基づき PASS/FAIL を判定します。

### AI モジュール（関数呼び出し）
AI 関連は主にプログラムから呼び出す設計です（モジュール経由）。

- ニューススコア（ai_scores 保存）:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 例: Python スクリプト内で DuckDB 接続を作成し呼び出す

- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意: OpenAI API キーは環境変数 `OPENAI_API_KEY` を設定するか、引数で渡してください。API 呼び出しはリトライやバリデーションの仕組みを持ちますが、キー未設定時は ValueError が発生します。

---

## 動作停止（Kill / Stop）

- 実行スクリプトは `data/stop_requested.flag` の存在を監視しており、ファイルが存在すると監視ループやエンジンを停止します。
- Kill Switch は危険事象（ドローダウン超過、ポジション上限超過等）を検出すると `data/kill.flag` を書き込み、ExecutionEngine 側で検出して停止させる仕組みです。`KILL_FLAG_CLEAR_ON_START` を `1` にすると起動時に自動クリアします（本番では危険なので `0` を推奨）。

---

## ログ設定

- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます（kabusys.utils.logging_setup.setup_logging を使用）。
- ログレベルは `LOG_LEVEL` 環境変数または setup_logging の引数で設定できます。
- ログディレクトリは `LOG_DIR` 環境変数で上書き可能（デフォルト: logs/）。ディレクトリ作成に失敗した場合はファイル出力は無効化され、コンソールのみになります。

---

## ディレクトリ構成（Directory structure）

以下は主要なファイル・モジュールの一覧（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — Monitoring 起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成ツール
  - utils/
    - __init__.py
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（monitoring テーブル群）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — （注文関連監視）※実装はコードベースに依存（省略あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 制御
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート管理（存在する場合）
  - execution/
    - broker_factory.py — ブローカークライアント生成（Mock を含む想定）
    - execution_engine.py — 実行エンジン本体
    - order_manager.py — オーダー管理
    - order_repository.py — 注文永続化
    - reconciler.py — 注文照合
    - risk_manager.py — リスク管理（RiskConfig 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数決定・投下資金制御
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI 経由）
    - regime_detector.py — マクロ + MA によるレジーム判定
    - __init__.py

（注）上記はリポジトリに含まれる主要ファイルで、コード内に参照される他の補助モジュールや未掲示の実装が存在する場合があります。

---

## アーキテクチャ上の注意点 / 運用上のヒント

- .env と API キー: センシティブな情報（API キー、パスワード等）は `.env` に保存し、絶対にバージョン管理に含めないでください。
- 本番（live）環境では `KABUSYS_ENV=live` を設定する前に validate_config を必ず実行し、LINE 通知等が設定されていることを確認してください。
- Kill Switch 機構は重大なリスク時に自動停止を行いますが、運用フロー（誰がフラグをクリアするか等）を明確にしてください。
- OpenAI 利用時は API コストとレート制限に注意。ニューススコアリング・レジーム判定は外部コールを伴うため、エラー時のフォールバック動作を理解しておいてください。
- DuckDB / SQLite のパスは環境変数で変更可能。paper_trading の DB は明示的に分離されています。

---

## ライセンス・貢献

本ドキュメントにはライセンス情報は含みません。実際のリポジトリの LICENSE を参照してください。バグ報告や機能改善はリポジトリの Issue / PR を通じて行ってください。

---

この README はソースを読み解いて作成しています。さらに詳細な使用例や運用手順（systemd サービス化、監視ダッシュボード、バックアップ方針等）が必要であれば、その点を指定していただければ追補します。