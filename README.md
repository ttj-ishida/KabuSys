# KabuSys

KabuSys は日本株の自動売買システム構築を目的とした Python パッケージです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ等のモジュール群を含み、戦略研究環境と運用環境の両方を想定して設計されています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単な例）
- 環境変数（.env）
- ディレクトリ構成
- よくある質問 / トラブルシュート

---

## プロジェクト概要

KabuSys は以下を主目的とします。
- J-Quants API を用いた市場データ・財務データ・マーケットカレンダーの取得
- DuckDB を用いたデータの永続化とスキーマ管理
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- ファクター正規化・合成による特徴量生成（features テーブル）
- AI スコア等と統合した売買シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- 監査ログ（signal → order → execution のトレース）用スキーマ

設計上のポイント:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ参照）
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）で実装
- 外部 API 呼び出しは jquants_client に集中、リトライ・レート制御を実装
- DuckDB を主体にローカルで高速に分析・運用可能

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings オブジェクト）

- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動更新）
  - schema: DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - pipeline: 日次 ETL（市場カレンダー、株価、財務）および差分更新ロジック
  - news_collector: RSS フィード収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・次/前営業日・カレンダー更新ジョブ
  - stats: zscore_normalize 等の汎用統計ユーティリティ
  - features: research 用関数の再公開インターフェース

- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算 / IC（Spearman） / 統計サマリー

- kabusys.strategy
  - feature_engineering.build_features: 生ファクターから features テーブルを作成
  - signal_generator.generate_signals: features / ai_scores / positions を統合して BUY/SELL シグナルを生成

- kabusys.data.audit
  - 発注〜約定までの監査ログ用スキーマ（order_requests / executions / signal_events 等）

補助:
- news のテキスト前処理、URL 正規化、SSRF 対策、gzip / サイズ制限 等の堅牢な実装

---

## セットアップ手順

前提:
- Python 3.10 以上（型注釈の union operator (|) を使用しているため）
- DuckDB を利用するための環境（ファイルシステム書き込み権限）

簡単な手順:

1. リポジトリをクローンして移動（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要なパッケージをインストール
   - 最低限の依存:
     - duckdb
     - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

4. パッケージのインストール（開発時）
   ```
   pip install -e .
   ```
   （setup/pyproject が整備されている場合）

5. 環境変数設定
   - プロジェクトルートの `.env`（または `.env.local`）に必要な変数を設定します（下記参照）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

6. DuckDB スキーマ初期化（例）
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（簡単な例）

1) 設定値の取得
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

2) DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

3) 日次 ETL 実行（市場カレンダー・株価・財務を取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

4) 特徴量生成（features テーブルの構築）
```python
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

5) シグナル生成
```python
from kabusys.strategy import generate_signals
n = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {n}")
```

6) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効な銘柄コードセットを渡すと銘柄紐付けを行う
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

上記はあくまでモジュール API の利用例です。実運用ではジョブスケジューラ（cron / Airflow 等）で ETL → features → signals → execution を連携してください。

---

## 環境変数（.env の例）

自動ロードされる環境変数（必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意（デフォルトあり）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

.env のサンプル:
```
# .env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

補足:
- .env.local は .env を上書きする（優先度高）
- OS 環境変数は最も優先される
- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル / モジュール（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch / save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - schema.py                    — DuckDB スキーマ定義・init_schema
    - news_collector.py            — RSS 収集・保存・銘柄抽出
    - calendar_management.py       — カレンダー管理・営業日ユーティリティ
    - features.py                  — features 用再公開
    - stats.py                     — zscore_normalize 等
    - audit.py                     — 監査ログスキーマ（signal_events 等）
  - research/
    - __init__.py
    - factor_research.py           — momentum/volatility/value 計算
    - feature_exploration.py       — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features
    - signal_generator.py          — generate_signals
  - execution/                      — 発注 / ブローカー連携層（空ファイル含む）
  - monitoring/                     — 監視関連（空フォルダ等）

（上記は主要ファイルの抜粋です。リポジトリ全体に README や tests、CI 設定等が含まれる場合があります。）

---

## よくある質問 / トラブルシュート

- Q: Python バージョンエラーが出る
  - A: Python 3.10 以上を使用してください（型注釈で | が使用されています）。

- Q: .env がロードされない / 設定が反映されない
  - A: .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。優先順位は OS 環境 > .env.local > .env です。

- Q: DuckDB テーブルが作成されない
  - A: init_schema で接続パス指定（相対/絶対）を確認してください。親ディレクトリが存在しない場合は init_schema が作成します。権限やパスの誤りに注意。

- Q: J-Quants API の 401 が出る
  - A: jquants_client は 401 受信時にリフレッシュトークンから id token を再取得して 1 回リトライします。refresh token（JQUANTS_REFRESH_TOKEN）が正しいか確認してください。

- Q: RSS 取得でエラーが出る（SSRF/リダイレクト拒否）
  - A: news_collector はリダイレクト先やホストがプライベートアドレスかどうかを厳密に検証します。社内の非公開 RSS を取得したい場合は事前にホストの許可設定を検討してください。

---

必要に応じて README を拡張して、CI 設定、デプロイ手順、テスト実行方法（pytest 等）、監視・アラート設計、バックテスト手順などを追加できます。追加したい項目があれば教えてください。