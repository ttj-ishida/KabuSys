# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants からの市場データ取得、DuckDB ベースのデータレイク、研究用ファクター計算、特徴量生成、シグナル生成、ニュース収集などの機能を備え、戦略開発と本番運用の中間層を提供します。

主な設計方針
- ルックアヘッドバイアス排除（target_date 時点のみ参照）
- DuckDB を使ったローカルデータベース（冪等な保存）
- 外部 API 呼び出しは明確に分離（データ層・戦略層・実行層）
- 冪等性・トランザクション・エラーハンドリング重視

バージョン: 0.1.0

---

## 機能一覧

- data
  - J-Quants API クライアント（認証、ページネーション、レート制御、リトライ）
  - ETL パイプライン（日次差分更新・バックフィル・品質チェック）
  - DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ニュース収集（RSS -> raw_news、記事正規化、銘柄抽出、SSRF 対策）
  - カレンダー管理（JPX カレンダー取得、営業日判定、next/prev_trading_day 等）
  - 汎用統計ユーティリティ（Z スコア正規化）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
- strategy
  - 特徴量生成（research で算出した raw factor の正規化・フィルタリング -> features テーブル）
  - シグナル生成（features と ai_scores を統合し final_score 計算、BUY/SELL 判定 -> signals テーブル）
- execution（パッケージは用意済み、発注ロジックは層として想定）
- monitoring（監視用インターフェース想定）

主要な設計仕様はソース内のドキュメントコメント（StrategyModel.md / DataPlatform.md 等）に準拠しています。

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法などを使用しているため）
- Git（推奨）
- ネットワーク環境（J-Quants API 等へのアクセス）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - 必須パッケージ（代表例）
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （実際の requirements.txt がある場合はそちらを使用してください:
    pip install -r requirements.txt）

4. パッケージを編集可能インストール（任意）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる環境変数（コード上で要求されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他オプション / 設定例
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で自動 .env ロードを無効化
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL（kabuステーション API のベース URL。デフォルト "http://localhost:18080/kabusapi"）

例 .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

以下は Python REPL / スクリプト例です。各関数はモジュールから直接呼び出せます。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブルを作る
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日の処理
print(result.to_dict())
```

3) 特徴量構築（research で計算された raw factor を正規化して features テーブルへ保存）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date(2026, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成（features / ai_scores / positions を参照して signals に書き込む）
```python
from kabusys.strategy import generate_signals
from datetime import date

total = generate_signals(conn, date(2026, 1, 31))
print(f"signals generated: {total}")
```

5) ニュース収集ジョブ（RSS -> raw_news -> news_symbols）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄セットを用意
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意点
- ETL / API 呼び出しはネットワーク・API レートを使用します。J-Quants トークンは設定必須です。
- run_daily_etl の内部で品質チェックが実行され、issues が ETLResult に格納されます。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 配下に配置されています。主要ファイルと目的を示します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・取得・保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - schema.py
      - DuckDB スキーマ作成 / init_schema
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - news_collector.py
      - RSS 取得・前処理・DB 保存・銘柄抽出
    - calendar_management.py
      - カレンダー取得 / 営業日判定 / next/prev_trading_day 等
    - audit.py
      - 監査ログ用テーブル定義（発注・約定トレース）
    - features.py
      - data.stats の公開ラッパ
    - pipeline.py
      - ETL orchestration
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL シグナル生成、signals テーブル書き込み
  - execution/
    - __init__.py
    - （発注周りの実装想定）
  - monitoring/
    - （監視・通知周りの実装想定）

---

## 運用・開発上のポイント

- 環境管理
  - .env / .env.local をプロジェクトルートに置くことで起動時に自動読み込みされます（ただしテスト等で無効化可能）。
- スキーマ初期化は init_schema() を使用してください。既存テーブルはスキップされるため安全です。
- ルックアヘッドバイアス防止のため、戦略系関数は target_date を明示してその日の時点データのみを参照します。
- ロギングは LOG_LEVEL と KABUSYS_ENV に従います。運用環境では KABUSYS_ENV=live を設定してください。
- ニュース収集では SSRF 対策・XML サニタイズ・サイズ制限などを施していますが、外部ソースの取り扱いは注意してください。

---

## 貢献 / 拡張

- execution 層（証券会社ブリッジ / 冪等な発注ロジック）、monitoring（Slack 通知等）などは今後の拡張ポイントです。
- 新しい RSS ソースを追加する場合は data.news_collector.DEFAULT_RSS_SOURCES に追記してください。
- ファクターや特徴量の追加は research/*.py と strategy/feature_engineering.py を拡張してください。

---

何か追記してほしい点（例: 実運用時のデプロイ手順、具体的な SQL スキーマの説明、CI テストの書き方など）があれば教えてください。README を用途に合わせて拡張します。