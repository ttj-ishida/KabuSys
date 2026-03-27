# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、売買アルゴリズム開発と運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 特長（機能一覧）

- データ取得（J-Quants API）と DuckDB 保存（差分取得・ページネーション・冪等保存）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
- ETL パイプライン（run_daily_etl）による日次データ更新と品質チェック
- ニュース収集/前処理（RSS）とニュース NLP（OpenAI を用いたセンチメントスコア付与）
  - ニュースウィンドウの定義、銘柄別集約、バッチ API 呼び出し、レスポンス検証
- 市場レジーム判定（ETF 1321 の MA とマクロニュース LLM センチメントの合成）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）のスキーマ初期化ユーティリティ
- 環境変数ベースの設定管理（.env 自動読み込み、.env.local による上書き対応）

設計上の配慮:
- Look-ahead バイアスを防ぐ設計（内部で datetime.today() を直接参照しない等）
- API 呼び出しはリトライ・バックオフやフェイルセーフを実装
- DuckDB を中心に SQL/ウィンドウ関数で効率的に集計・処理

---

## 必要条件（依存）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants, OpenAI, RSS フィード など）

（実際の依存はプロジェクトの requirements.txt / pyproject.toml を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウトし、パッケージをインストール
   - 開発時（editable）:
     - pip install -e .
   - または通常インストール:
     - pip install .

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

3. 環境変数の準備
   - プロジェクトルートに `.env` を作成します（自動読み込みあり）。
   - `.env.local` を作れば `.env` を上書きします（OS 環境変数が優先されます）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等の API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に渡す代わりに設定可能）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視用 SQLite パス（デフォルト data/monitoring.db）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（クイックスタート）

以下はライブラリの主要機能を呼び出すためのサンプルコード例です。実行環境で Python スクリプトやジョブとして利用してください。

共通準備:
```python
import duckdb
from kabusys.config import settings

# DuckDB 接続（ファイルまたは :memory:）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると today が使われます（内部で営業日に調整あり）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース NLP スコアリング（AI を使った銘柄別スコア算出）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーは OPENAI_API_KEY 環境変数 か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Wrote scores for {n_written} codes")
```

3) 市場レジーム判定（ETF 1321 MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ書き込まれます
```

4) 監査ログ（audit）スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

# 監査専用 DB を作成して接続を返す
audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

5) ETL で使用する J-Quants クライアントを直接使う例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を参照して id_token を取得
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
# 取得した records を save_daily_quotes などで保存可能
```

6) RSS を取得する（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# articles は NewsArticle のリスト。データベース保存はプロジェクト側で行ってください。
```

注意点:
- score_news / score_regime は OpenAI API を呼びます。API キーは引数 api_key に渡すか環境変数 OPENAI_API_KEY を設定してください。
- 各処理はルックアヘッドバイアス防止のため、内部で target_date 未満のデータのみ参照する等の配慮がされています。
- ETL / API 呼び出しはリトライやフェイルセーフを持ちますが、API 利用料やレート制限には注意してください。

---

## 設計上の重要な挙動・運用ノート

- 環境変数の自動読み込み
  - プロジェクトルート（__file__ の親を上って .git もしくは pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

- OpenAI 呼び出し
  - gpt-4o-mini（設定によりモデル名は定数で管理）を Chat Completions（JSON Mode）で利用します。
  - API 失敗時はリトライ・バックオフし、それでも失敗した場合は安全側のデフォルト（例: macro_sentiment=0.0）で処理を継続します。

- J-Quants API
  - rate-limit（120 req/min）を固定間隔スロットリングで遵守します。
  - 401 を受けた場合はリフレッシュして 1 回だけ再試行します。
  - 取得データは fetched_at に UTC タイムスタンプを付与して保存します（Look-ahead 記録）。

- DuckDB との相互作用
  - 保存処理は ON CONFLICT DO UPDATE などで冪等化しています。
  - 一部の executemany は DuckDB バージョン依存の挙動（空リスト不可等）を考慮しています。

---

## ディレクトリ構成

以下はコードベースの主要なパッケージ構成（src/kabusys）です。実際のファイルはプロジェクトルートの src/kabusys 以下にあります。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュース NLP スコアリング
    - regime_detector.py             -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & 保存
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult 再エクスポート
    - news_collector.py              -- RSS 収集 / 前処理
    - calendar_management.py         -- 市場カレンダー管理（営業日判定等）
    - stats.py                       -- 統計ユーティリティ（zscore_normalize 等）
    - quality.py                     -- データ品質チェック
    - audit.py                       -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム / ボラティリティ / バリュー
    - feature_exploration.py         -- 将来リターン / IC / 統計サマリー
  - (その他)                          -- strategy, execution, monitoring 等のプレースホルダを示唆する __all__ あり

各モジュールは責務が明確に分離されており、ETL・データ管理・AI スコアリング・リサーチ機能を分離して利用できます。

---

## よくある質問 / トラブルシューティング

- Q: 環境変数が読み込まれない
  - A: デフォルトでプロジェクトルートの .env / .env.local を自動読み込みします。CI 等で手動で環境変数を渡す場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化してください。

- Q: OpenAI のレスポンスが不正（JSON パースエラー）
  - A: LLM レスポンスは厳密な JSON を期待しますが、万が一パースに失敗すると該当チャンクはスキップして安全側のデフォルトで継続します。必要に応じてリトライやプロンプトの調整を検討してください。

- Q: DuckDB に既存スキーマがない / テーブルがない
  - A: ETL 初回実行前にスキーマ定義（DDL）を適用する処理が別途必要です。監査用スキーマは kabusys.data.audit.init_audit_db / init_audit_schema で作成できます。

---

## 貢献 / 開発

- コードはモジュールごとに単体テストを追加することを推奨します。API 呼び出し部分はモック化しやすい設計（呼び出しラッパー等）になっています。
- セキュリティ: RSS の取得は SSRF 対策、XML のパースは defusedxml を使用し安全性に配慮しています。
- ライセンスや CI/CD の設定はプロジェクトルートのファイルを参照してください（ここには含まれていません）。

---

README に書かれている利用法は主要なユースケースをカバーするための導入ガイドです。具体的な運用や追加設定（Slack 通知、kabu API 発注処理、戦略実行フローなど）はプロジェクトの上位レイヤーで実装してください。必要であれば使い方のサンプルスクリプトや運用手順のテンプレートも作成します。希望があれば教えてください。