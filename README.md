# KabuSys

日本株向け自動売買システムの一部を実装した Python パッケージ。  
このリポジトリには、実行エンジン・監視機能・ポートフォリオ構築・リサーチ・Ai（ニュース NLP / レジーム判定）などのモジュールが含まれます。

## プロジェクト概要
- 実運用を想定した自動売買向けコンポーネント群（ExecutionEngine、モニタリング、リスク管理、アラートなど）。
- DuckDB／SQLite を用いた市場データ・監視ログの永続化。
- Paper Trading（ペーパートレード）モードと Live モードの分離。
- ニュースを LLM（OpenAI）でスコアリングする Ai モジュール、ETF を基にしたレジーム判定。
- ポートフォリオ構築やポジションサイジングの純粋関数群（テスト容易）。

## 主な機能一覧
- Execution
  - ExecutionEngine／OrderManager／RiskManager／Reconciler（発注・約定管理）
  - paper_trading モード：MockBrokerClient を使用し paper DB に分離して記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク・プロセス・データ鮮度チェック
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件により `data/kill.flag` を書き込み ExecutionEngine 停止
  - MonitoringEngine：各モニタの統括ポーリング（アラート送信）
- Ai
  - news_nlp：OpenAI（gpt-4o-mini）でニュースをセンチメントスコア化し `ai_scores` に書き込み
  - regime_detector：ETF 200日 MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- Research / Portfolio
  - factor_research, feature_exploration：ファクター計算、IC（Information Coefficient）など
  - portfolio：候補選定、重み計算、セクター制限、ポジションサイズ計算
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

## 要件（依存パッケージ）
- Python 3.9+
- duckdb
- psutil
- openai (Ai 機能使用時)
- PyYAML（config 検証のため、任意）
- 標準ライブラリ（sqlite3, logging, threading, datetime, pathlib など）

pip でインストールする場合の例（仮想環境推奨）:
```
pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. リポジトリをクローン／チェックアウトする。

2. 仮想環境を用意して依存をインストールする（上記参照）。

3. .env を作成する（環境変数設定）。
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは `.env` を手動で作成（`.env.example` を参考にする想定）。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を用いる機能を使う場合:
     - 環境変数 OPENAI_API_KEY を設定

4. 設定検証（起動前チェック）:
```
python -m kabusys.validate_config       # 警告は許容
python -m kabusys.validate_config --strict  # 警告も失敗扱い
```

5. 必要に応じてデータディレクトリを作成:
```
mkdir -p data
```

## 使い方（主なエントリポイント）

- Execution Engine（実行エンジン）起動:
  - 実運用（KABUSYS_ENV に依存）
  - エントリ:
    - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper DB（デフォルト: data/paper_trading.db）に記録して本番 DB と分離します。
    - 実行中は `data/execution.pid` に PID を書きます。`data/stop_requested.flag` または `data/kill.flag` の存在で停止処理を行います。

- Monitoring（監視ループ）起動:
  - エントリ:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 注意:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（デフォルト: data/monitoring.db）を利用します（ログ／監視用）。
    - 停止フラグファイル: data/stop_requested.flag（存在する場合ループ終了）

- 設定ウィザード:
  - python -m kabusys.config_setup
  - .env の初期作成・更新を対話式で行います。

- 設定検証:
  - python -m kabusys.validate_config

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

## 主要な環境変数（主なもの）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（Ai 機能で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードのフィルモード（instant / partial / never / reject。デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）

## 運用・制御ファイル
- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル。SystemMonitor が存在・生存チェックに使用。
- data/stop_requested.flag: 実行プロセス（monitoring / execution）を優雅に停止させるためのフラグファイル（存在するとループが終了）。
- data/kill.flag: KillSwitch により書き込まれる停止フラグ（ExecutionEngine に即時停止を指示）。
- Kill フロー:
  - Monitoring の RiskMonitor が閾値超過（ドローダウン等）を検知すると KillSwitch が `data/kill.flag` を生成し、ExecutionEngine は次回ループで検知して停止します。

## 注意事項（安全上のガイド）
- 本番環境（KABUSYS_ENV=live）では必ず設定を慎重に確認してください。validate_config は本番向けのチェックを含みます。
- `.env` は決してリポジトリにコミットしないでください（config_setup でも注意書きがあります）。
- OpenAI の利用は API キー管理とコストに注意してください。API 呼び出しはリトライやバックオフ処理を実装していますが、失敗時はフェイルセーフ（代替値）で継続します。

## ライブラリとしての使用例
- ポートフォリオ関連関数（純粋関数、DB に依存しない）:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- 研究用関数:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
- Ai スコアリング:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="YOUR_KEY")

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / Settings
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor 起動スクリプト
  - utils/
    - process_priority.py       — プロセス優先度・CPU affinity 設定
  - execution/                  — 発注・注文管理関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py          — 監視ログ DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

（注: 上記は主要ファイルの抜粋です。細かいモジュールは実際のツリーを参照してください。）

## よくある運用コマンド（例）
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動（バックグラウンド・systemd などで管理することを推奨）:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

追加で README に入れたい内容（インストール済み依存のバージョン、例 .env.example、systemd ユニット例、運用上のチェックリストなど）があれば指示してください。必要に応じて英語版の README も作成できます。