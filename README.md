# KabuSys — 日本株自動売買システム（README）

以下はこのリポジトリに含まれるコードベースの概要、セットアップ手順、使い方、ディレクトリ構成の説明です。開発者向けに主要な挙動や環境変数の意味、実行コマンド例をまとめています。

注意: .env（環境変数）には秘密情報（API トークン等）が含まれるため、絶対に Git へコミットしないでください。

## プロジェクト概要
KabuSys は日本株の自動売買システムです。  
機能群は主に以下で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・整合処理を行う。
- 監視 (Monitoring): システム状態・注文滞留・リスク（ドローダウン等）を定期チェックしてログ・アラート・Kill Switch を管理。
- ポートフォリオ構築（選定・配分・株数決定・リスク調整）: 純粋関数群により銘柄選定とサイズ計算を行う。
- リサーチ機能: ファクター計算・特徴量探索・将来リターン / IC 計算。
- AI 補助: ニュースに対する LLM（OpenAI）でのセンチメント評価、マクロセンチメントを用いた市場レジーム判定。
- ツール: ペーパートレードの検証レポート生成など。

設計上の特徴:
- production / paper_trading を分離（paper_trading は専用 SQLite DB に記録）
- DuckDB を分析用途に使用
- .env を利用した環境変数管理。対話式ウィザードと検証ツール付き
- OpenAI API を用いた NLP 処理はフェイルセーフ（失敗時はスキップ/フォールバック）

## 機能一覧
主な機能（抜粋）:

- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV に応じて実挙動/モック切替）
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔制御）
- monitoring: system / trade / risk の監視、監視ログ（SQLite）保持、Kill Switch 判定、アラート連携
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクターキャップ・レジーム乗数
- research: ファクター（Momentum / Volatility / Value 等）計算、forward returns、IC 計算
- ai: news_nlp（ニュースセンチメント -> ai_scores）、regime_detector（マクロ＋MA200 を合成して regime 決定）
- tools: paper_verification_report（ペーパートレードの検証レポート出力）
- config_setup.py: .env を対話的に作成・更新するウィザード
- validate_config.py: .env および config/*.yaml の事前検証 CLI

## 要求環境（例）
- Python 3.10+（型ヒントに依存）
- 必須/推奨パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai (LLM 機能が必要な場合)
  - PyYAML (config.yaml の検証を行いたい場合)
- SQLite（標準ライブラリで可）

依存パッケージはプロジェクトに requirements.txt が無い場合もあるため、上記を個別にインストールしてください。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動。

2. 仮想環境作成（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール:
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数ファイル（.env）を作成:
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成または既存値を更新します。途中キャンセルも可能です。

5. 設定検証（推奨）:
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. DB の準備:
   - DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLite 監視 DB（デフォルト: data/monitoring.db）
   - paper_trading を使う場合、paper 用 SQLite（デフォルト: data/paper_trading.db）
   多くの起動シーケンスでテーブルは自動作成されます（init_monitoring_db 等）。

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時使用）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI を利用する場合の API キー
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定（任意）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

重要:
- run_execution.py は KABUSYS_ENV=paper_trading のとき、MockBrokerClient が利用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録されます。
- run_monitoring.py は KABUSYS_ENV に関係なく監視用 sqlite_path（本番 sqlite_path）を使用します。

## 使い方（実行コマンド例）

- ExecutionEngine を起動（デーモン化等は別途運用すること）:
  ```bash
  python -m kabusys.run_execution
  ```
  - 実行中に data/stop_requested.flag が作成されると安全に停止します。
  - Execution の PID は data/execution.pid に書き込まれます（監視がプロセス存在を確認します）。

- Monitoring を起動:
  ```bash
  # ポーリング間隔を環境変数で上書き（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - 停止にはプロジェクトルート/data/stop_requested.flag を作成するか Ctrl+C。
  - Monitoring は Settings.sqlite_path（通常 data/monitoring.db）を使用します。

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- AI 関連:
  - ニューススコアリング（プログラムから呼ぶ API）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

（上記はライブラリ関数として呼び出す用途の説明。実行スクリプトは用途に合わせて作成してください。）

## 停止 / Kill Switch / フラグファイル
- data/stop_requested.flag:
  - run_execution.run_monitoring のループを終了させるために使用されます（手動で作成）。
- data/kill.flag:
  - KillSwitch が条件を満たしたときに書き込まれるファイル。ExecutionEngine は存在を検出して停止します。
- data/execution.pid:
  - ExecutionEngine 実行時に PID を書き出します。SystemMonitor は PID を見てプロセス生存を検査します。

## 開発時の注意事項
- .env は自動ロードされます（プロジェクトルートに .env/.env.local がある場合）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- OpenAI/外部 API 呼び出しは失敗時にフォールバックする設計ですが、APIキーの未設定は関数呼び出し時に明示的な例外を発生させることがあります（必要に応じてキーを渡してください）。
- DuckDB の一部操作（executemany で空リスト）がバージョンによって挙動が異なるため、コード内で空チェックを行っています。DuckDB のバージョンアップ時は注意してください。

## ディレクトリ構成
以下は主要ファイル・ディレクトリのツリー（src/kabusys 以下）です（抜粋）:

```
src/kabusys/
├─ __init__.py
├─ config.py                 # Settings / .env 自動ロード・ヘルパ
├─ config_setup.py           # .env 対話式ウィザード
├─ validate_config.py        # 設定検証 CLI
├─ run_execution.py          # ExecutionEngine 起動スクリプト
├─ run_monitoring.py         # SystemMonitor 起動スクリプト
├─ tools/
│  └─ paper_verification_report.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py            # ニュース NLP -> ai_scores
│  └─ regime_detector.py     # マクロ + MA200 による regime 判定
├─ portfolio/
│  ├─ __init__.py
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ monitoring_engine.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py
│  ├─ risk_monitor.py
│  ├─ kill_switch.py
│  └─ alert_manager.py      # （未完/実装に依存する箇所あり）
├─ execution/                # 発注・注文管理等（実装ファイル群）
│  ├─ execution_engine.py
│  ├─ order_manager.py
│  ├─ order_repository.py
│  └─ ... (その他)
├─ data/                     # 実行時の DB / フラグファイル置き場（デフォルト）
└─ utils/
   ├─ __init__.py
   └─ process_priority.py    # プロセス優先度 / CPU affinity ユーティリティ
```

※ 上記はサブモジュールごとにファイルを抜粋しています。実装ファイルはさらに多く含まれます。

## トラブルシューティング（よくある質問）
- 「.env に何を入れればよいかわからない」  
  → `.env.example` があれば参照してください。無ければ `python -m kabusys.config_setup` を使うと対話式で生成できます。

- 「PyYAML が無い」  
  → validate_config は YAML の検証をスキップします。config/*.yaml の構文検証を行いたい場合は `pip install pyyaml` を行ってください。

- 「OpenAI 呼び出しで失敗するとプロセスが止まる？」  
  → LLM 関連処理はフェイルセーフに設計されており、API 失敗時はスキップ/フォールバックします（ログに警告が出ます）。

## 参考コマンドまとめ
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

---

この README はコードベースの主要機能と起動手順をまとめたものです。さらに詳しい設計書（PortfolioConstruction.md / StrategyModel.md 等）がリポジトリ内に存在する場合はそちらも参照してください。追加で記載してほしい項目（例: 各設定のデフォルト値表、運用手順、ユニットテスト方法など）があれば教えてください。