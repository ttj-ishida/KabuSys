# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
J-Quants からのデータ取得、DuckDB ベースの ETL、ニュース収集・NLP（OpenAI）によるスコアリング、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを提供します。

## プロジェクト概要
- パッケージ名: kabusys
- 目的: J-Quants 等から市場データを収集・保管し、ニュースセンチメントや市場レジーム判定、ファクター計算、ETL・データ品質チェック、発注監査ログなど自動売買システムに必要な基盤機能を提供する。
- 主要技術: Python、DuckDB、OpenAI（gpt-4o-mini）、標準ライブラリ中心

## 主な機能一覧
- 設定管理
  - .env ファイル／環境変数からの自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須環境変数の検証（settings オブジェクト）

- データ取得・ETL（kabusys.data）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - 日次 ETL パイプライン（株価、財務、カレンダー）
  - 市場カレンダー管理（営業日判定、next/prev 営業日など）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS → raw_news、SSRF / XML 攻撃対策・トラッキング除去）
  - 監査ログ初期化（監査テーブル・インデックス、監査 DB 初期化ユーティリティ）

- AI（kabusys.ai）
  - ニュースセンチメント解析（score_news: gpt-4o-mini で銘柄ごとにスコア）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースを組み合わせて bull/neutral/bear を判定）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（情報係数）や統計サマリー
  - Zスコア正規化ユーティリティ（kabusys.data.stats）

- その他
  - 監査・トレーサビリティ（signal_events / order_requests / executions の DDL と初期化）
  - DuckDB に対する冪等保存ロジック（ON CONFLICT DO UPDATE 等）

## セットアップ手順

前提: Python 3.10+（コード内で型ヒント等に Python 3.10 以上を想定）およびインターネット接続

1. リポジトリを取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がない場合、主な依存を手動でインストール:
     ```
     pip install duckdb openai defusedxml
     ```
   - プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください（例: pip install -e . など）。

4. 環境変数／.env の準備
   - プロジェクトルート（.git または pyproject.toml をルート検出に使用）に .env を作成できます。
   - 自動ロードはデフォルトで有効。テストなどで無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   推奨される最小 .env（実運用では各値を安全に管理してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   KABUSYS_ENV=development  # または paper_trading / live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリの作成（必要に応じて）
   - デフォルトの DuckDB ファイルパスは data/kabusys.duckdb
   - 監視用 SQLite は data/monitoring.db（設定で変更可）
   - 例:
     ```
     mkdir -p data
     ```

## 使い方（サンプル）

以下は Python REPL / スクリプトからの簡単な利用例です。

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.env, settings.log_level)
```

- DuckDB 接続を作って ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニューススコア生成（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- RSS の取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

- J-Quants の ID トークン取得（内部で settings.jquants_refresh_token を参照）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
print(token)
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を使用する前提。API レスポンスの JSON モードを使って厳密な JSON を期待しているため、API レスポンスが不正な場合は該当処理はフェイルセーフでスキップまたはデフォルト値（例: macro_sentiment=0）で継続します。
- ETL / スコアリング処理はいずれもルックアヘッドバイアス対策（target_date 未満 / target_date を参照しない設計）に配慮されています。

## 環境変数一覧（主なもの）
- 必須（必ず設定が必要）
  - JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン
  - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（Slack 連携を使う場合）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携をする場合）

- 推奨／任意
  - OPENAI_API_KEY: OpenAI API キー（AI スコアリング実行時に必要）
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルトは development
  - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）デフォルト INFO
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: SQLite ファイルパス（監視など、デフォルト data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する（1 を設定）

## ディレクトリ構成（主要ファイル）
リポジトリの主要部分は src/kabusys 配下にあります。簡易ツリー:

```
src/kabusys/
├─ __init__.py
├─ config.py                    # 環境変数 / .env 自動読み込み
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py               # ニュースセンチメントスコアリング
│  └─ regime_detector.py        # 市場レジーム判定
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py         # J-Quants API クライアント & DuckDB 保存
│  ├─ pipeline.py               # ETL パイプライン (run_daily_etl 等)
│  ├─ etl.py                    # ETLResult 再エクスポート
│  ├─ news_collector.py         # RSS フィード収集
│  ├─ calendar_management.py    # 市場カレンダー管理
│  ├─ quality.py                # データ品質チェック
│  ├─ stats.py                  # zscore 正規化等
│  ├─ audit.py                  # 監査ログ DDL / 初期化
│  └─ ...                       # その他データ関連モジュール
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py        # モメンタム/バリュー/ボラティリティ計算
│  └─ feature_exploration.py    # 将来リターン / IC / サマリー
└─ ...
```

モジュールの役割:
- kabusys.config: .env 読み込み、settings を通じたアプリ設定取得
- kabusys.data.jquants_client: API 呼び出し・レート制御・DuckDB への保存
- kabusys.data.pipeline: ETL の高レベルワークフロー（run_daily_etl）
- kabusys.data.news_collector: RSS の安全な取り込み・正規化
- kabusys.ai: OpenAI を使った NLP / レジーム判定
- kabusys.research: バックテスト・リサーチ用のファクター計算・解析ユーティリティ

## 運用上の注意点
- 本ライブラリには実際の発注機能やライブ取引向けコード（kabu API 連携等）が含まれる想定の部分があります。live 環境で実行する際は事前に安全確認・テストを十分に行ってください。
- 秘密情報（API トークン等）は .env に平文で置く場合は適切に保護し、CI/CD や本番環境ではシークレットマネージャ等の利用を推奨します。
- OpenAI / J-Quants の API 利用にはそれぞれの利用規約や料金が発生します。キーやコール頻度には注意してください。

---

README に記載のない細かい使い方や追加のユーティリティ関数については、各モジュール（src/kabusys 以下）のドキュメント文字列を参照してください。質問や追加の README 改訂希望があれば教えてください。