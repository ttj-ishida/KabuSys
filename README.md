# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI でのセンチメント解析）、ファクター計算・リサーチユーティリティ、監査ログスキーマなど、アルゴリズム取引／リサーチ基盤の主要機能をロジック単位で提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() や現在時刻を不用意に参照しない設計）
- DuckDB をデータ層に採用（高速な分析向け）
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライやレートリミット制御を備える
- 冪等性（ETL / DB 保存処理）を重視

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動ロード（プロジェクトルート検出）・必須環境変数チェック（kabusys.config）
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）取得、財務データ、JPX カレンダー（kabusys.data.jquants_client）
  - レート制限・トークン自動リフレッシュ・ページネーション対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付整合性）を含む日次 ETL（kabusys.data.pipeline）
- ニュース収集
  - RSS フィードからの記事収集、前処理、SSRF 対策、raw_news への冪等保存（kabusys.data.news_collector）
- ニュース NLP / LLM スコアリング
  - 銘柄ごとのニュースセンチメントスコア付与（gpt-4o-mini を想定）（kabusys.ai.news_nlp）
  - マクロニュースとETF MA200 を組み合わせた市場レジーム判定（bull/neutral/bear）（kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ、Zスコア正規化など
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査スキーマ定義と初期化ユーティリティ（kabusys.data.audit）
- 汎用統計・ユーティリティ
  - zscore_normalize、日付/カレンダー処理、各種ヘルパー

---

## 必要条件（依存パッケージ）

- Python >= 3.10（型注釈に `|` を使用）
- duckdb
- openai
- defusedxml

推奨インストール（例）
pip install duckdb openai defusedxml

プロジェクトで配布されている `pyproject.toml` / requirements を利用する場合はそちらに従ってください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
     または
   - pip install duckdb openai defusedxml

4. パッケージを編集可能インストール（開発）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動で読み込まれます（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数（用途）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD : kabuステーション等の API パスワード（運用時）
     - SLACK_BOT_TOKEN : Slack 通知用トークン
     - SLACK_CHANNEL_ID : Slack チャネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG / INFO / ...（デフォルト INFO）
     - KABU_API_BASE_URL : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - OPENAI_API_KEY : OpenAI 呼び出しを行う場合は環境変数または各関数の引数で指定可能

   例 `.env`（機密情報は必ず安全に管理してください）
   JQUANTS_REFRESH_TOKEN=xxxxxxxx...
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

---

## 使い方（主要ユースケース）

以下は簡単なサンプルコード例です。各関数の引数詳細はソースにドキュメントがあります。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI を使って銘柄ごとにスコア）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しているか、第二引数で直接渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定（ETF 1321 MA200 + マクロニュース）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が挿入されます
```

4) 監査ログ DB の初期化（独立した監査 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring.db")
# テーブルが作成されます
```

5) ファクター計算・リサーチ
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)

# 正規化など
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- OpenAI 呼び出しを行う関数（news_nlp.score_news、regime_detector.score_regime）は API キーを環境変数 OPENAI_API_KEY か引数で受け取ります。API 制限やコストに注意して実行してください。
- ETL / 保存処理は冪等設計ですが、実運用ではバックアップ・ログの管理を行ってください。

---

## ディレクトリ構成（主要ファイル）

（src レイアウト）
- src/
  - kabusys/
    - __init__.py
    - config.py                       : 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                   : ニュースの LLM スコアリング
      - regime_detector.py            : 市場レジーム判定（MA200 + マクロ）
    - data/
      - __init__.py
      - jquants_client.py             : J-Quants API クライアント & DB 保存関数
      - pipeline.py                   : ETL パイプライン & run_daily_etl
      - etl.py                        : ETL 外部インターフェース（ETLResult）
      - news_collector.py             : RSS 取得・前処理・raw_news 保存
      - calendar_management.py        : 市場カレンダー管理 / 営業日ロジック
      - stats.py                      : 統計ユーティリティ（zscore_normalize）
      - quality.py                    : データ品質チェック
      - audit.py                      : 監査ログ（テーブル DDL / 初期化）
    - research/
      - __init__.py
      - factor_research.py            : Momentum / Value / Volatility など
      - feature_exploration.py        : forward returns / IC / factor summary
    - monitoring/ (※実装ファイルがあればここに)
    - execution/  (※発注関連の実装があればここに)
- pyproject.toml / setup.cfg / requirements.txt （存在する場合）
- .env.example （プロジェクトルートに置くことを推奨）

---

## 開発・テストについての注意

- 自動で .env をロードする仕組みがあります。テスト環境で自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants API 呼び出し部分は外部 API に依存するため、ユニットテストでは各 _call_openai_api や jquants_client._request 等をモックすることを推奨します。ソース中にテスト用差し替えを想定した実装（関数分離・内部ユーティリティの設計）があります。
- DuckDB を用いるため、実行時に DB ファイルの権限や保存先ディレクトリの存在を確認してください。監査 DB 初期化関数は親ディレクトリを自動作成します。

---

## 連絡先 / 貢献

バグ報告・機能提案・プルリクエストはリポジトリの Issue / PR を通じてお願いします。設計方針（ルックアヘッドバイアス回避・冪等性・フェイルセーフ）を尊重した変更を歓迎します。

---

README は以上です。使い方の具体例や追加の CLI スクリプトが必要であれば、実行例やテンプレートを作成しますのでご指定ください。