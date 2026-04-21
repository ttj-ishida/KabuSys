# KabuSys

日本株自動売買システムのコアモジュール群（ライブラリ + 起動スクリプト）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・AI を含む運用向けコンポーネントをまとめています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要な関心事は以下です。

- シグナル／ファクター計算（research）
- ポートフォリオ構築・ポジションサイズ決定（portfolio）
- 発注管理・実行エンジン（execution） — 本番 / ペーパートレードに対応
- 監視・アラート・Kill Switch（monitoring）
- ニュースの NLP スコアリング・市場レジーム判定（ai）
- 実行環境設定ウィザード・設定検証ツール（config_setup / validate_config）
- 運用支援ツール（tools）

設計上の注意点（抜粋）：
- 計算ロジックは可能な限り純粋関数（副作用なし）で実装。
- 本番データベース・ペーパートレード DB は分離（ペーパートレード時は `data/paper_trading.db` を使用）。
- OpenAI 呼び出し・外部 API は明示的にキー指定。デフォルト環境変数 `OPENAI_API_KEY` を参照。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution: ExecutionEngine を起動（KABUSYS_ENV により mock/real broker を切替）
  - run_monitoring: SystemMonitor をポーリングで起動
- 設定管理
  - .env の自動ロード / 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- モニタリング
  - system_monitor: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor: 発注ログの健全性チェック（滞留注文、価格異常など）
  - risk_monitor: ドローダウン / ポジション上限チェック、dashboard データ更新
  - kill_switch: 条件に応じて `data/kill.flag` を書いて ExecutionEngine を停止
  - monitoring_engine: 上記を統合して定期実行・アラート送出
- ポートフォリオ関連
  - 銘柄選定（スコア順）、等金額/スコア加重配分、セクター制約、ポジションサイズ最適化（lot 単位で丸め）
- 研究用モジュール
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI モジュール
  - news_nlp: ニュースを LLM（OpenAI）でセンチメント評価し ai_scores に登録
  - regime_detector: ma200 とマクロニュースを組み合わせて market_regime を算出
- 運用ツール
  - paper_verification_report: ペーパートレード DB を集計し PASS/FAIL レポートを生成

---

## 必要要件（概略）

- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml のパース検証用）

pip インストール例（requirements.txt がない場合の最小例）:
```
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／よく使う:
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: (デフォルト) `data/kabusys.duckdb`
- SQLITE_PATH: (監視用 DB) (デフォルト) `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH: (ペーパートレード時の DB) (デフォルト) `data/paper_trading.db`
- OPENAI_API_KEY: OpenAI 呼び出し用（ai モジュール使用時）
- LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`...
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: `logs/`）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）（デフォルト: 60）

注意:
- KABUSYS は .env / .env.local をプロジェクトルートから自動ロードします（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
4. 環境変数（.env）を作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` をプロジェクトルートに作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
5. 設定検証（任意）
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いになります。

6. データディレクトリやログディレクトリは起動時に自動作成されますが、必要に応じて手動で作成して権限を確認してください。

---

## 使い方（起動例）

- ExecutionEngine を起動（通常 / ペーパートレードは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、`data/paper_trading.db` に記録します（本番 DB と分離）。
  - 停止は `data/stop_requested.flag` の作成で行えます（run_execution はこのフラグを監視して停止）。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を秒で上書き可能（デフォルト 60 秒）。
  - 監視は本番の sqlite_path を常に使います（環境にかかわらず）。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定できます。

ログ:
- ログはデフォルトで `logs/<app_name>.log` に日次ローテートで出力されます。アプリ名は起動スクリプトで指定（例: `execution`, `monitoring`）。
- ログディレクトリ作成に失敗した場合は標準出力のみで継続します（警告が出ます）。

停止フラグ / PID:
- 起動スクリプトは `data/stop_requested.flag` を監視します。これを作成すると安全に停止できます。
- ExecutionEngine 用 PID ファイル: `data/execution.pid`（`run_execution` が使用）。

---

## 注意事項 / 運用上のヒント

- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `1` にするのは危険です。kill flag の自動クリアは推奨されません。
- OpenAI API 呼び出しを行う機能（news_nlp, regime_detector）を使うには `OPENAI_API_KEY` が必要です。失敗時は多くの処理がフェイルセーフ（スコア 0.0 等）で継続しますが、ログを確認してください。
- DuckDB や SQLite のファイルパスは `.env` で明示的に設定可能です。運用時は十分なディスク容量／バックアップを考慮してください。
- `monitoring` コンポーネントは監視データを SQLite に永続化します。スキーマは `kabusys.monitoring.monitoring_db.init_monitoring_db` で自動作成・マイグレーションされます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                   — 環境変数 / Settings
- config_setup.py             — .env 対話ウィザード
- validate_config.py          — 設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
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
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
- execution/                   — 発注・リスク管理・エンジン関連（省略）
- data/                        — 実行時生成: DB / pid / flag など（プロジェクトルート直下に存在）

（注）上はリポジトリの主要ファイルのみ抜粋した構成です。詳細は `src/kabusys` 配下の各モジュールを参照してください。

---

## 付録: よく使うコマンドまとめ

- .env 作成（ウィザード）
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
- 監視ループ起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README は以上です。必要であれば、セットアップ用の requirements.txt や systemd / supervisor 用のユニットファイル例、Dockerfile などの追補ドキュメントも作成します。どの部分を優先して補足しますか？