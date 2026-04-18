# KabuSys

日本株自動売買システムの一部を切り出した Python パッケージ（ライブラリ＋起動スクリプト群）。

このリポジトリには、実行エンジン起動スクリプト、監視（Monitoring）周りのコンポーネント、ポートフォリオ構築／リスク制御の純粋関数群、研究用ファクター計算、AI（LLM）連携モジュールなどが含まれます。

---

## 主な機能

- 実行エンジン起動（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアントのファクトリ、Order 管理、リスク管理、リコンサイルを組み立てて ExecutionEngine を起動
- 監視プロセス（run_monitoring.py）
  - System / Trade / Risk のモニタをポーリングしてログ保存、Kill Switch 評価やアラート発行
  - ポーリング間隔は環境変数で制御可能
- 設定管理
  - .env 対話ウィザード（config_setup.py）
  - 起動前チェック CLI（validate_config.py）
- Research / Data
  - DuckDB を用いたファクター計算（momentum / volatility / value など）
  - 将来リターン計算・IC（Information Coefficient）などの解析ユーティリティ
- Portfolio Construction
  - 候補選定、重み計算、単元丸め・ポジションサイズ計算、セクター上限・レジーム調整
- AI（LLM）連携
  - ニュースのセンチメント評価（OpenAI を利用）→ ai_scores へ書き込み
  - 市場レジーム判定（ETF MA + マクロニュースを LLM で評価）
- 運用支援ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - ロギング設定、プロセス優先度 / CPU affinity 設定、監視 DB 永続化層（SQLite）

---

## 必要条件（概略）

- Python 3.10+
  - 型ヒントに `X | None` などを使っているため Python 3.10 以上を推奨
- 必要なパッケージ（例）
  - duckdb
  - psutil
  - openai
  - （推奨）PyYAML（config 検証時に YAML パースを行う場合）
- SQLite（組み込み）／DuckDB（Python パッケージでファイルにアクセス）
- ネットワーク接続（kabuステーション API、OpenAI 等を使う場合）

pip インストール例（requirements.txt が無い場合の例）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / コピーして任意の作業ディレクトリに配置。
2. Python 仮想環境を作成して有効化（推奨）。
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール。
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. .env（環境変数）を用意する。
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って値を入力するとプロジェクトルートに `.env` が生成されます。
   - 手動で作成する場合は、最低限以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   例（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABUSYS_ENV=development
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```
5. 設定検証（任意だが推奨）:
   ```
   python -m kabusys.validate_config
   ```
   --strict オプションを付けると警告も失敗扱いになります:
   ```
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリ（`data/`）やログディレクトリ（`logs/`）が自動生成されますが、パーミッション等に注意してください。

---

## 使い方（主要スクリプト）

- 実行エンジンを起動する
  - 本番 / ペーパートレードは KABUSYS_ENV で切り替え
  - 例: ペーパートレードで起動（本番 DB と分離して data/paper_trading.db を使用）
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 通常起動（デフォルトは development）
    ```
    python -m kabusys.run_execution
    ```

- 監視プロセスを起動する
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 起動前チェック（設定検証）
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または環境変数で DB を指定:
  ```
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db python -m kabusys.tools.paper_verification_report
  ```

- ライブラリとして利用する例
  - ポートフォリオ関数呼び出し:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
    ```
  - 研究用関数:
    ```
    from kabusys.research import calc_momentum, calc_volatility
    ```
  - AI スコアリング:
    ```
    from kabusys.ai.news_nlp import score_news
    ```

---

## よく使う環境変数一覧（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード専用）
- ペーパートレード設定
  - PAPER_FILL_MODE: instant | partial | never | reject
- 監視関連
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）
  - MONITOR_POLL_INTERVAL（監視ポーリング間隔、run_monitoring 用）
- OpenAI
  - OPENAI_API_KEY（ai モジュールを使う場合）

詳細は `src/kabusys/config.py` を参照してください（Settings クラスで各キーの既定値やバリデーションが定義されています）。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定の解決
  - config_setup.py            — .env 対話型ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum/value/volatility 等）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py         — SQLite 用永続化層（schema + helper）
    - system_monitor.py
    - trade_monitor.py         — （含まれるはずのモジュール。リポジトリ全体で利用）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — アラート管理（実装に応じて通知）
  - execution/
    - execution_engine.py      — ExecutionEngine（起動部は run_execution が呼ぶ）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - data/                      — 実行時に生成されるファイル（data/monitoring.db 等）
  - utils/
    - logging_setup.py         — 統一的な logging 設定
    - process_priority.py      — プロセス優先度 / CPU affinity 設定

（注）上記はリポジトリ内の主なファイルを抜粋したものです。実行エンジン／ブローカー実装部分は外部依存やスタブが含まれる想定です。

---

## 運用上の注意／補足

- 本番運用時は KABUSYS_ENV=live を設定し、.env の中身（API キー等）を厳重に管理してください。validate_config は live 時に追加警告を出します。
- kill.flag（デフォルト data/kill.flag）を書くことで実行エンジンを停止させる「Kill Switch」機構があります。運用時は誤操作に注意してください。
- run_monitoring は Monitoring 用に本番の sqlite_path を参照します（設定に依らず本番 DB に書き込む設計になっている点に注意）。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーとコスト管理が必要です。API 呼び出しはリトライ・フェイルセーフが組み込まれていますが、課金やレート制限に注意してください。
- DuckDB / SQLite ファイルはローカルに保存されます。バックアップや容量管理が必要です。
- ログは logs/<app_name>.log に日次ローテーションで出力されます（`kabusys.utils.logging_setup`）。

---

README は以上です。より詳しい API 仕様や ExecutionEngine の内部設計、ブローカークライアント実装、監視・アラートポリシーについては該当モジュールのドキュメント（モジュール内 docstring）や別途提供されている設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。必要があれば README の拡張（運用手順や Systemd / Supervisor 用のサービス定義例など）も作成します。どの情報を追加しますか？