# KabuSys

日本株向け自動売買基盤ライブラリ (KabuSys) の README。

このリポジトリは、データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、監査・スキーマ管理等を含む日本株自動売買プラットフォームのコアモジュール群を提供します。

- 対象: 研究環境（バックテスト / ファクタ探索）から実運用（ETL → 特徴量 → シグナル → 発注監査）までの一貫したワークフローを補助
- 言語: Python（タイプヒントに | を使用しているため Python 3.10 以降を推奨）

---

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されます。

- data: J-Quants API クライアント、RSS ニュース収集、ETL パイプライン、DuckDB スキーマ管理、統計ユーティリティ、カレンダー管理、監査ログ
- research: 研究用途のファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー、IC 計算等）
- strategy: 特徴量正規化（feature_engineering）とシグナル生成（signal_generator）
- execution / monitoring: 発注・モニタリング関連（骨格）

設計上の主な方針:
- DuckDB を内部データベースとして利用し、冪等な保存処理とトランザクション単位の置換を行う
- ルックアヘッドバイアス対策として、常に target_date 時点で利用可能なデータのみを使用
- 外部通信にはレート制御・リトライ・トークン自動更新などの堅牢性を備える
- RSS ニュース収集では SSRF / XML Bomb 等の対策を実装

---

## 機能一覧

主な機能（モジュール別）:

- kabusys.config
  - .env / .env.local からの自動環境変数読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパー（settings オブジェクト）

- kabusys.data.jquants_client
  - J-Quants API クライアント（ID トークン自動リフレッシュ、固定間隔レートリミット、リトライ）
  - データ取得: 日足（daily_quotes）、財務（statements）、マーケットカレンダー
  - DuckDB への保存ユーティリティ（冪等 save_* 関数）

- kabusys.data.pipeline
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェックとの連携（quality モジュール呼び出し）

- kabusys.data.schema
  - DuckDB のスキーマ初期化（init_schema）
  - テーブル群: raw / processed / feature / execution / audit など

- kabusys.data.news_collector
  - RSS フィード収集（fetch_rss）、記事正規化、raw_news への保存、銘柄抽出・紐付け
  - SSRF / レスポンスサイズ / XML の安全対策実装

- kabusys.data.calendar_management
  - market_calendar の管理、営業日判定、次/前営業日の取得、カレンダー更新ジョブ

- kabusys.data.stats
  - zscore_normalize（クロスセクション Z スコア正規化）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（ファクター探索用ユーティリティ）

- kabusys.strategy
  - build_features（raw ファクターを正規化して features テーブルへ保存）
  - generate_signals（features と ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存）

- kabusys.data.audit
  - 監査ログ用テーブル群（signal_events, order_requests, executions 等）定義

---

## セットアップ手順

前提
- Python 3.10 以上
- DuckDB を利用するためネイティブ拡張が必要。pip で duckdb をインストールします。

1. リポジトリをクローン
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール
   最低限の依存:
   - duckdb
   - defusedxml
   （プロジェクト配布に pyproject.toml / requirements.txt があればそれを使用してください）

   例:
   ```
   pip install duckdb defusedxml
   ```

   開発中はこのリポジトリを editable install することを想定:
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.cfg 等がある場合）

4. 環境変数の設定
   プロジェクトルートに `.env` として必要な環境変数を配置できます。自動で `.env` → `.env.local` の順に読み込まれます（OS 環境変数が優先）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（Settings が require しているもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 関連で使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要な場合）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必要な場合）
   任意 / デフォルトを持つ:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本的なワークフロー）

以下はライブラリを Python から利用する基本例です。用途に合わせてスクリプト化して cron やジョブスケジューラで回すことを想定しています。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数から取得される
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（市場カレンダー・株価・財務の差分取得と保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を明示することも可能
print(result.to_dict())
```

3) 特徴量計算（features テーブルの構築）
```python
from datetime import date
from kabusys.strategy import build_features

target = date(2024, 1, 31)
n = build_features(conn, target)
print(f"built features: {n}")
```

4) シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals

target = date(2024, 1, 31)
count = generate_signals(conn, target)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 既知銘柄セットを与えると抽出・紐付けする
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- run_daily_etl 等は内部で例外を捕捉して処理を継続する設計ですが、エラー詳細は ETLResult の errors に格納されます。必ずログと戻り値を確認してください。
- J-Quants API はレート制限があり、jquants_client モジュールは固定間隔スロットリングとリトライを実装しています。長時間・大規模取得時は配慮してください。

---

## 環境変数の振る舞い

- 自動ロード: パッケージの config モジュールは .git または pyproject.toml を基準にプロジェクトルートを探索し、ルートにある `.env`（優先度低）および `.env.local`（優先度高）を読み込みます。OS 環境変数が優先されます。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成

主要なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py           # RSS 収集・前処理・DB保存
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
    - stats.py                    # zscore_normalize 等統計ユーティリティ
    - features.py                 # features の公開インタフェース（再エクスポート）
    - calendar_management.py      # market_calendar 管理・営業日判定
    - audit.py                    # 監査ログ（signal_events, order_requests, executions）
    - ...
  - research/
    - __init__.py
    - factor_research.py          # モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py      # forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py      # raw factor -> features 生成
    - signal_generator.py         # final_score 計算 & BUY/SELL 判定
  - execution/                    # 発注関連モジュール（骨格）
  - monitoring/                   # 監視用モジュール（骨格）

ドキュメント参照:
- ソース内に StrategyModel.md / DataPlatform.md / DataSchema.md 等の設計メモに準拠する旨の注記があり、実運用時はそれらのドキュメント（もし別ファイルで存在するなら）を参照してください。

---

## 開発・運用上の注意点 / トラブルシュート

- DuckDB ファイルの権限やパス: デフォルトは data/kabusys.duckdb。ディレクトリが存在しない場合、schema.init_schema() が自動作成しますが、運用サーバでのパスは事前に確認してください。
- J-Quants トークン: get_id_token は refresh token を使って idToken を取得します。トークンが無効、あるいは API のレスポンスが 401 の場合は自動リフレッシュを試みますが、環境変数が正しいか確認してください。
- レート制限: jquants_client は 120 req/min を前提に間隔調整を行います。短時間で大量の銘柄を取得するスクリプトを走らせると遅延します。
- ニュース収集: 外部 RSS を取得するためネットワーク・プロキシ設定や SSRF 対策の影響を受けます。内部ネットワークへアクセスするフィードはブロックされます。
- ログ: LOG_LEVEL を設定して詳細なログを出力してください。問題解析のために logger 出力を確認すること。

---

## ライセンス / 貢献

本リポジトリのライセンス情報やコントリビュート方法は本 README に含まれていないため、リポジトリのトップレベルファイル（LICENSE、CONTRIBUTING 等）を確認してください。

---

README に記載のコード例は、ライブラリの主要な API を示すサンプルです。詳細な設定や運用フロー（スケジューリング、Slack 通知、実行層のブローカー連携）は別途実装・テストしてください。必要なら利用例や追加ドキュメント（運用ガイド、設計ドキュメント要約）を作成します。