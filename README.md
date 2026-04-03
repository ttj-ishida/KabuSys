# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター算出、監査ログ（発注/約定トレーサビリティ）、市場レジーム判定などの機能を提供します。

主な設計方針
- Look-ahead bias を避ける（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB を用いたローカルデータプラットフォーム
- 冪等性（ON CONFLICT / トランザクション）を重視した保存処理
- 外部 API 呼び出しに対する堅牢なリトライ / フェイルセーフ設計

バージョン: 0.1.0

---

## 機能一覧

- データ収集（J-Quants 経由）
  - 株価日足（OHLCV）
  - 財務情報（四半期等）
  - JPX マーケットカレンダー

- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集
  - RSS フィード取得、記事前処理、raw_news への冪等保存、銘柄紐付け

- ニュース NLP（OpenAI）
  - 銘柄ごとのセンチメントスコア生成（ai_scores テーブルへ保存）
  - マクロニュースの LLM 評価を用いた市場レジーム判定（market_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化

- カレンダー管理
  - 営業日判定、前後営業日の取得、JPX カレンダー自動更新ジョブ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルにより、シグナル→発注→約定までを UUID 連鎖でトレース可能に

- Utility
  - 設定管理（.env の自動読み込み / settings オブジェクト）
  - J-Quants クライアント（レート制御・トークン自動リフレッシュ・ページネーション対応）

---

## 要件

- Python 3.10 以上（型ヒントや Union 表記のため）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib 等）を多用

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで依存をパッケージ化している場合は pip install -e . を利用してください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと、自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主に使用する環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（必要に応じて）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : 通知用（任意）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等（監視・プロセス管理用）
- KABUSYS_ENV : development / paper_trading / live
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な API）

基本的に DuckDB 接続を渡して関数を呼び出します。以下は簡単な利用例です。

- DuckDB 接続の作成（ファイル）
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（日次パイプライン実行）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付与（指定日）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジーム判定（1321 MA200 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター計算（モメンタム / ボラティリティ / バリュー）
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

- Zスコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

is_trade = is_trading_day(conn, date(2026, 3, 20))
next_td = next_trading_day(conn, date(2026, 3, 20))
days = get_trading_days(conn, date(2026, 3, 1), date(2026, 3, 31))
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降、order_requests / signal_events / executions テーブルを利用可能
```

- J-Quants ID トークン取得（手動）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## 開発／テストのヒント

- 環境変数自動読み込み
  - パッケージの起点（src/kabusys/config.py）は .git または pyproject.toml を基準にプロジェクトルートを探索し、.env/.env.local を自動読み込みします。
  - 自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- OpenAI 呼び出し部分は内部で独立関数を使っているため、unittest.mock.patch を使って _call_openai_api を差し替えればテストが容易です。

- DuckDB による executemany の空リスト制約（バージョン依存）をコードが考慮しているため、テスト時も同様に動作します。

- news_collector の RSS 取得は SSRF 対策やサイズ制限を実装しているため、テストでは fetch_rss 内の _urlopen をモックできます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py  — 環境変数/設定管理
- ai/
  - __init__.py
  - news_nlp.py        — ニュースのセンチメント化、score_news
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch/save）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETLResult 再エクスポート
  - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py       — RSS 取得・前処理・保存
  - quality.py              — データ品質チェック（欠損・スパイク等）
  - stats.py                — 統計ユーティリティ（zscore_normalize）
  - audit.py                — 監査ログ（監査テーブル作成/初期化）
- research/
  - __init__.py
  - factor_research.py      — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py  — calc_forward_returns / calc_ic / rank / factor_summary
- monitoring/ (存在する場合、監視系モジュール)
- strategy/, execution/, monitoring/ (パッケージ化用エクスポート箇所あり)

（実際のリポジトリにはさらにファイルが存在する可能性があります。上は主要モジュールの一覧です）

---

## 注意事項

- 本ライブラリは実運用での発注や本番口座へのアクセスを含む可能性があるため、live 環境を使用する場合は十分なレビューとリスク管理を行ってください。
- OpenAI / J-Quants の API 呼び出しには料金が発生します。API キーと利用量にご注意ください。
- DuckDB ファイルはローカルファイルシステム上に保存されます。バックアップ・アクセス制御を適切に行ってください。

---

もし README に追加してほしい具体的な情報（例: pyproject.toml / requirements.txt の内容、デプロイ手順、CI 設定サンプル、サンプル .env.example）などがあれば教えてください。必要に応じて追記します。