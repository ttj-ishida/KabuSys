# KabuSys

日本株向け自動売買システムのリポジトリ（部分実装）。  
この README はコードベース（src/kabusys）を元に作成した概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連するリサーチ／監視機能を備えたシステムです。  
主なコンポーネントは次のとおりです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況・注文ログ・リスク監視を行い、Kill Switch による安全停止を提供
- Portfolio：銘柄選定・配分・ポジションサイズ計算などポートフォリオ構築ロジック
- Research：DuckDB を使ったファクター計算・将来リターン計算・特徴量解析
- AI モジュール：ニュース NLP（OpenAI）によるセンチメントスコア化、レジーム判定
- CLI ツール：環境設定ウィザード、設定検証、Paper Trading 検証レポート生成 など

設計方針の主要点：
- 本番用データベース（SQLite / DuckDB）は明示的に分離（ペーパートレード用 DB を別に持てる）
- ルックアヘッドバイアスを避けるため日時参照方法に注意
- フェイルセーフ設計（API 失敗時はスキップまたはデフォルト値で継続）

---

## 機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）で .env ファイル生成
- 設定検証ツール（python -m kabusys.validate_config）
- 実行エンジンの起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を使用し paper_trading DB に記録
- 監視ループの起動スクリプト（python -m kabusys.run_monitoring）
  - システム状態・注文状態・リスク監視を周期的に実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Kill Switch（監視でトリガーした場合に data/kill.flag を書き込んで ExecutionEngine を停止）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- ファクター計算・特徴量探索（research/*.py）
- ニュース NLP（OpenAI）を使った銘柄ごとのセンチメント自動スコア化
- ロギングユーティリティ（stdout + 日次ローテーションファイル）

---

## 必要条件（想定）

以下はコード内から読み取れる主要依存パッケージ（正確な requirements.txt はプロジェクトに合わせて作成してください）：

- Python 3.9+
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config 検証時に任意で使用）

インストール例（仮）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数 / .env の概要

自動読み込み:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数が優先）。
- 無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須（validate_config や Settings により参照）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション（抜粋）:
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力先ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

最小例（.env の一部）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

.env の生成はウィザードで支援可能（後述）。

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成
   ```
   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ 実際の requirements.txt があれば `pip install -r requirements.txt` を使用してください。

3. 環境変数（.env）を作成
   - 対話型ウィザードを起動:
     ```
     python -m kabusys.config_setup
     ```
     - or: 手動で `.env` を作成（上記の最小例を参考に）

4. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ作成
   - 必要ディレクトリ（例: data, logs）は自動作成される場合がありますが、手動で用意しておくと確実です:
     ```
     mkdir -p data logs
     ```

---

## 使い方

基本的な起動方法（開発 / テスト用）:

- 監視ループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数でポーリング間隔上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録して本番 DB と分離します。

停止制御:
- どちらの起動スクリプトもプロジェクトの data ディレクトリにある `stop_requested.flag` を監視しています。ファイルを作成すると安全にループ／スレッドを終了します（運用での停止フラグ）。
- 監視側の Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（実運用では注意して使用してください）。

ツール:
- Paper Trading 検証レポート（SQLite の paper_trading DB を指定可）
  ```
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  ```

AI 機能（コード実行例）:
- ニュース NLP / レジーム判定は関数呼び出し API（duckdb 接続と target_date を渡す）で利用します。実行には OpenAI API キー（環境変数 OPENAI_API_KEY）が必要です。
  - 例（擬似コード）:
    ```
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 11), api_key="sk-...")
    ```

ログ:
- ログは標準出力と `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリは環境変数 `LOG_DIR` または `logs/` が使われます。

---

## 運用メモ / 注意点

- 本番（KABUSYS_ENV=live）では設定値を慎重に確認してください。validate_config は live 設定時に追加警告を出します。
- Paper Trading は実発注を行わないが、検証に有用なログを別 DB に記録します（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を利用する処理は外部 API 呼び出しに依存するため、レート制限・接続断に備えたリトライやフェイルセーフ実装がありますが、API キー管理は厳重に行ってください。
- プロセス優先度設定（psutil を使用）を行いますが、OS 権限により失敗する場合があります（警告ログのみ）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の src/kabusys を中心に主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings クラス（.env 自動読み込み）
  - config_setup.py          — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py       — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/               — 実行エンジン関連（order_manager, broker_factory 等）※詳細ファイルは repo に依存
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 初期化・読み書きラッパー
    - system_monitor.py      — システム状態／データ鮮度監視
    - trade_monitor.py       — 注文関連監視（参照あり）
    - risk_monitor.py        — ドローダウン・ポジション制限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるポーリング実行器
    - alert_manager.py       — アラート送信（LINE 等）※参照あり
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

（上記は主要ファイルの抜粋です。実際のファイル数・詳細はリポジトリの内容を参照してください。）

---

## 開発向けヒント

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト実行時に自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB を使ったリサーチ機能はデータテーブル（prices_daily / raw_financials / raw_news 等）に依存します。データ投入のためのスクリプトやパイプラインが別に存在する想定です。
- ロギングは統一された設定関数 setup_logging を呼ぶことで stdout とファイル出力が設定されます。ユニットテストでは出力先やレベルを調整してください。

---

この README はコードの解読に基づくもので、実際の運用手順や依存関係はプロジェクトの root にあるドキュメント（requirements.txt / deployment README 等）を優先してください。必要なら実際の requirements.txt やデプロイ手順をもとにドキュメントを拡張します。