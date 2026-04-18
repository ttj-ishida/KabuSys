# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群です。  
このリポジトリには、戦略・ポートフォリオ構築、実行エンジン、監視、研究ユーティリティ、AI（ニュースNLP／レジーム判定）など、実運用を想定したコンポーネント群が含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するライブラリ兼アプリケーション群です。主な役割は以下:

- 戦略側（ファクター計算、特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム調整）
- 実行エンジン（Broker クライアント経由で発注、ペーパートレード対応）
- 監視（リソース／プロセス監視、滞留注文・約定異常・ドローダウン検知、Kill Switch）
- AI モジュール（OpenAI を使ったニュースセンチメント、マクロセンチメント → レジーム判定）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート生成）

設計方針として、DB（DuckDB/SQLite）を使ったデータ管理、外部 API 呼び出しは明示的にキーを渡す/環境変数で渡す、安全フェイル（API 失敗時のフォールバック）などが考慮されています。

---

## 主な機能一覧

- 実行関連
  - run_execution: ExecutionEngine を起動（本番 / paper_trading 切替、pid/stop フラグ対応）
  - BrokerClientFactory（kabuステーション or MockBroker）

- 監視関連
  - run_monitoring: SystemMonitor をポーリングで実行（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルの管理
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager

- ポートフォリオ構築（純粋関数）
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk-based / equal / score）
  - セクターキャップ、レジーム乗数適用

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等

- AI（OpenAI）
  - news_nlp.score_news: raw_news を集約して LLM で銘柄ごとにセンチメントを付与（ai_scores テーブルへ）
  - regime_detector.score_regime: ETF の MA200 とマクロニュースの LLM 評価を合成して 'bull'/'neutral'/'bear' を判定し書き込み

- 開発 / 運用ツール
  - config_setup: 対話式で .env を生成・更新
  - validate_config: 起動前に環境変数・config/*.yaml を検証
  - tools.paper_verification_report: ペーパートレード DB を集計し PASS/FAIL レポート出力

- ユーティリティ
  - ロギング設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## 前提 / 必要環境

- Python 3.10+
  - （ソース内で `X | Y` など Python 3.10 の型構文を使用）
- 外部ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に任意）
- OS: Linux / macOS / Windows（各プラットフォームでの挙動差はある）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install duckdb psutil openai pyyaml
# またはパッケージが準備されていれば:
# pip install -e .
```

（requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数設定
   - 推奨: プロジェクトルートに .env を置く（`python -m kabusys.config_setup` で対話式ウィザード）
   - 重要な環境変数例:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db） — 監視は本番 sqlite_path を使用
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB: data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR
5. 設定検証:
```
python -m kabusys.validate_config
# 警告も FAIL 扱いにしたい場合:
python -m kabusys.validate_config --strict
```

6. data/logs ディレクトリの作成（通常はセットアップ時に自動作成されますが、権限により失敗する可能性あり）
```
mkdir -p data logs
```

注意:
- run_monitoring は説明文どおり「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」します。  
- run_execution は paper_trading 環境時に PAPER_TRADING_SQLITE_PATH を使い本番 DB と分離します。

---

## 使い方（代表的なコマンド）

- 環境ウィザード（.env 作成）
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- 実行エンジン起動
```
python -m kabusys.run_execution
```
- 補足:
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中の停止は data/stop_requested.flag を作成するか、ExecutionEngine が kill.flag を検出して停止します。

- 監視プロセス起動（ポーリング）
```
# デフォルトは 60 秒間隔
python -m kabusys.run_monitoring

# 間隔を変更する場合（秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- 補足:
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使います（監視 DB は同一で管理する想定）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで次のループで終了します。

- Paper Trading 検証レポート生成
```
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定する場合
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- OpenAI を使った AI 処理（ライブラリ関数として利用）
  - ニューススコア付与（DuckDB 接続を渡して呼び出す）:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  これらは CLI エントリポイントを持ちません。スクリプトやスケジューラから import して利用してください。api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。

---

## 停止 / Kill Switch / フラグ操作

- 実行の停止（監視・実行エンジン共通）
  - プロジェクトルート/data/stop_requested.flag を作成すると、run_execution/run_monitoring は次のポーリング／ループで検出して終了します。
- 強制停止（Kill Switch）
  - KillSwitch はリスク条件を満たした際に data/kill.flag を書き込みます。ExecutionEngine は起動時や定期チェックでこのファイルを検知して停止します。
  - kill.flag を手動で削除するには:
    ```
    rm data/kill.flag
    ```
  - 環境変数 KILL_FLAG_CLEAR_ON_START=1 を設定すると、ExecutionEngine 起動時に kill.flag を自動クリアする動作になります（本番では 0 推奨）。

---

## ログ

- ログ出力先（デフォルト）: logs/<app_name>.log
  - run_execution → logs/execution.log
  - run_monitoring → logs/monitoring.log

- ログは日次ローテーション（30 日分保持）されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

ログレベルは環境変数 LOG_LEVEL で変更可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。

---

## ディレクトリ構成

（src 配下を簡潔に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py                — ニュース NLP（OpenAI）によるスコア付与
    - regime_detector.py         — マクロ + MA200 によるレジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py           — SQLite テーブル初期化・CRUD ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - (ExecutionEngine, order manager/repository, broker factory 等 — 実行ロジック)
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                         — 実行時に使用するデータディレクトリ（DB / フラグファイル等）
  - logs/                         — ログ出力先（デフォルト）

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （各 YAML ファイルはデプロイ時に必要。存在しない場合は警告が出ます。generate スクリプト等で生成してください）

---

## .env の最小例

プロジェクトルートに .env を配置する例（本番では機密値を適切に管理）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

推奨は `python -m kabusys.config_setup` による対話式生成です。

---

## 注意事項 / トラブルシューティング

- Python バージョン: 3.10 以上を推奨。型ヒントに | 記法等を使用しています。
- OpenAI 関連:
  - API キーは OPENAI_API_KEY または各関数の api_key 引数で指定。
  - API のレート制限や一時エラーはリトライで対処する設計ですが、運用時はキーの割当とレートを確認してください。
- プロセス優先度設定:
  - set_process_priority("high") を呼びます。OS・権限により設定できない場合は警告が出ます（権限昇格が必要な場合あり）。
- DB ファイル:
  - monitoring は run_monitoring が本番 sqlite_path を使用する点に注意ください（監視は常に本番 DB を参照）。
  - paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使うため、本番 DB と完全分離できます。
- ログディレクトリ作成に失敗するとファイル出力は無効化されコンソールのみ出力になります。パーミッションを確認してください。
- .env の自動ロードはデフォルトで有効です。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

もし README に追加して欲しい内容（例: Deployment 手順、Systemd / supervisor サービスユニット例、詳細な API 仕様ドキュメント等）があれば教えてください。必要に応じてサンプル systemd ユニットや docker-compose 例も用意します。