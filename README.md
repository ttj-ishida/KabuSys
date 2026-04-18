# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
この README はソースコードの構成・セットアップ・起動方法を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な機能として、シグナル生成・ポートフォリオ構築・ポジションサイジング・注文実行（本番 / ペーパートレード分離）・監視・リスク管理・AI によるニュース解析やレジーム判定などを備えています。  
データ解析には DuckDB、監視・取引ログには SQLite を利用します。起動スクリプトや対話式設定ウィザード、検証ツールも提供します。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード（mock ブローカー）を切替可能
  - 発注・orders 管理、リスク管理、reconciler 等
- 監視（Monitoring）
  - システムリソース、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）監視
  - Kill Switch（kill.flag によるエンジン停止）
  - 監視用 DB（SQLite）とログ永続化
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスク調整（セクター上限）、単元丸めによる株数算出
- リサーチ機能
  - モメンタム / バリュー / ボラティリティファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI 機能
  - ニュース NLP（OpenAI）による銘柄別センチメントスコア生成（ai_scores テーブル）
  - マクロニュース + ETF MA を用いた市場レジーム判定（bull / neutral / bear）
- ツール
  - .env 対話式生成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート出力ツール（tools/paper_verification_report）
- ユーティリティ
  - ロギング設定（ファイルローテーション含む）
  - プロセス優先度 / CPU affinity 設定
  - .env ファイルの柔軟なパース・ロード

---

## 事前要件

- Python 3.9+（実際には typing の Union | 省略形を使っているため 3.10 以降が望ましい場合あり）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config 検証で YAML をチェックする場合）
- システムにより追加権限（プロセス優先度設定など）

パッケージはプロジェクトの pyproject.toml / requirements.txt に従ってインストールしてください。

---

## 環境変数（主要）

必須：
- JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意/設定項目（デフォルト値は括弧内）：
- KABUSYS_ENV (development | paper_trading | live) （development）
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- LOG_LEVEL (INFO)
- LOG_DIR (logs/)
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0 or 1, デフォルト 0)
- PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject")（instant）
- OPENAI_API_KEY — OpenAI を使う機能時に必要
- MONITOR_POLL_INTERVAL — 監視ループのポーリング秒数（run_monitoring 用、デフォルト 60）

.env の自動読み込み:
- プロジェクトルートにある `.env` / `.env.local` が自動でロードされます（OS 環境変数を上書きしない）。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## セットアップ手順（概要）

1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージをインストール（pip 等）
3. .env を用意
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
4. 設定検証:
   - python -m kabusys.validate_config
   - 本番に近いチェックを行う場合は `--strict` を使用（警告も失敗扱い）
5. 必要なデータディレクトリを作成（data/, logs/ などはスクリプトが自動作成することもあります）

例コマンド:
```
python -m pip install -r requirements.txt
python -m kabusys.config_setup
python -m kabusys.validate_config
```

---

## 使い方（起動 / 実行）

以下は主要なスクリプトの説明と起動例。

1. ExecutionEngine を起動（本番 / ペーパートレード）
   - 動作:
     - KABUSYS_ENV によりペーパートレード時は MockBroker を使用し、データは `data/paper_trading.db` に隔離されます。
     - 起動時に PID ファイル（data/execution.pid）を管理。
     - data/stop_requested.flag の存在で停止。
   - 起動:
     ```
     python -m kabusys.run_execution
     ```
   - 注意:
     - 事前に .env で必要な環境変数を設定してください。
     - KILL スイッチは `data/kill.flag` によって ExecutionEngine の停止を指示できます。

2. Monitoring（継続監視）を起動
   - 動作:
     - SystemMonitor を定期ポーリングし、system_status などを SQLite に記録
     - 環境にかかわらず monitoring は本番用の sqlite_path を使用（monitoring のログは本番 DB に残る）
     - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60）
     - 停止フラグ: data/stop_requested.flag
   - 起動:
     ```
     python -m kabusys.run_monitoring
     ```
   - カスタム間隔例:
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```

3. .env 対話式セットアップ
   ```
   python -m kabusys.config_setup
   ```

4. 設定検証
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```

5. Paper Trading 検証レポート（ツール）
   - 役割: ペーパートレード DB（デフォルト data/paper_trading.db）を読み取り、稼働率・注文成功率・レイテンシなどのレポートを出力します。
   - 例:
     ```
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     ```
   - DB を明示する場合:
     ```
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
     ```

6. AI 機能
   - 必要: OPENAI_API_KEY 環境変数または各関数の api_key 引数
   - 主な関数:
     - kabusys.ai.score_news — ニュースを LLM に投げて ai_scores を更新
     - kabusys.ai.regime_detector.score_regime — 市場レジーム判定して market_regime テーブルへ書き込み
   - 注意: API エラーはフェイルセーフで一部代替処理（0.0 等）にフォールバックする設計です。API の利用量・コストに注意してください。

---

## 監視 / 停止フロー（Kill Switch / Stop フラグ）

- Kill Switch:
  - リスク条件（ドローダウンやポジション上限）に該当すると `data/kill.flag` を作成し、ExecutionEngine に停止指示を出します。
  - KillSwitch は冪等に書き込みを行い、既存ファイルがあれば再書き込みしません。
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定していると起動時に自動で kill.flag を削除します（本番ではデフォルト 0 を推奨）。
- 手動停止:
  - data/stop_requested.flag を作成すると、run_execution / run_monitoring が次のループで検知して停止します。

---

## ログ / DB の既定パス

- DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
- 監視 SQLite: data/monitoring.db（環境変数 SQLITE_PATH で変更可）
- ペーパートレード SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- ログ: logs/<app_name>.log（LOG_DIR で変更可、日次ローテーション・30日保持）
- PID ファイル: data/execution.pid（PID_FILE_PATH で変更可）
- Kill flag: data/kill.flag（KILL_FLAG_PATH で変更可）
- Stop flag: data/stop_requested.flag（プロジェクト内の data ディレクトリに配置される）

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/.env の読み込みと Settings
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し）
    - regime_detector.py — レジーム判定
  - monitoring/
    - monitoring_db.py — 監視用 DB 層
    - system_monitor.py — システム監視
    - trade_monitor.py — （存在、取引監視ロジック）
    - risk_monitor.py — リスク監視（ドローダウン等）
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - alert_manager.py —（存在、通知管理）
  - execution/  — 発注系コンポーネント（BrokerClientFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ （実行時に作成される想定）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用）
    - kill.flag / stop_requested.flag / execution.pid など

（上記はソース内にある主要モジュールの抜粋です。実際のディレクトリにはさらに細かいモジュールや補助ファイルが含まれます。）

---

## 開発・運用上の注意

- 本番運用時は KABUSYS_ENV=live を設定し、KILL_FLAG_CLEAR_ON_START は 0 を推奨します。validate_config の警告に注意してください。
- .env は機密情報を含むため Git にコミットしないでください（config_setup でも注意喚起あり）。
- AI 機能を利用する場合は OpenAI の利用料金に注意し、API キーの管理を徹底してください。
- 監視は監視用 SQLite（monitoring.db）へ記録されます。monitoring は環境に関わらず本番用 sqlite_path を使用します。
- ペーパートレードは本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## よく使うコマンドまとめ

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```
- ExecutionEngine 起動
  ```
  python -m kabusys.run_execution
  ```
- Monitoring 起動
  ```
  python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコードベースの主要点をまとめたものです。細部の実装や追加オプションについては各モジュールの docstring / ソースコメントを参照してください。必要であれば運用手順書（運用 runbook）やデプロイ手順のテンプレートも作成できますのでご依頼ください。