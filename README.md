# KabuSys

日本株向け自動売買システムのコアモジュール群（ライブラリ＋起動スクリプト群）。

このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP / レジーム判定などの機能を備えたモジュール群で構成されています。設計方針として「本番 DB との分離」「ルックアヘッドバイアスの排除」「外部 API 呼び出しのフェイルセーフ化」を重視しています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（主要）
- 使い方（起動 / CLI）
- ファイル・ディレクトリ構成
- 補足と運用メモ

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたコンポーネント群です。主要な要素は以下です。

- ExecutionEngine：発注ロジック・リスク制御・オーダー管理
- Monitoring：プロセス・システム状態・注文ログの監視と Kill Switch
- Portfolio：銘柄選定・重み付け・株数算出（等金額・スコア加重・リスクベース）
- Research：ファクター計算（モメンタム / ボラティリティ / バリュー）や特徴量解析
- AI：ニュースセンチメント（OpenAI）を使ったスコアリング / レジーム判定
- Tools：ペーパートレードの検証レポート生成などの補助ツール
- utils：ログ設定、プロセス優先度設定などの汎用ユーティリティ

設計は主に純粋関数（副作用を持たないもの）と DB IO 層の分離を意識しており、テストや部分運用がしやすい作りになっています。

---

## 機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス稼働）
- 監視データの SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- ExecutionEngine（本番 / ペーパートレードモード切替）
  - Paper Trading 時は MockBrokerClient を用い、専用 DB（data/paper_trading.db）へ記録
- ポートフォリオ構築（候補選定、等分配・スコア重み・リスクベース配分）
- ポジションサイズ計算（単元株丸め、aggregate cap スケーリング）
- セクター集中の制限適用
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ニュース NLP（OpenAI を使用して銘柄別センチメント評価）
- 市場レジーム判定（ETF ma200 とマクロニュースを組み合わせる）
- Paper Trading 検証用レポート生成（期間指定可）
- .env の対話式生成ウィザードと設定検証 CLI

---

## 前提条件

- Python 3.10+
- SQLite（標準で同梱）
- 推奨パッケージ（pipで導入）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度処理はプラットフォーム依存の挙動あり）

必要パッケージはプロジェクトに requirements.txt があればそれを利用、ない場合は上記を個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 必要パッケージをインストール
   （requirements.txt がある場合）
   ```
   pip install -r requirements.txt
   ```
   ない場合は最低限：
   ```
   pip install duckdb psutil openai PyYAML
   ```

4. ディレクトリ作成（ログ / データ用）
   ```
   mkdir -p data logs
   ```

5. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成することを推奨します:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作る場合はプロジェクトルートに `.env` を作成（例は下記「環境変数」セクション参照）。

6. 設定検証（.env と config/*.yaml の整合性をチェック）
   ```
   python -m kabusys.validate_config
   ```
   問題がある場合は `--strict` を付けると警告もエラー扱いになります。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（推奨・デフォルトあり）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番アラート用（任意）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- KILL_FLAG_CLEAR_ON_START: 0|1（本番では 0 推奨）

モニタリング関連:
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60）
- PID_FILE_PATH, KILL_FLAG_PATH: デフォルトは data/execution.pid, data/kill.flag（Settings で参照）

.env の簡易例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-....
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方

### 監視プロセス起動（Monitoring）
Monitoring はシステム状態や注文状況をポーリングし、SQLite に永続化します。

```
python -m kabusys.run_monitoring
```

- ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
- 監視スクリプトは常に「本番用の sqlite_path」を使用します（環境にかかわらず monitoring DB は同じ）。
- 停止はプロジェクトルートの data/stop_requested.flag ファイルを作成することで行えます（監視ループが検知して終了します）。

### 発注エンジン起動（Execution）
ExecutionEngine を起動します。Paper Trading モードでは MockBrokerClient を使用し、paper_trading 用 DB に書き込みます。

```
python -m kabusys.run_execution
```

- KABUSYS_ENV=paper_trading を指定すると、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- 起動時、既に data/stop_requested.flag がある場合は起動せず終了します。
- 実行中に同フラグを作成するとエンジン停止をトリガーします。
- 実行中の PID は data/execution.pid に記録されます。

### .env の対話式作成
```
python -m kabusys.config_setup
```
対話形式で .env を生成・更新します。生成後は `python -m kabusys.validate_config` で検証してください。

### 設定検証
```
python -m kabusys.validate_config
```
--strict を付けると警告も失敗扱いになります。

### Paper Trading 検証レポート
ペーパートレード DB から検証用レポートを出力します。

```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
```

--db オプションで DB パスを明示できます（デフォルトは PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）。

### AI 機能（ニュース NLP / レジーム判定）
- ニュース NLP のスコア付与:
  - ライブラリ関数: kabusys.ai.score_news(conn, target_date, api_key=None)
- レジーム判定:
  - ライブラリ関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

どちらも OpenAI API キー（OPENAI_API_KEY または api_key 引数）が必要です。API 呼び出しは冗長性を考慮してリトライやフェイルセーフを備えています。

---

## 停止・Kill Switch に関する運用メモ

- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）は ExecutionEngine に対する停止シグナル（Kill Switch）です。KillSwitch.evaluate が条件を満たすと書き込みが行われます。ExecutionEngine はこのフラグを読んで安全に停止します。
- stop_requested.flag（data/stop_requested.flag）はスクリプト（monitoring, execution）の外部からの停止要求に使われます。ファイルが存在するとポーリングループを抜けて終了します。
- 本番環境で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag が自動でクリアされますが、本番では 0（クリアしない）を推奨します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・ディレクトリ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_monitoring.py       — Monitoring 起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py      — ロギング設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py      — （注文監視 / ログ参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - monitoring/              # 上述の監視モジュール群
  - tools/
    - paper_verification_report.py

プロジェクトルート:
- data/                    — SQLite DB、PID、flag 等（実行時に作成）
- logs/                    — 日次ローテーションされたログ出力先

---

## 補足 / 運用上の注意

- DB マイグレーションは monitoring_db.init_monitoring_db() が冪等的にテーブル・カラムを作成します。既存 DB にカラムを追加するマイグレーション処理も含まれています。
- OpenAI を使う処理は API 呼び出しに失敗した場合にフェイルセーフ（スコア0やスキップ）する実装になっていますが、API キーの管理やコストには注意してください。
- プロセス優先度や CPU affinity の操作は OS によって権限が必要な場合があります（設定に失敗すると警告を出してスキップします）。
- 本番運用前に必ず `python -m kabusys.validate_config` を実行し、設定が適切か確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup.py でも同旨の警告を出しています）。

---

必要であれば、README の英語版や運用チェックリスト、systemd / Windows サービス用の起動ユニット例、サンプル .env.example を追加で作成します。どれを優先しますか？