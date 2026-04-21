# KabuSys

日本株向け自動売買システム（参考実装）

このリポジトリは日本株自動売買システム「KabuSys」のコアモジュール群のサンプル実装です。売買ロジック・リサーチ・監視・ランタイム周辺のユーティリティを含み、ローカル開発・ペーパートレード・本番運用を想定した設計になっています。

主な設計方針
- DuckDB を分析用データベース、SQLite を監視 / 履歴用 DB に使用
- .env による環境変数管理（自動ロード機能あり）
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と完全分離
- OpenAI を利用したニュース NLP / レジーム判定機能（任意）
- 監視コンポーネントにより安全装置（Kill Switch, Risk Monitor）を提供

---

## 機能一覧

- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は PID ファイルを生成（data/execution.pid）し、stop フラグで停止可能

- 監視（Monitoring）
  - src/kabusys/run_monitoring.py
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングし、監視ログを SQLite に永続化
  - Kill Switch（drawdown などの条件で ExecutionEngine を停止するための flag 書き込み）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整（デフォルト 60 秒）

- 設定管理 CLI / ウィザード
  - src/kabusys/config_setup.py : 対話式で .env を作成・更新
  - src/kabusys/validate_config.py : 起動前に環境変数・設定ファイルを検証（--strict オプション有）

- ポートフォリオ構築ユーティリティ
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制約など（純粋関数群）

- リサーチ（ファクター計算）
  - src/kabusys/research/* : momentum / value / volatility 等のファクター計算、forward returns、IC 計算など（DuckDB を利用）

- AI（任意）
  - src/kabusys/ai/news_nlp.py：ニュース記事を OpenAI に投げて銘柄別センチメントを計算
  - src/kabusys/ai/regime_detector.py：ETF の MA とマクロニュースを組み合わせて市場レジームを判定
  - OpenAI API キー（OPENAI_API_KEY）が必要

- ツール
  - src/kabusys/tools/paper_verification_report.py：Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等を集計）

- 共通ユーティリティ
  - ロギングセットアップ（TimedRotatingFileHandler／コンソール出力）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.9+（各自の環境に合わせてください）
- system に sqlite3 があれば標準で利用可能
- DuckDB、psutil、openai などをインストール

推奨のインストール例:
```
pip install duckdb psutil openai pyyaml
```
※ requirements.txt は本リポジトリに含まれていないため、必要に応じて上記パッケージをインストールしてください。

1. リポジトリをクローン／配置
2. .env を作成
   - 対話式に作る場合:
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（デフォルト INFO）

3. 設定検証（任意だが推奨）
```
python -m kabusys.validate_config
# 警告もエラー扱いにする場合:
python -m kabusys.validate_config --strict
```

4. データディレクトリ等の作成（自動的に作られることが多いですが手動でも可）
```
mkdir -p data logs
```

---

## 使い方（起動・運用）

- 実行エンジン（ExecutionEngine）を起動
  - 通常（paper_trading などは .env の KABUSYS_ENV で指定）:
    ```
    python -m kabusys.run_execution
    ```
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します（安全措置）
  - 実行中は data/execution.pid に PID が保存されます

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
    （値は秒。1 秒未満や 0 は無効でデフォルト 60 秒にフォールバック）
  - 監視プロセスは stop フラグ（data/stop_requested.flag が存在）で安全にループを止めます

- Kill Switch（ExecutionEngine を停止する信号）
  - KillSwitch は data/kill.flag（デフォルト）を作成します。ExecutionEngine は起動時や監視によりこのフラグを検出して停止します
  - Kill 条件例: ドローダウン閾値超過、ポジション数上限超過など

- Paper Trading レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は data/paper_trading.db。別パスを使う場合は --db オプション or 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能の利用
  - OPENAI_API_KEY を .env に設定するか、関数呼び出し時に api_key を渡してください
  - news_nlp.score_news / regime_detector.score_regime を呼び出すと DuckDB のテーブルを参照して結果を書き込みます

停止・フラグ操作の例
- 監視・実行プロセスを止めたい（安全停止）:
  - 監視プロセス・実行エンジン両方を止めたい場合:
    ```
    touch data/stop_requested.flag
    ```
    これらのランナーはループ内で stop_requested.flag の存在を確認して終了します
- kill.flag を消す（起動時に自動クリアしない設定で手動クリアする場合）:
  ```
  rm data/kill.flag
  ```
  - Settings.kill_flag_clear_on_start が 1 の場合、ExecutionEngine 起動時に自動で kill.flag をクリアします（本番環境では 0 を推奨）

ログ
- デフォルトは logs/ ディレクトリにアプリ別ログが出力されます（例: logs/execution.log, logs/monitoring.log）
- ログの設定は kabusys.utils.logging_setup.setup_logging によって統一管理されます

---

## 環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時の DB）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring に適用）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（instant / partial / never / reject）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み取り / 自動 .env ロード / Settings クラス
- config_setup.py
  - .env を対話式で作成するウィザード
- validate_config.py
  - 起動前チェック用 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring 起動スクリプト

サブパッケージ（主要ファイルのみ抜粋）
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - monitoring_engine.py
  - risk_monitor.py
  - kill_switch.py
  - (TradeMonitor, AlertManager 等は同ディレクトリに存在)
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

その他
- data/ (実行時に作成される想定)
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用、任意）
  - execution.pid / stop_requested.flag / kill.flag
- logs/（ログ出力先）

---

## 追加の注意点・運用メモ

- 本プロジェクトはサンプル実装のため、実運用前に十分なテスト・監査を行ってください。特に KABUSYS_ENV=live の場合は誤発注や資金管理に注意が必要です。
- .env は機密情報を含むため Git には絶対にコミットしないでください。
- OpenAI 周りは API 料金が発生します。大量バッチ呼び出し時はレート制限や料金に注意してください。
- ペーパートレードは本番 DB から分離されますが、ロジックの差異や MockBroker の挙動が本番と完全一致する保証はありません。評価時は実環境との差異を認識してください。
- config/*.yaml（system_config.yaml 等）は設定ファイルとして参照される想定です。validate_config はこれらの存在や YAML パースをチェックします（PyYAML がある場合のみ中身の検証を実施）。

---

README に記載のない個別の実装詳細（ExecutionEngine の API、OrderManager の仕様、TradeMonitor の具体的な判定基準など）は各モジュールのソースコード内の docstring を参照してください。質問や追加ドキュメントの要望があれば教えてください。