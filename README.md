# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集と NLP スコアリング・市場レジーム判定・ファクター計算・監査ログなど、取引システム/リサーチ環境で必要となる主要機能を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（簡易例）
- 環境変数（主な設定）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は、日本株の自動売買／リサーチ基盤用に設計された Python ライブラリ群です。  
主に以下用途を想定しています。

- J-Quants API からのデータ ETL（株価日足、財務データ、JPX カレンダー等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と NLP による銘柄別センチメントスコア作成（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査（信号→発注→約定）用の監査テーブル初期化・管理
- DuckDB を用いたローカルデータストアとの統合

設計方針の一部:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- API 呼び出しに対するリトライ・レート制御・フォールバックを実装
- 冪等性（DB 書き込みは ON CONFLICT などで重複を抑制）
- 外部 API キーは明示的に渡すか環境変数で管理

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルート検出）と必須変数検査
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants から日次株価・財務・上場情報・カレンダーを差分取得・保存
  - DuckDB との統合、ページネーション・トークン自動更新、レート制御
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合検査
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・前後営業日の取得・夜間バッチでのカレンダー更新
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、SSRF 対策、raw_news への冪等保存支援
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア化（ai_scores テーブルへ）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200 日 MA 乖離 + マクロニュース LLM スコアで日次レジーム決定
- リサーチ（kabusys.research）
  - Momentum / Value / Volatility 等のファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions 等テーブル DDL とインデックスを作成
- 監視・通知連携（Slack 用トークン読み込み等の設定サポート）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の union などを使用）
- DuckDB を利用するための native 環境（pip インストールで利用可能）

1. リポジトリをクローン
   - git clone ... / 任意の方法でソースを取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）
   - 開発時: pip install -e . で editable install（パッケージ化されていれば）

4. 環境変数設定
   - プロジェクトルートに .env を置くと自動読み込みされます（.env.local は .env を上書き）
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数は次節参照。まずは必須変数を .env に設定してください。

5. データベース初期化（監査ログ等）
   - 監査ログ用 DB 初期化例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")

6. （オプション）J-Quants / OpenAI / Slack の API キーを設定

---

## 環境変数（主要なもの）

必須（利用機能により必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 実行に必須）
- SLACK_BOT_TOKEN: Slack 通知を使う場合
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携時）
- OPENAI_API_KEY: OpenAI API を使う場合（news_nlp / regime_detector）。関数呼び出し時に api_key 引数で渡すことも可能。

任意
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読み込みを無効化

.env の読み込みルール:
- プロジェクトルート（.git または pyproject.toml を基準）から .env を自動探索
- 読み込み順: OS 環境 > .env.local > .env
- export KEY=val 形式に対応、クォートやコメントのパースを実装

---

## 使い方（短い例）

以下は最小限のコード例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) OpenAI を使ってニューススコアを生成（news_nlp）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を渡すか環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

3) 市場レジームを判定して保存（regime_detector）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査 DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/kabusys_audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

5) ニュース収集（RSS）を取得して raw_news に保存するワークフローは
   - kabusys.data.news_collector.fetch_rss を利用して記事リストを作成し、
   - 保存はプロジェクト内の ETL / 保存ロジックに合わせて実装してください（fetch_rss は記事辞書のリストを返します）。

---

## ディレクトリ構成

主要なファイル / モジュール（src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py         -- ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py  -- ETF MA とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   -- J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
  - etl.py              -- ETLResult の再エクスポート
  - calendar_management.py -- マーケットカレンダー管理（営業日判定 etc.）
  - news_collector.py   -- RSS 収集（SSRF 対策・XML 安全パース）
  - quality.py          -- データ品質チェック
  - stats.py            -- 汎用統計ユーティリティ（zscore_normalize）
  - audit.py            -- 監査ログ DDL / 初期化
- research/
  - __init__.py
  - factor_research.py  -- Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py -- 将来リターン計算、IC、統計サマリー

（上記以外に strategy / execution / monitoring などのサブパッケージが __all__ に含まれる可能性がありますが、本コードベース抜粋では全内容を列挙しています）

---

## 注意事項 / 実装上のポイント

- OpenAI 呼び出しは外部ネットワーク依存のため、テスト時は関数をモックしてください（各モジュールで _call_openai_api を差し替え可能）。
- J-Quants API へのリクエストはレート制御（120 req/min）とリトライロジックを実装しています。トークンは自動更新されます。
- ETL は差分取得＋backfill を行い、品質チェックは Fail-Fast にせず問題を収集する設計です。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックが行われています。
- news_collector は SSRF・XML Bomb・巨大レスポンス等に対する防御を実装しています（defusedxml、受信サイズ制限、リダイレクト検査など）。
- 環境変数の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）を行います。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を指定してください。

---

README はここまでです。  
さらに具体的な利用例（例: バッチ cron / Airflow 連携、監査ログを用いた発注フロー例など）や API ドキュメント、テスト手順を追加したい場合は、その用途に合わせてセクションを拡張できます。必要があればサンプル .env.example やスクリプト例も作成します。