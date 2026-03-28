# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / kabuステーション API からのデータ取得（ETL）、ニュースの収集・NLP評価、ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。内部データストアには DuckDB を利用し、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価機能を備えます。

## 特徴（機能一覧）
- ETL（Daily ETL）: 株価日足、財務、JPXカレンダーの差分取得・保存・品質チェック
- J-Quants クライアント: ページネーション／リトライ／トークン自動リフレッシュ対応
- ニュース収集: RSS フィードの安全な取得（SSRF対策、gzip/サイズ制限、トラッキング除去）と raw_news 保存
- ニュースNLP: OpenAI を用いた銘柄別センチメントスコアリング（ai_scores への書き込み）
- 市場レジーム判定: ETF（1321）のMA乖離＋マクロニュースセンチメントで日次レジーム（bull/neutral/bear）を判定
- 研究ユーティリティ: ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン、IC/統計サマリー
- データ品質チェック: 欠損・スパイク・重複・日付不整合の検出
- 監査ログ／トレーサビリティ: signal → order_request → executions を追跡する監査スキーマの初期化・管理
- 設定管理: .env / 環境変数の自動読み込み（プロジェクトルート検出）と検証ユーティリティ

---

## 動作要件（主な依存）
- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- （標準ライブラリ：urllib, datetime, json, logging 等）

例:
pip install duckdb openai defusedxml

プロジェクトをパッケージとして使う場合は pyproject.toml/setup を想定しているため、
リポジトリルートで:
pip install -e .

もしくは開発時に直接 `PYTHONPATH=src` を使って import できます。

---

## セットアップ手順

1. リポジトリをクローンして適切な Python 仮想環境を用意
   - Python 3.10 以上を推奨

2. 依存ライブラリのインストール
   - 例: pip install duckdb openai defusedxml

3. 環境変数を設定
   - プロジェクトルートに `.env` を配置すると自動読み込みされます（.git または pyproject.toml があるディレクトリをプロジェクトルートとして探索）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ID トークン取得に使用）
   - KABU_API_PASSWORD : kabuステーション API パスワード（発注機能を使う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知に利用する場合
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で必須）
   - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : development / paper_trading / live（既定: development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）

5. 例: .env の雛形
```
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要なサンプル）

以下は代表的な利用例（Pythonスクリプト／REPL）です。import パスはパッケージが正しくインストール/読み込まれている前提です。

- 共通: 設定・DB 接続
```python
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコアリング（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# APIキーは環境変数 OPENAI_API_KEY または api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored codes:", count)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（DuckDB ファイルを別に作る例）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を監査用に使用
```

- ファクター計算・研究ユーティリティ
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- データ品質チェック（ETL 後に実行）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

---

## 注意点 / 設計上のポイント
- ルックアヘッドバイアス対策: 多くの関数は内部で date.today() を参照せず、明示的な target_date を受け取る設計です。バックテストや再現性を保つために target_date を明示的に渡してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時や特殊環境で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI クライアント呼び出しは retry/backoff を実装していますが、APIキーが未設定のときは ValueError を送出します。
- J-Quants クライアントは内部でレート制御とトークン自動更新を行います。大量に API を叩く際はレート制限に注意してください。

---

## ディレクトリ構成（抜粋）
```
src/kabusys/
├─ __init__.py                # パッケージのエントリ（__version__等）
├─ config.py                  # 環境変数・設定管理（.env 自動ロード）
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py             # ニュースセンチメントスコアリング（OpenAI 経由）
│  └─ regime_detector.py      # 市場レジーム判定（MA + マクロセンチメント）
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py       # J-Quants API クライアント（fetch / save）
│  ├─ pipeline.py             # ETL パイプライン（run_daily_etl 等）
│  ├─ calendar_management.py  # 市場カレンダー管理・営業日判定
│  ├─ news_collector.py       # RSS ニュース収集（SSRF 対策等）
│  ├─ quality.py              # データ品質チェック
│  ├─ stats.py                # 共通統計ユーティリティ（zscore 等）
│  ├─ audit.py                # 監査ログスキーマ定義・初期化
│  └─ etl.py                  # ETL 公開インターフェース（ETLResult 再エクスポート）
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py      # Momentum/Value/Volatility などのファクター算出
│  └─ feature_exploration.py  # 将来リターン・IC・統計サマリ等
# （その他: strategy / execution / monitoring 等のサブパッケージが想定）
```

主要モジュールの役割はそれぞれのファイル冒頭に記載された docstring を参照してください。

---

## 開発・貢献
- コードはテスト容易性を考慮して設計されています（API 呼び出しや時間系の関数は差し替え可能）。
- 新しい ETL ジョブや API クライアントの追加、監査スキーマの拡張は既存のパターンに従って実装してください。
- Pull Request 時はユニットテストと静的解析（型チェック）を推奨します。

---

もし特定の利用例（バックテスト、kabu 連携、Slack 通知の実装など）について詳しい README 追記を希望される場合は、どの機能を重点的に説明するか教えてください。