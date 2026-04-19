# KabuSys

日本株自動売買システムの一部を構成する Python パッケージ。  
このリポジトリには、実行エンジン起動スクリプト、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ / ファクター計算、AI を使ったニューススコアリング等のモジュールが含まれます。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買および運用支援ツール群です。主要な役割は次のとおりです。

- 発注・実行エンジン（ExecutionEngine）
- システム／注文／リスク監視（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リサーチ（ファクター計算、特徴量解析）
- AI モジュール（ニュースセンチメント、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

---

## 機能一覧

- 設定管理 (.env 自動読み込み / Settings クラス)
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper 用 DB に記録
  - stop フラグ / pid ファイル管理
- 監視ループ起動スクリプト（run_monitoring）
  - 定期ポーリング（デフォルト 60 秒、環境変数で上書き可）
  - System / Trade / Risk の監視、Kill Switch 評価、アラート連携
- 監視 DB（SQLite）永続化レイヤ（monitoring_db）
  - system_status, trade_logs, positions, risk_logs, dashboard 等のテーブル管理
- リスク監視（drawdown, position limit 等）
- ポートフォリオ構築（候補選定・等配分・スコア配分・リスク制限・単元丸め）
- リサーチ（ファクター計算: モメンタム / ボラティリティ / バリュー 等）
- AI モジュール
  - ニュースを OpenAI に渡して銘柄ごとの ai_score を計算（news_nlp）
  - マクロニュース + ETF MA で市場レジーム判定（regime_detector）
- 運用ユーティリティ
  - .env 対話式作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール（tools.paper_verification_report）

---

## 必要条件 / 依存パッケージ（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（config の YAML 検証にのみ必要）
- （標準）sqlite3

環境によっては追加で pip install が必要です。例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

※ requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順

1. リポジトリをチェックアウトし、仮想環境を作成・有効化する。

2. 依存関係をインストールする（上記参照）。

3. .env を用意する（推奨: 対話式ウィザード）:

```
python -m kabusys.config_setup
```

ウィザードの完了後、生成された .env を確認してください。

4. 設定検証:

```
python -m kabusys.validate_config
# 警告をエラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```

5. 必要なディレクトリ作成（自動で作られることが多いが手動で作る場合）:

- data/
- logs/

6. OpenAI を利用する機能を使う場合、環境変数 `OPENAI_API_KEY` を設定する（または ai 関数に api_key を渡す）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意 / デフォルト:
- KABUSYS_ENV: execution モード。allowed: development, paper_trading, live（default: development）
  - paper_trading 時は MockBroker を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH: data/kabusys.duckdb（分析用）
- SQLITE_PATH: data/monitoring.db（監視 DB、monitoring は常に本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: INFO（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LOG_DIR: logs/
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）
- PAPER_FILL_MODE: paper_trading のモック発注の挙動（instant|partial|never|reject）

注意:
- config.py はプロジェクトルートの .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- validate_config で不足を事前検出してください。

---

## 使い方（主要な実行方法）

パッケージとして実行できます（推奨は仮想環境内で python -m を使用）。

- 設定ウィザード（.env 作成）

```
python -m kabusys.config_setup
```

- 設定検証

```
python -m kabusys.validate_config
```

- 監視ループ起動（SystemMonitor のポーリング）

```
# 環境変数 MONITOR_POLL_INTERVAL で間隔を秒で指定可能（デフォルト 60）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 実行エンジン起動（ExecutionEngine）

```
# 本番・ペーパートレードは KABUSYS_ENV に依存
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```

- ペーパートレード検証レポート

```
# デフォルト DB は data/paper_trading.db。--db で上書き可
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

- AI モジュール（プログラム内呼び出し）
  - OpenAI API キーを環境変数に設定してください:
    - export OPENAI_API_KEY="sk-..."
  - 例（ニューススコアリング）:

```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 4, 10))
```

- 停止 / Kill Switch
  - run_monitoring / run_execution はプロジェクトの data/stop_requested.flag（または同等パス）を監視し、存在すれば安全に停止します。
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を要求します（Monitoring が判定して書き込むことが多い）。

---

## ロギング

- 共通ロギング設定: kabusys.utils.logging_setup.setup_logging を全スクリプトが呼び出し、次の出力先を設定します:
  - コンソール（stdout）
  - ファイル: <LOG_DIR>/<app_name>.log を日次ローテーション（30 日分保持）
- LOG_LEVEL 環境変数で出力レベルを制御できます（デフォルト INFO）。
- ディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

---

## 監視 DB スキーマ（概要）

monitoring_db.init_monitoring_db により作成される主要テーブル:

- system_status: CPU/メモリ/ディスク/プロセス状態のポーリングログ
- trade_logs: 発注イベントのログ（event_type: Created/Sent/Filled 等、latency_ms を含む）
- positions: 現在のポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスク関連アラート（DRAWDOWN_ALERT, POSITION_LIMIT 等）
- dashboard: ダッシュボード集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

マイグレーション処理で不足列（peak_value, latency_ms）を追加する仕組みが含まれます。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル／ディレクトリのツリー（抜粋）です。

```
src/kabusys/
├─ __init__.py
├─ config.py
├─ config_setup.py
├─ validate_config.py
├─ run_monitoring.py
├─ run_execution.py
├─ utils/
│  ├─ __init__.py
│  ├─ logging_setup.py
│  └─ process_priority.py
├─ monitoring/
│  ├─ monitoring_db.py
│  ├─ system_monitor.py
│  ├─ trade_monitor.py         # (実装あり)
│  ├─ risk_monitor.py
│  ├─ monitoring_engine.py
│  ├─ kill_switch.py
│  └─ alert_manager.py         # (実装あり)
├─ execution/                   # ExecutionEngine, OrderManager 等
│  ├─ execution_engine.py
│  ├─ order_manager.py
│  ├─ order_repository.py
│  ├─ broker_factory.py
│  └─ risk_manager.py
├─ portfolio/
│  ├─ portfolio_builder.py
│  ├─ position_sizing.py
│  └─ risk_adjustment.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ tools/
│  └─ paper_verification_report.py
...
```

（実際のリポジトリにはさらに多くのモジュール・補助ファイルがあります）

---

## 運用上の注意 / ベストプラクティス

- 本番実行時（KABUSYS_ENV=live）は .env の内容を慎重に管理し、LINE など通知先設定を確認してください（validate_config の live チェックを参照）。
- Paper Trading は本番 DB と完全分離されています。KABUSYS_ENV=paper_trading を使用することで data/paper_trading.db に記録されます。
- デフォルトの監視 DB は data/monitoring.db です。バックアップ・パーミッション管理を検討してください。
- OpenAI／外部 API との連携は失敗を許容する設計（リトライ・フォールバック）ですが、API キーの漏洩には十分注意してください。
- stop フラグ（stop_requested.flag / kill.flag）を使った安全停止の運用を推奨します（直接プロセスを kill するより安全です）。

---

## よくあるコマンドまとめ

- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- 監視開始: python -m kabusys.run_monitoring
- 実行エンジン開始: python -m kabusys.run_execution
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

---

不明点や追加で欲しいドキュメント（API リファレンス、設定項目の詳述、ユースケース別運用手順など）があれば教えてください。README をその要求に合わせて拡張します。