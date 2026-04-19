# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
このリポジトリは、データ処理・リサーチ、ポートフォリオ構築、発注エンジン、監視・アラート、AI（ニュース NLP / レジーム判定）などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下機能を組み合わせ、実戦運用とペーパートレードの両方をサポートする自動売買プラットフォームです。

- データ格納・分析用に DuckDB を利用
- 監視・ログ保持に SQLite（monitoring.db）を利用
- 実行（ExecutionEngine）は環境に応じて実ブローカーまたはモックを使用
- ニュースセンチメントやマクロ判定に OpenAI（gpt-4o-mini）を利用する機能を提供
- ポートフォリオ構築/リスク管理/ポジションサイズ決定の純粋関数群を提供
- 監視ループ・Kill Switch による安全停止、監視アラート出力

設計上の方針として、ルックアヘッドバイアス防止やフェイルセーフ（API失敗時のフォールバック）に配慮しています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` では MockBroker を使用し DB を分離
- 監視ループ起動スクリプト（SystemMonitor ポーリング）: `kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可
- 監視データ永続化（SQLite）/監視ロジック: `kabusys.monitoring.*`
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - リスク監視（ドローダウン、保有上限）と Kill Switch 機能
- ポートフォリオ構築・比率計算: `kabusys.portfolio.*`
  - 候補選定 / スコア重み / 等金額配分 / ポジションサイズ算出（LOT丸め等）
- リサーチ（ファクター計算 / 特徴探索）: `kabusys.research.*`
  - momentum, volatility, value, forward returns, IC（スピアマンランク）など
- AI系機能:
  - ニュース NLP（銘柄別センチメント取得 / ai_scores 書き込み）: `kabusys.ai.news_nlp`
  - 市場レジーム判定（ma200 + マクロセンチメント合成）: `kabusys.ai.regime_detector`
- 運用ツール:
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提・依存関係

- Python 3.10 以上（ソース内で | 型注釈を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証に任意）
- その他: SQLite は標準ライブラリで利用

requirements.txt はリポジトリに含まれていない場合があります。一般的なインストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。

2. Python 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. データ・ログディレクトリ作成（任意、設定で変更可）:

```bash
mkdir -p data logs
```

4. .env を用意（対話式ウィザード推奨）:

```bash
python -m kabusys.config_setup
```

ウィザードは .env（デフォルトはプロジェクトルート）を生成・更新します。主要な必須環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- OPENAI_API_KEY（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート通知に任意）
- LOG_LEVEL（DEBUG/INFO/...）

5. 設定検証（必ず推奨）:

```bash
python -m kabusys.validate_config
# 警告を FAIL 扱いにする場合:
python -m kabusys.validate_config --strict
```

validate_config は .env と config/*.yaml の存在や基本整合性をチェックします。PyYAML がインストールされていると YAML のパースも行います。

---

## 環境変数の重要な挙動

- KABUSYS_ENV:
  - development: 開発用（発注なしなど）
  - paper_trading: ペーパートレード（MockBroker、専用 SQLite）
  - live: 本番（実ブローカー）
- MONITOR_POLL_INTERVAL:
  - 監視ループのポーリング間隔（秒）。run_monitoring にて読み込む（デフォルト 60 秒）。
- PAPER_FILL_MODE:
  - paper_trading 時のモック約定挙動（instant, partial, never, reject）
- KILL_FLAG_CLEAR_ON_START:
  - 本番環境での自動 Kill Flag クリアを制御（0 推奨）

---

## 使い方（実行例）

- 実行エンジン（ExecutionEngine）起動:

```bash
python -m kabusys.run_execution
```

- 監視ループ起動:

```bash
# ポーリング間隔を上書きする例（30秒）
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```

- 設定ウィザード（.env 作成）:

```bash
python -m kabusys.config_setup
```

- 設定検証:

```bash
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポート生成:

```bash
# デフォルト DB (data/paper_trading.db) の全期間
python -m kabusys.tools.paper_verification_report

# 期間を指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI 機能（プログラム的利用）:
  - news_nlp.score_news(conn, target_date, api_key=...)
  - ai.regime_detector.score_regime(conn, target_date, api_key=...)

（DuckDB 接続オブジェクトを渡して呼び出します。OPENAI_API_KEY を環境変数に設定していれば api_key は省略可）

---

## 運用上の注意

- run_execution は KABUSYS_ENV により発注先や使用 DB を切り替えます。paper_trading は本番 DB と完全に分離されますが、本番モード（live）での設定ミスは重大な事故に繋がるため、validate_config の実行や LINE 通知設定を推奨します。
- Kill Switch（data/kill.flag）や stop フラグ（data/stop_requested.flag）を使用し、外部から安全にプロセスを停止できます。KILL_FLAG_CLEAR_ON_START 設定には注意してください（本番では 0 推奨）。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- OpenAI 呼び出しはレートリミットや一時エラーを考慮してリトライ実装がありますが、API キー管理やコストには十分注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの一覧と簡単な説明（プロジェクトルートの `src/kabusys` を基点）。

- src/kabusys/
  - __init__.py — パッケージのメタ情報（__version__ 等）
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス（各種設定取得）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - utils/
    - logging_setup.py — 統一ログ設定（コンソール + 日次ファイルローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態 / データ鮮度チェック
    - trade_monitor.py — （trade 関連の監視ロジック）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書込み・評価
    - monitoring_engine.py — 監視コンポーネント統合ループ
    - alert_manager.py — （Line 等への通知管理）

  - execution/  (実行関連の各コンポーネント)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数算出・スケーリング・LOT丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — forward returns / IC / 統計サマリー

  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

  - monitoring_db.py, tools/, portfolio/, research/ 等 その他モジュールも含む

（注）一部ファイル・詳細実装はここに抜粋されている以外にも存在する場合があります。

---

## サンプル .env（最低限）

実運用では .env.example を参照して作成してください。最小例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_api_key_here
```

このファイルは絶対にリポジトリに含めないでください（機密情報を含むため）。

---

## 開発・デバッグのヒント

- ログレベルを DEBUG にすると内部の計算過程や SQL 実行ログを確認できます（環境変数 LOG_LEVEL=DEBUG）。
- validate_config で config/*.yaml のパースチェックを行うため、PyYAML を入れると有益です。
- AI 関連関数は OpenAI クライアント呼び出し部分をモックできるように設計されています。ユニットテストでは該当関数を patch して外部 API を切り離してください。
- DuckDB 接続を直接作ってリサーチ関数を対話的に試すとデータ処理の挙動確認がしやすいです。

---

## ライセンス / 貢献

この README はコードベースの概要説明です。ライセンスやコントリビューションガイドが別途用意されている場合はプロジェクトルートの該当ファイルを参照してください。

---

必要であれば README にさらに以下を追加します：
- 詳しい設定例（production / staging / paper_trading）
- systemd / Supervisor 用のユニットファイル例
- よくあるトラブルシュート（OpenAI エラー、DuckDB ファイル権限、psutil AccessDenied など）

どの追加情報が必要か教えてください。