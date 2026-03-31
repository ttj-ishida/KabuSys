# KabuSys

KabuSys は日本株向けのデータプラットフォームおよび自動売買補助ライブラリです。  
J-Quants による市場データ取得、DuckDB ベースの ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注トレーサビリティ）などを一貫してサポートします。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない）
- DuckDB を中心に SQL + Python で効率的に処理
- 外部 API 呼び出しは冗長性・リトライ・レート制御を実装
- フェイルセーフ設計（API 失敗時は安全側にフォールバック）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX マーケットカレンダーを差分取得・保存
  - 差分/バックフィル、ページネーション対応、取得タイムスタンプ記録（fetched_at）
- データ品質管理
  - 欠損、重複、スパイク（前日比）や日付不整合のチェック
  - 品質チェック結果を QualityIssue オブジェクトとして収集
- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores）算出
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- リサーチ機能
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 までトレース可能な監査テーブル群を DuckDB に作成・初期化
- 設定管理
  - .env（プロジェクトルート）や OS 環境変数から設定を自動ロード
  - 自動ロードの無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要環境 / 依存

（実際の pyproject.toml / requirements.txt がないため、典型的な依存を列挙します）
- Python 3.10+
- duckdb
- openai (OpenAI SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

インストール方法（例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# パッケージを開発インストールする場合（プロジェクトルートに pyproject.toml がある想定）
pip install -e .
```

---

## 環境変数（主なもの）

config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

自動 .env ロードについて:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` / `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例 .env（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順

1. Python と仮想環境を用意
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # もし提供されていれば:
   pip install -e .
   ```

3. 環境変数を設定 (.env をプロジェクトルートに置く)
   - 上記の必須キー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を必ず設定してください。

4. データディレクトリの作成（必要な場合）
   ```bash
   mkdir -p data
   ```

5. 監査DB を初期化（オプション）
   Python から：
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn: duckdb.DuckDBPyConnection
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（DuckDB 接続を渡す）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別スコア付与）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"書込み銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（例：モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), "銘柄のモメンタムを計算しました")
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- RSS ニュース取得（news_collector の低レベル関数）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  print(len(articles))
  ```

注意点：
- OpenAI 呼び出しはモデル gpt-4o-mini を使用（news_nlp / regime_detector）。API 制限・料金に注意してください。
- J-Quants API 呼び出しではレート制限とリトライを実装していますが、実運用ではトークン管理とスケジューリングに注意してください。
- ETL / リサーチ関数はルックアヘッドバイアスを避ける設計になっています。バックテスト等で使用する場合は設計方針に注意して利用してください。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュールツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - calendar_management.py       — マーケットカレンダーの管理
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログテーブル初期化
    - news_collector.py            — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py           — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py       — 将来リターン/IC/統計サマリー

（その他、strategy / execution / monitoring 等のパッケージファサードが想定されていますが、今回のコードベースでは上記が中心です。）

---

## 設計上の注意・ベストプラクティス

- 環境（KABUSYS_ENV）が `live` の場合は本番の注文やトレード連携に注意すること（テストは paper_trading を推奨）。
- OpenAI の呼び出しはアカウントごとのレート・課金が発生します。ローカルテストでは環境変数でキーを差し替える、あるいはモックを使ってテストしてください（コード内でもテスト用に _call_openai_api を差し替えることが想定されています）。
- DuckDB のスキーマや初期化は、データを保持する前にスキーマ作成処理を行ってください（audit.init_audit_db のようなユーティリティを利用）。

---

もし README に追記してほしい点（例：実行スクリプト、テスト方法、CI 設定、具体的な SQL スキーマ定義の抜粋など）があれば教えてください。必要に応じてサンプル .env.example も作成します。