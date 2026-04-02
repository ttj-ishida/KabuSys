# KabuSys

バージョン: 0.1.0

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買支援ライブラリです。J-Quants API からの ETL、ニュース収集・NLP によるセンチメント評価、ファクター計算・リサーチユーティリティ、監査ログ（トレーサビリティ）、および市場レジーム判定などを提供します。バックテストや運用パイプラインの基盤として利用できるよう設計されています。

主な設計方針の特徴
- Look-ahead bias を避ける設計（内部で date.today() を参照しないAPIが多い）
- DuckDB を用いたローカルデータ保存（冪等な保存ロジック）
- OpenAI / J-Quants など外部 API に対する堅牢なリトライ・レート制御
- SSRF・XML攻撃などセキュリティ考慮（news_collector）
- 部分失敗に強い ETL / 品質チェック / 監査ログ

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（jquants_client, data.pipeline）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合チェック
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日の取得、カレンダー夜間更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策・受信サイズ制限・XML 安全パーサ使用
- ニュース NLP / AI（ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア算出（ai_scores へ保存）
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次の市場レジーム判定
- 研究用ユーティリティ（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン計算、IC 計算、Z スコア正規化
- 監査ログ（data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義・初期化ユーティリティ
- その他ユーティリティ
  - 設定管理（config.Settings）：.env / 環境変数読み込み、各種パス・閾値取得

---

## セットアップ手順

前提
- Python 3.10 以上（タイプヒントで PEP 604 の union 型（|）を使用）
- 仮想環境の利用を推奨

例（UNIX 系）:

1. 仮想環境作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージのインストール（最低限）
   - 必要な主要ライブラリ:
     - duckdb
     - openai
     - defusedxml
   - 簡易インストール例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 開発用にパッケージを editable インストールする場合（プロジェクトのルートに setup.cfg / pyproject.toml がある想定）:
   ```bash
   pip install -e .
   ```

3. 環境変数 / .env ファイル
   - プロジェクトルート（.git もしくは pyproject.toml が存在するディレクトリ）に置いた `.env` / `.env.local` を自動読み込みします（config モジュールが起動時に読み込み）。
   - 自動読み込みを無効化したい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      : kabu ステーション API のパスワード（発注系で使用）
     - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID       : Slack チャンネル ID
   - 任意 / デフォルトあり
     - OPENAI_API_KEY         : OpenAI の API キー（ai.* の関数は引数で渡せる）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              : DEBUG/INFO/…（デフォルト INFO）

4. データベース初期化（監査ログ等）
   - 監査ログ専用 DB 初期化例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は duckdb.DuckDBPyConnection
   ```

---

## 使い方（主な API と実行例）

以下は最小限の利用例です。実運用ではエラーハンドリングやログ設定、スケジューリングを追加してください。

設定読み込み・DuckDB 接続作成例
```python
from kabusys.config import settings
import duckdb

db_path = str(settings.duckdb_path)  # Path オブジェクトを文字列化して渡す
conn = duckdb.connect(db_path)
```

日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメント（銘柄スコア）生成
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OpenAI API キーを引数で渡すことも可能
written = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxx")
print(f"書き込んだ銘柄数: {written}")
```

市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxx")
```

RSS フィード取得（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

J-Quants クライアントの直接利用例
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
from kabusys.config import settings
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を使用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

factors = calc_momentum(conn, target_date=date(2026,3,20))
```

注意点
- OpenAI 呼び出しはネットワークエラーやレート制限に対してリトライロジックを備えていますが、APIキーは安全に管理してください。
- ETL / 書き込みは冪等性を考慮して実装されているため再実行可能です。

---

## ディレクトリ構成（主要ファイルの説明）

（プロジェクトルート）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数/.env の自動読み込みと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          : ニュースを集約して OpenAI で銘柄別センチメントを算出し ai_scores に書き込む
    - regime_detector.py   : ETF 1321 の MA200 とマクロセンチメントを合成して market_regime を算出
  - data/
    - __init__.py
    - pipeline.py          : ETL パイプライン（run_daily_etl など）
    - jquants_client.py    : J-Quants API クライアント（fetch/save の実装）
    - news_collector.py    : RSS 取得と前処理（SSRF、XML 対策あり）
    - calendar_management.py : JPX カレンダー管理（営業日判定、更新ジョブ）
    - quality.py           : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py             : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py             : 監査ログテーブル定義・初期化ユーティリティ
    - etl.py               : ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py   : Momentum / Volatility / Value の計算
    - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - ai/、data/、research/ のほか、strategy / execution / monitoring 等の名前空間は
    __all__ に含まれており将来的な発注ロジック・監視ロジックとの統合が想定されています。

---

## 運用上のヒント / 注意事項

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを設定してください。live 環境ではより慎重な設定と権限管理が必要です。
- .env / .env.local の自動読み込みは config.py によりプロジェクトルートを基準に行われます。CI などで明示的に読み込み制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI / J-Quants の API 呼び出しはそれぞれリトライやレート制御を持ちますが、実運用では監視・アラート設定を行うことを推奨します（Slack 通知等）。
- DuckDB のスキーマ設計は冪等性を重視していますが、スキーマ変更時や外部ツールで直接 DB を編集する場合は整合性に注意してください。
- news_collector は外部 RSS を取得するため、RSS のパース失敗や接続エラーに備えたログ運用を行ってください。

---

## 貢献 / 開発

- 単体テストや CI の設定を追加すると品質が向上します。AI 呼び出し箇所やネットワーク I/O はモック可能なように設計されています（例: _call_openai_api の差し替え、_urlopen のモック）。
- ドキュメントや example スクリプトを整備して、ETL や運用ジョブ（スケジューリング）のサンプルを提供してください。

---

必要であれば、README に含める具体的なコマンド例（systemd ユニット、cron ジョブ、Dockerfile）、依存パッケージ一覧（requirements.txt）、または各モジュールの API リファレンスを追記します。どれを追加しますか？