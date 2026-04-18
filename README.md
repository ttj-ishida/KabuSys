# KabuSys

日本株自動売買システムの一部（ライブラリ & 実行スクリプト群）。  
このリポジトリには、監視／実行エンジン、ポートフォリオ構築、リサーチ、AI（ニュース NLP）などのモジュールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買のためのモジュール群です。主要な責務は以下の通りです。

- ExecutionEngine（発注エンジン）の起動・制御
- Monitoring（システム監視、取引監視、リスク監視）とアラート管理
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- DuckDB を用いたリサーチ／ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュースを LLM（OpenAI）でスコア化する AI モジュール
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証等）
- ペーパートレード検証用レポート生成ツール

設計方針の特徴:
- 環境変数（.env）経由で設定を管理
- DuckDB / SQLite を利用したデータ永続化
- 本番（live）とペーパートレード（paper_trading）を明確に分離
- LLM 呼び出しはフェイルセーフ（失敗時は安全側で継続）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading 用クライアントを使用）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 設定関連
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前の設定検証 CLI
- 監視 / キルスイッチ
  - monitoring モジュール: system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine
  - kill.flag を書くことで ExecutionEngine の停止シグナルを送る設計
- ポートフォリオ構築
  - portfolio モジュール: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ
  - research モジュール: ファクター計算（momentum / value / volatility）、前向きリターン、IC 計算、統計サマリ
- AI
  - ai.news_nlp: ニュース記事を OpenAI でスコア化し ai_scores テーブルに保存
  - ai.regime_detector: ETF + マクロニュースを使って市場レジームを判定・保存
- ツール
  - tools.paper_verification_report: ペーパートレード DB から期間レポート生成（PASS/FAIL 判定）
- ユーティリティ
  - utils.logging_setup: 統一的なロギング設定（コンソール + 日次ローテートファイル）
  - utils.process_priority: プロセス優先度 / CPU affinity の設定

---

## 必要な依存パッケージ（主なもの）

実際の requirements.txt は本コード断片に含まれませんが、少なくとも以下が必要になります:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の厳密チェック時）
- その他（標準ライブラリ: sqlite3 等）

導入例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# もし requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成し有効化
3. 依存パッケージをインストール（上記参照）
4. 初期 .env を作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV 等を設定します。
5. 設定を検証
   ```bash
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```
6. 必要なデータディレクトリを作る（.env のデフォルトは data/ と logs/）
   ```bash
   mkdir -p data logs
   ```
   DuckDB / SQLite ファイルは初回起動時に自動作成されますが、親ディレクトリは存在させておくと安全です。

注意: 本番運用時は KABUSYS_ENV を `live` に設定します。ペーパートレードは `paper_trading`。開発は `development`。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN (任意)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 時に使用
- PAPER_FILL_MODE (paper_trading 時の挙動, デフォルト: instant). 有効値: instant | partial | never | reject
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — AI モジュール利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1=クリア、開発向け。デフォルト 0）

.env の基本例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（主要コマンド）

- ExecutionEngine を起動
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中に data/stop_requested.flag が存在するとエンジンは停止します。
  - 起動時に kill.flag が残っていると起動を行わないような安全策を持っています（設定に依存）。

- Monitoring を起動（ポーリング）
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - デフォルト 60 秒。MONITOR_POLL_INTERVAL で上書き可。
  - Monitoring は常に Settings.sqlite_path（本番 DB）を使用します。
  - data/stop_requested.flag が存在するとループを抜けます。

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI モジュール（プログラム内で使用）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    - DuckDB 接続を渡し、OPENAI_API_KEY を環境変数に設定して呼び出します。
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime

- ログ
  - デフォルト: logs/<app_name>.log（日次ローテーション、30日保持）
  - setup_logging() を全エントリポイントで呼んでいます（run_* スクリプトは app_name を指定）。

---

## 停止・キルスイッチ

- stop_requested.flag
  - run_monitoring.py / run_execution.py は data/stop_requested.flag の存在を監視し、見つかれば正常終了します。
  - 開発や手動停止用フラグです。

- kill.flag
  - monitoring の KillSwitch が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。
  - ExecutionEngine は起動時/実行中に kill.flag を見て停止または起動を抑止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると ExecutionEngine 起動時に自動クリアします（本番では推奨しません）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（省略箇所あり）:

- src/kabusys/
  - __init__.py
  - run_execution.py
  - run_monitoring.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py      (参照: アラート管理)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/             (上記)
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                   (実行時に使用されるデータディレクトリ: DB/フラグ等)
  - logs/                   (ログ出力先)

（注）実際のファイルは上記断片を含む形で構成されています。ここには抜粋して記載しています。

---

## 開発・運用上の注意点

- 本番環境では KABUSYS_ENV=live を設定し、LINE 通知等の設定を必ず確認してください。
- KILL_FLAG_CLEAR_ON_START を `1` にするのは危険（本番では `0` 推奨）です。自動で kill.flag を消すと、意図しない運用が続行される恐れがあります。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）を必要とします。API 料金やレート制限に注意してください。失敗時はフェイルセーフで動作するよう設計されていますが、運用ポリシーを検討してください。
- DuckDB / SQLite ファイル（data/）はバックアップポリシーを検討してください。特に本番の monitoring.db / orders db の扱いは慎重に。
- psutil によるプロセス優先度設定は権限が必要になる場合があります（AccessDenied の可能性をログで通知）。cron / systemd で起動する際の権限設定に注意。

---

## トラブルシューティング（よくある項目）

- .env を読み込まない / 値が反映されない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にすると自動読み込みを無効化できます（テスト時に利用）。
  - `.env` と `.env.local` の読み込み順に注意（OS 環境変数が優先されます）。
- logs/ にファイルが作れない
  - LOG_DIR を適切に設定するか、ログディレクトリのパーミッションを確認してください。作成失敗時はコンソール出力のみになります。
- OpenAI 関連で JSON 解析エラーが出る
  - モデル応答のバリエーションに備えた復元処理が入っていますが、それでも解析できない場合は LLM 側の応答をログで確認してください。

---

この README はリポジトリ内コードの要点をまとめたものです。詳細な実装や追加の実行オプションは各モジュールの docstring / コメントを参照してください。必要であれば各スクリプトの使い方や config の詳細説明を追記します。