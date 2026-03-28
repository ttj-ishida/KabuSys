# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からの株価/財務/カレンダー取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（オーダー/約定トレース）、および市場レジーム判定などの機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数 / .env
- 使い方（基本例）
- ディレクトリ構成
- 注意事項 / 運用上のヒント

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・研究・監査・AI スコアリングまでを一貫して扱うための内部ライブラリ群です。  
主に次の用途を想定しています:

- J-Quants API からの差分 ETL（株価 / 財務 / 市場カレンダー）
- RSS を用いたニュース収集と NLP による銘柄センチメント算出（OpenAI）
- ファクター計算・特徴量探索（研究用途）
- 市場レジーム判定（ETF とマクロニュースを組合せた判定）
- 監査用テーブル（signal → order_request → execution のトレース）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- DuckDB を利用したローカル DB 操作（高速な分析向け）
- Look-ahead bias を防ぐ設計（バックテストでの誤用を防止）
- API 呼び出しに対するリトライやレート制御・フェイルセーフ実装
- OpenAI（gpt-4o-mini）を JSON mode で利用する設計（テスト容易性を考慮）

---

## 主な機能（抜粋）

- ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー、株価、財務の差分取得と品質チェックを一括実行
  - 個別 ETL: run_prices_etl / run_financials_etl / run_calendar_etl

- データ品質（kabusys.data.quality）
  - 欠損検出 / スパイク検出 / 重複検出 / 日付整合性チェック
  - QualityIssue を返して呼び出し元で対応を決定

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・正規化・前処理・raw_news への冪等保存支援
  - SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去など堅牢化

- ニュース NLP（kabusys.ai.news_nlp）
  - 銘柄ごとに記事を集約して OpenAI に渡し、銘柄センチメント（-1.0〜1.0）を ai_scores テーブルに保存
  - バッチ処理・リトライ・レスポンス検証あり

- 市場レジーム（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュース（LLM）のスコアを重み合成して daily の市場レジームを判定・保存

- 研究ユーティリティ（kabusys.research）
  - momentum / value / volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、z-score 正規化など

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルの DDL と初期化ユーティリティ
  - init_audit_db で監査用 DuckDB を作成・初期化

- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御・リトライ・トークン自動リフレッシュ・ページネーション対応の API ラッパー
  - save_* 関数で DuckDB へ冪等保存

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 演算子を使用）
- DuckDB が利用可能（Python パッケージ duckdb を利用）
- OpenAI を使う機能は OpenAI API キーが必要

1. リポジトリをクローン / 配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに setup/pyproject があれば `pip install -e .` を利用できます）

4. 環境変数を設定
   - 下記「環境変数 / .env」参照

5. DuckDB の準備
   - デフォルトでは data/kabusys.duckdb を使用します（settings.duckdb_path で変更可能）
   - 監査用 DB を別途用意する場合は init_audit_db を利用

---

## 環境変数 / .env

パッケージ起動時に自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数
- JQUANTS_REFRESH_TOKEN - 必須: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - 必須: kabu ステーション API のパスワード
- KABU_API_BASE_URL - オプション: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN - 必須: Slack 通知を使う場合
- SLACK_CHANNEL_ID - 必須: Slack 通知先チャンネル
- OPENAI_API_KEY - OpenAI 呼び出しに使用（news_nlp / regime_detector）
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視 DB など（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env の書式解釈はシェル風（export KEY=val やシングル/ダブルクォート対応）です。

---

## 使い方（基本例）

以下は Python REPL やスクリプトから利用する代表的な例です。

準備: DuckDB 接続と settings の利用例
```python
import duckdb
from kabusys.config import settings

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略すると today）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースセンチメントを算出して ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"{count} 銘柄のスコアを保存しました")
```

3) 市場レジームをスコアして market_regime に保存する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) 研究用ユーティリティ（ファクター計算例）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
```

ログレベルや環境は settings で検証されます（KABUSYS_ENV, LOG_LEVEL）。

---

## ディレクトリ構成

主要モジュールのツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py               - 環境変数 / .env 読込と Settings
  - ai/
    - __init__.py
    - news_nlp.py           - ニュース NLP（OpenAI 経由で銘柄スコア）
    - regime_detector.py    - 市場レジーム判定
  - data/
    - __init__.py
    - etl.py                - ETL インターフェース（ETLResult 再エクスポート）
    - pipeline.py           - 日次 ETL パイプラインと個別 ETL
    - jquants_client.py     - J-Quants API クライアント（取得・保存関数）
    - news_collector.py     - RSS 取得・前処理
    - calendar_management.py- 市場カレンダー管理・営業日判定
    - quality.py            - データ品質チェック
    - stats.py              - 基本統計ユーティリティ（zscore_normalize）
    - audit.py              - 監査ログ DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py    - 各種ファクター計算（momentum, value, volatility）
    - feature_exploration.py- 将来リターン、IC、統計サマリー等

（上記は抜粋です。実際のリポジトリにはさらに詳細な実装・ユーティリティが含まれます）

---

## 注意事項 / 運用上のヒント

- OpenAI や J-Quants 等の外部 API を呼ぶ処理はキーや課金が関係します。テスト時はモック（unittest.mock）で _call_openai_api や jquants_client._request 等を差し替えてください。
- settings.env は "development", "paper_trading", "live" のいずれかである必要があります。live モードでは実際の注文系処理での危険があるため、本番運用前に十分な検証を行ってください。
- ニュース収集は RSS を利用しますが、SSRF/大容量レスポンス対策や XML パース対策が組み込まれています。外部 URL を扱う部分は慎重に扱ってください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン依存問題があるため、ライブラリ実装側でチェック済みです。独自に SQL を追加する際は注意してください。
- ETL は複数ステップで失敗を収集する設計です。結果の ETLResult から errors / quality_issues を確認して運用判断を行ってください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。CI 等で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 参考: よく使うコマンド例

- パッケージを editable install（開発時）:
  - pip install -e .

- DuckDB コンソールでファイルを確認:
  - python -c "import duckdb; conn=duckdb.connect('data/kabusys.duckdb'); print(conn.execute('SELECT count(*) FROM information_schema.tables').fetchall())"

- ETL をスクリプトから定期実行（簡易例）:
  - scripts/run_etl.py を作り cron / systemd timer で実行する（本リポジトリに含めることを推奨）

---

README に記載のない詳細な API 仕様やテーブルスキーマはソースコード内の docstring / コメントを参照してください。必要ならば具体的な使い方（例: ETL の cron 設定、Slack 通知の使い方、バックテストでのデータ利用方針）についても別途ドキュメント化できます。必要であれば教えてください。