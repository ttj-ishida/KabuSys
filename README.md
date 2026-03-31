# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを備え、バックテストや本番自動売買システムの基盤として利用できます。

主な設計方針：
- Look‑ahead bias を避ける設計（関数内で date.today() 等を参照しない）
- DuckDB を中心とした軽量なデータストア
- 冪等（idempotent）な ETL / DB 保存処理
- API リトライ・レート制御・セーフフェールを内包

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須設定値の取得（settings オブジェクト）
- データ収集 / ETL
  - J-Quants から株価（日足）、財務、上場情報、マーケットカレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付整合性チェック（run_all_checks）
- ニュース収集・前処理
  - RSS からの安全な収集（SSRF 対策、gzip 制限、XML の安全パース）
  - URL 正規化と記事 ID 生成
- ニュース NLP / AI
  - 銘柄ごとのニュースセンチメント算出（score_news：OpenAI gpt-4o-mini）
  - マクロニュースと ETF (1321) MA による市場レジーム判定（score_regime）
  - API 呼び出しのリトライ、レスポンス検証、JSON モード対応
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum 等）
  - 将来リターン、IC（スピアマン）、統計サマリ、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（init_audit_schema / init_audit_db）
  - 発注トレーサビリティ（UUID ベースで冪等キー管理）
- その他ユーティリティ
  - マーケットカレンダー管理（営業日判定、翌営業日/前営業日取得）
  - J-Quants クライアント（レート制御・トークンリフレッシュ・保存関数）

---

## 要件

- Python >= 3.10
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

（プロジェクトの pyproject.toml / requirements.txt を参照して具体的なバージョンを管理してください）

---

## セットアップ手順

1. リポジトリをクローン / 環境に配置
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -e .          # 開発インストール（pyproject.toml が整備されている前提）
   - または: pip install duckdb openai defusedxml

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で .env / .env.local を読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - KABU_API_PASSWORD=（kabuステーション API パスワード）
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
     - OPENAI_API_KEY=sk-...
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=Cxxxxxx
     - DUCKDB_PATH=data/kabusys.duckdb         # デフォルト
     - SQLITE_PATH=data/monitoring.db         # デフォルト
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - .env ファイルの例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX
     DUCKDB_PATH=./data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプト内での利用例です。

- DuckDB 接続の作成（設定で指定したパスを利用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(settings.duckdb_path)
```

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント（OpenAI 必須）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API key は環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"Scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して schema を追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- ファクター計算 / リサーチ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- マーケットカレンダーのユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- 各関数は docstring に使用前提テーブル（例: raw_news, prices_daily 等）を明記しています。ETL を適切に走らせて対象テーブルが整備されていることを確認してください。
- OpenAI を利用する処理は API 使用コストが発生します。利用時は API key とレートに注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                                  - 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                               - ニュースセンチメント（score_news）
  - regime_detector.py                        - 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                         - J-Quants API クライアント（fetch/save）
  - pipeline.py                               - ETL パイプライン（run_daily_etl 等）
  - etl.py                                    - ETL の公開型（ETLResult）
  - news_collector.py                          - RSS ニュース収集
  - quality.py                                 - データ品質チェック
  - stats.py                                   - 共通統計ユーティリティ
  - calendar_management.py                     - マーケットカレンダー管理
  - audit.py                                   - 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                         - Momentum/Value/Volatility 等
  - feature_exploration.py                     - 将来リターン / IC / rank 等
- research/__init__.py
- その他モジュール（strategy / execution / monitoring 等はパッケージ公開対象に含まれる想定）

（上記はソースの主要ファイルを抜粋したものです。実際のリポジトリには追加ファイルやドキュメントが存在する可能性があります。）

---

## 実運用上の注意

- 本ライブラリは本番口座での自動売買を想定した機能群を含みます。実際の発注処理（kabu API の呼び出し等）を行う場合は、十分なテストとリスク管理を行ってください。
- ETL・API 呼び出しはネットワークや外部サービスに依存します。リトライやフェイルセーフが組み込まれていますが、運用監視（ログ / Slack 通知等）を必ず設けてください。
- OpenAI のレスポンスは将来的に変更される可能性があるため、レスポンス検証ロジックやエラーハンドリングの更新を行ってください。
- DuckDB のバージョンによっては executemany の挙動など差異があるため、CI 環境と本番環境でバージョンを合わせることを推奨します。

---

これで README の簡易版です。必要であれば以下を追加で作成できます：
- .env.example のテンプレート
- 具体的な依存ファイル（pyproject.toml / requirements.txt）例
- 監査スキーマの ER 図やテーブル定義の詳細ドキュメント
- よくあるトラブルシュート（FAQ）