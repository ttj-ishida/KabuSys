# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 経由）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）、および研究用ファクター計算や統計ユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的で設計された内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集し、OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出して保存
- ETF 指標（1321 の MA200 乖離）とマクロニュースセンチメントを組み合わせた市場レジーム判定
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ（Zスコアなど）
- 監査ログ（シグナル／発注要求／約定）のスキーマ初期化と管理
- データ品質チェックモジュール

設計上の特徴（抜粋）:
- ルックアヘッドバイアス回避を重視（関数内部で datetime.today() を直接参照しない等）
- OpenAI / J-Quants 呼び出しにリトライやバックオフ、フェイルセーフ処理を実装
- DuckDB を中心としたローカルデータストア（軽量で高速な分析向け）
- 冪等性（ON CONFLICT / ID キーによる再実行安全性）を考慮

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS -> raw_news）
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化・管理（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - ニュース NLP（score_news: 銘柄別センチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ma200 とマクロセンチメントを合成し market_regime に保存）
- research:
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）

---

## 必要条件 / 依存パッケージ

- Python 3.10+
- duckdb
- openai (対応する SDK、ここでは OpenAI の新版 SDK の利用を前提)
- defusedxml

※ 他に標準ライブラリの urllib, logging, datetime, pathlib などを使用しています。実行環境によっては追加のパッケージや OS レベルでのライブラリが必要になる場合があります。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# pip install -e . などでパッケージ化している場合はプロジェクトをインストール
```

---

## 環境変数 / .env

パッケージは起動時にプロジェクトルート（.git または pyproject.toml の存在）を探索し、`.env` / `.env.local` を自動読み込みします（OS 環境変数優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用する環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI API キー（ai.score系で使用）

例 `.env`（プロジェクトルートに配置）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカルでの利用例）

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```
4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
5. DuckDB データベース用ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```
6. 監査ログ用 DB を初期化（任意）
   ```python
   from pathlib import Path
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db(Path("data/audit.duckdb"))
   # conn は duckdb 接続オブジェクト
   ```

---

## 使い方（代表的な例）

以下は Python REPL / スクリプト内での使い方例です。

- settings の参照（環境変数経由）
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（1321 MA200 とマクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら env OPENAI_API_KEY を使用
```

- ファクター計算（研究用）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査スキーマ初期化（既存接続にテーブルを作る）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 注意点 / 運用上の留意事項

- OpenAI API 呼び出しや J-Quants API は課金・レート制限があるため運用時は注意してください。J-Quants は 120 req/min を想定した RateLimiter を実装しています。
- API キーは秘匿管理してください（.env、Vault 等を利用）。
- モジュールはルックアヘッドバイアスを避ける実装方針です。バックテストでの使用時は関数のドキュメントに従い target_date を明示してください。
- 自動ロードされる `.env` はプロジェクトルートを基準に探索します。CI やテストで不要であれば `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- DuckDB のバージョン差異で SQL の振る舞いが異なる場合があります。テスト環境と本番環境でバージョン差がないようにしてください。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールとその役割です（プロジェクトの src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュースセンチメント算出（OpenAI）
    - regime_detector.py -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント（fetch/save）
    - pipeline.py       -- ETL パイプライン（run_daily_etl 等）
    - etl.py            -- ETLResult の公開
    - news_collector.py -- RSS 取得・前処理・保存
    - calendar_management.py -- 市場カレンダー管理
    - quality.py        -- データ品質チェック
    - stats.py          -- 統計ユーティリティ（Zスコア等）
    - audit.py          -- 監査ログスキーマ初期化 / DB 作成
  - research/
    - __init__.py
    - factor_research.py -- ファクター計算（momentum / value / volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー

各モジュールに詳細な docstring が付与されています。関数単位での入力要件や副作用（DB 書き込み）に注意して利用してください。

---

## 開発 / 貢献

- コード内に多くの設計方針・制約（ルックアヘッド回避、冪等性、リトライ設計など）が明記されています。変更を加える際はそれらを破壊しないようにしてください。
- テストはモジュールの外部依存（OpenAI / J-Quants / ネットワーク）をモックして実装することが推奨されます。

---

必要であれば README に追加したい情報（例: pyproject.toml / packaging 手順、CI 設定例、より具体的な .env.example テンプレート、実行スクリプト例など）を教えてください。