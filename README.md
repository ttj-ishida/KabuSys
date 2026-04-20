# KabuSys

日本株向け自動売買・リサーチ基盤の軽量実装（ライブラリ + 起動スクリプト群）。

この README はリポジトリ内のコードを元に作成しています。開発用 / ペーパートレード / 本番（live）を切り替えて動かせるよう設計されています。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されたシステムです：

- 発注・実行エンジン（ExecutionEngine） — ブローカークライアント経由で注文を発行・管理
- 監視サブシステム（Monitoring） — システム状態・注文・リスクの常時監視とアラート／Kill Switch
- ポートフォリオ構築ロジック（Portfolio） — 候補選定・重み計算・株数決定
- リサーチ（Research） — ファクター計算・将来リターン計算・IC評価など
- AI モジュール（AI） — ニュースNLP（OpenAI）を用いたセンチメント評価やレジーム判定
- 運用ユーティリティ（config_wizard / validate / ロギング設定 等）
- 分析用データ格納に DuckDB、監視・発注履歴に SQLite を使用

主な設計方針：
- 本番 DB とペーパートレード DB を分離
- ルックアヘッドバイアスを避ける設計（日時参照の注意）
- フェイルセーフ：API失敗時は安全なデフォルトで進める
- テストしやすい純粋関数・副作用の明示

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ペーパートレード時は MockBrokerClient を使い別 DB に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- 監視（run_monitoring.py / monitoring モジュール群）
  - CPU / メモリ / ディスク / プロセスの死活監視
  - 注文の滞留チェック、約定異常検出
  - ドローダウン・ポジション上限の監視と Kill Switch（data/kill.flag）発行
  - ログ永続化（SQLite）と DuckDB 参照

- ポートフォリオ（kabusys.portfolio）
  - 候補選定（スコアソート）
  - 等配分・スコア加重配分
  - ポジションサイズ決定（単元丸め、リスクベース、最大ポジション・投資額制限）
  - セクター上限適用、レジーム乗数

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算（DuckDB SQLベース）
  - 将来リターン、IC（スピアマンランク）計算、統計サマリ

- AI（kabusys.ai）
  - ニュースをまとめて OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に格納
  - マクロニュース + ETF MA200 乖離を合成して市場レジーム（bull/neutral/bear）判定

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.10+ を推奨（ソースに型ヒントや新しい構文を使用）。

1. リポジトリをクローンしてワークディレクトリへ移動

2. 仮想環境を作成・有効化（例）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要なパッケージをインストール（requirements ファイルがない場合は以下を個別インストール）
   ```
   pip install duckdb psutil openai
   ```
   - 任意 / 検証用:
     - PyYAML（config 検証で YAML をパースする場合）: `pip install pyyaml`
   - sqlite3 は標準ライブラリに含まれます。

4. .env を作成（2つの方法）
   - 対話式ウィザード（推奨）：
     ```
     python -m kabusys.config_setup
     ```
     ウィザードが .env を生成します。
   - 手動で作成：プロジェクトルートに `.env` を置く（.env.example を参考に）

5. 設定を検証：
   ```
   python -m kabusys.validate_config
   # 警告を FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データ / ログ用ディレクトリの作成（通常は自動作成されますが権限等に注意）:
   - data/
   - logs/

---

## 主要な環境変数（主なもの）

- 必須（少なくともローカルで確認する）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector で使用

- ログ / 実行制御
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存先
  - PID_FILE_PATH: 実行エンジンの PID ファイルパス（default: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag パス（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1, default 0）

- 監視間隔
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- Paper Trading の動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- 自動 .env ロードの無効化（テスト等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 監視ループ起動（本番的な監視プロセス）:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更できます（例: 30 秒）。
  - 監視は常に本番 sqlite_path を使用します（環境にかかわらず）。

- 実行エンジン起動（発注エンジン）:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い `data/paper_trading.db` に記録します（本番 DB と完全に分離）。
  - 起動前に `data/stop_requested.flag` が存在すると起動しません。
  - 実行中、停止指示は `data/stop_requested.flag` を作ることで伝えられます。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは `data/paper_trading.db`。`--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI / レジーム判定（ライブラリ呼び出し例）
  - ニューススコアリング（プログラムから呼ぶ場合）:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

---

## 停止・Kill 制御

- run scripts（run_monitoring / run_execution）はプロジェクトルートの `data/stop_requested.flag` が作成されるとループを抜けます（グレースフル停止）。
- 監視コンポーネントは重大なリスク（ドローダウンやポジション超過）を検出した場合、`KILL_FLAG_PATH`（デフォルト: `data/kill.flag`） に理由を書き込み ExecutionEngine に停止指示を送ります。
- `KILL_FLAG_CLEAR_ON_START=1` が設定されていると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## ログ・ファイル

- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（起動時に app_name を指定してセットアップ）
- ローテーション: 日次、過去 30 日分保持
- 実行エンジンの PID: data/execution.pid（run_execution が使用）

---

## トラブルシューティング（よくある注意点）

- psutil によるプロセス優先度設定は OS や権限によって失敗することがあります（警告が出ますが処理は継続します）。
- ログディレクトリ / data ディレクトリの権限不足でファイル出力に失敗する場合があります。ディレクトリを作成して書き込み権限を確認してください。
- OpenAI 呼び出しは APIKey と料金に注意。失敗時はフェールセーフで進む実装になっていますが、期待するスコアが得られない場合があります。
- DuckDB / SQLite の接続先（パス）は環境変数で上書き可能です。運用では永続ディスク上の path を指定してください。
- config/*.yaml の内容検証は PyYAML が必要です（未インストールだと検証はスキップされ、警告が出る）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の抜粋（主要モジュール）です：

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロードロジック含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定

  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 注文/約定の監視（ファイル内にあり）
    - risk_monitor.py         — ドローダウン・ポジション監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - monitoring_engine.py    — 各モニタの束ね（ポーリングループ）

  - execution/                — 発注エンジン関連（broker factory 等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・制限・丸め
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity

---

## 開発メモ / 補足

- DuckDB 接続は分析専用で、SQL を使ったファクター集計を想定しています。
- 多くの関数はテストしやすい純粋関数として設計され、外部副作用（DB 書き込み等）が分離されています。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

必要であれば、README に以下を追加で含めます：
- 詳細な環境変数の一覧（全項目）
- docker / systemd ユニット例（監視・実行プロセスの永続化）
- 代表的な API の使い方（関数レベルの呼び出し例）
ご希望があれば教えてください。