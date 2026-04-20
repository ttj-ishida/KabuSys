# KabuSys

日本株自動売買システム「KabuSys」の簡易 README。  
本リポジトリは戦略・ポートフォリオ構築、発注エンジン、監視、研究ツール、AI ベースのニュース NLP 等を含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株自動売買のための統合フレームワークです。主要コンポーネントは次のとおりです。

- ExecutionEngine: ブローカーとのやりとり・リスク管理・注文管理を行う発注エンジン
- Monitoring: システム稼働・注文状況・リスク（ドローダウンなど）を監視しアラートや Kill Switch を管理
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター上限などの純粋関数群
- Research: DuckDB に格納された価格データを用いたファクター計算・特徴量解析
- AI: ニュースの NLP スコアリング、レジーム検出（OpenAI API を利用）
- Tools: ペーパートレード検証レポート等のユーティリティスクリプト
- 設定管理 / CLI ユーティリティ: .env ウィザード、設定検証ツール 等

設計方針として、分析処理は DuckDB、監視や履歴は SQLite を使用し、本番とペーパートレードは DB を分離できるようになっています。

---

## 主な機能一覧

- 発注／注文管理（実ブローカー or MockBrokerClient）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- モニタリング
  - CPU / メモリ / ディスク使用率、プロセス死活、データ鮮度の監視
  - リスク監視（ドローダウン、ポジション上限など）
  - Kill Switch（条件を満たすと data/kill.flag を書き込む）
- ポートフォリオ構築
  - シグナルの候補抽出、等配分・スコア加重、リスクベースの株数算出
  - セクター集中制限、レジームに応じた乗数
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）等
- AI（OpenAI）
  - ニュース記事を LLM（gpt-4o-mini 等）でスコアリングし ai_scores に保存
  - マクロニュース + ETF MA 乖離を用いた市場レジーム判定
- 運用支援ツール
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト

---

## 前提・依存関係

最低限の想定環境（目安）:

- Python 3.10+
- パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容チェック用）
- その他: ネットワーク接続（本番でブローカー/API を使う場合）、OpenAI API キー（AI 機能を使う場合）

requirements.txt を用意している場合はそれを利用してください。ない場合は手動でインストールしてください:

例:
pip install duckdb psutil openai PyYAML

---

## 環境変数（主なもの）

設定は .env ファイルまたは環境変数で行います。主要なキー（詳細は src/kabusys/config.py、config/*.yaml を参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能で使用)
- KABUSYS_ENV: execution モード
  - development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- PAPER_FILL_MODE (paper_trading の Fill 動作: instant | partial | never | reject)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL (監視ループの秒数を上書き; デフォルト 60)

注意:
- .env は決して Git にコミットしないでください（README・テンプレートのみを共有）。
- live 環境（KABUSYS_ENV=live）は慎重に取り扱ってください。validate_config による確認を強く推奨します。

---

## セットアップ手順

1. リポジトリをクローン / 展開

2. Python 環境の準備
   - 仮想環境を作成（推奨）
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
   - 依存パッケージをインストール
     pip install duckdb psutil openai PyYAML

3. .env の作成（対話式）
   - ウィザードで作成:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動で作成
   - 重要: .env を絶対にリポジトリにコミットしない

4. 設定検証
   - 自動検証:
     python -m kabusys.validate_config
   - 厳格モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict

5. データディレクトリ / ログディレクトリの準備（必要に応じて）
   - デフォルトは `data/` と `logs/`。多くのスクリプトが自動作成しますが、権限やパスを事前確認してください。

---

## 起動・使い方

- ExecutionEngine（発注エンジン）起動
  - 本番 / 開発 / ペーパートレードの動作は KABUSYS_ENV に依存します。
  - 起動:
    python -m kabusys.run_execution
  - ペーパートレード:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  - 注意: ペーパートレード時は paper_sqlite_path（デフォルト data/paper_trading.db）に発注ログが記録され、本番 DB と分離されます。

- Monitoring（監視プロセス）起動
  - 起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）:
    export MONITOR_POLL_INTERVAL=30

  - 監視は monitoring DB（Settings.sqlite_path）に書き込みます。monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（運用上の注意）。

- 停止フロー / フラグ
  - 停止をリクエストするにはプロジェクトルートの data/stop_requested.flag を作成してください（run_execution/run_monitoring は存在を検知して終了します）。
  - Kill Switch（自動停止）:
    - risk 部分で条件を満たすと data/kill.flag が書き込まれ、エンジン停止シグナルとなります。
    - 設定により起動時に kill_flag を自動クリアすることが可能（KILL_FLAG_CLEAR_ON_START=1）※本番では推奨しません。

- Paper Trading 検証レポート
  - ペーパートレード DB を使って実行結果を検証するツール:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。

- AI 機能（ニュース NLP / レジーム）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してください。
  - ニューススコア付与（プログラム的に利用）:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

- ロギング
  - 共通のユーティリティ `kabusys.utils.logging_setup.setup_logging` を各起動スクリプトが呼んでいます。
  - デフォルトログディレクトリ: logs/
  - 各アプリ名に応じて logs/<app_name>.log に日次ローテーションで保存されます。

---

## 主要 CLI / スクリプト一覧

- python -m kabusys.config_setup
  - .env の対話式作成・更新ウィザード

- python -m kabusys.validate_config [--strict]
  - .env および config/*.yaml のチェック

- python -m kabusys.run_execution
  - ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）

- python -m kabusys.run_monitoring
  - Monitoring のポーリングループを起動

- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - Paper Trading の検証レポートを生成

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数・設定管理
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

その他:
- data/                   — データファイル（デフォルトの DB 等）
  - monitoring.db (デフォルト)
  - paper_trading.db (ペーパートレード)
  - execution.pid, stop_requested.flag, kill.flag など
- logs/                   — ログ出力（デフォルト）

---

## 運用上の注意

- .env は絶対にコミットしないでください（クレデンシャルが含まれます）。
- 本番（KABUSYS_ENV=live）で起動する前に validate_config を実行し、設定を慎重に確認してください。
- Monitoring は監視用 sqlite DB を参照/更新します。Monitoring 側は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する実装になっています。テスト/ペーパートレードで DB 分離したい場合は設定を見直してください。
- OpenAI 等の外部 API への呼び出しは課金・レート制限リスクがあります。API キーやコスト管理は十分に行ってください。
- process priority / CPU affinity の設定は psutil を用いて行っていますが、権限や OS により動作しない場合があります（警告が出ます）。

---

この README はコードベースの概要と基本的な使い方をまとめたものです。詳細な実装・設計方針は各モジュールの docstring やソースを参照してください。必要であれば README に含めたい追加の使い方や設定例を教えてください。