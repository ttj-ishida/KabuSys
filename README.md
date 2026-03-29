# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
DuckDB をデータレイヤに採用し、J-Quants API からのデータ取得（ETL）、ニュースの収集と LLM によるニュース解析、ファクター計算、監査ログ（トレーサビリティ）などを提供します。

主な設計方針：
- バックテストでのルックアヘッドバイアスを避ける設計（多くの関数が内部で `date.today()` を参照しない）
- DuckDB を用いた効率的な SQL + Python 実装
- J-Quants / OpenAI 呼び出しはリトライやレート制御など堅牢性を重視
- ETL/品質チェック/監査ログは冪等性を考慮して実装

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（kabusys.data.jquants_client, kabusys.data.pipeline）
  - 日次 ETL の一括実行（run_daily_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合等の検出
- ニュース収集・前処理（kabusys.data.news_collector）
  - RSS フィードから記事収集、URL 正規化、SSRF 対策、Gzip サイズ制限などの安全対策
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（JSON モード、バッチ処理、リトライ実装）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- ファクター計算・リサーチユーティリティ（kabusys.research）
  - Momentum, Value, Volatility 等の定量ファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定までの監査テーブル定義・初期化、冪等なスキーマ作成ユーティリティ

---

## 必要環境（推奨）

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- （用途に応じて）urllib / sqlite3 等の標準ライブラリ

インストール例:
```
pip install duckdb openai defusedxml
```
プロジェクト配布に requirements.txt / pyproject.toml があればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをチェックアウト／配置
   - パッケージは `src/kabusys` に配置されています（PEP 517/518 構成が想定）。

2. 仮想環境作成（推奨）
```
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージのインストール
```
pip install -r requirements.txt
# または個別に
pip install duckdb openai defusedxml
```

4. 環境変数の設定
- プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（ただし、テスト時などで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
- 必須の環境変数（少なくとも以下を設定してください）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=...

# OpenAI（score_news / score_regime に必要）
OPENAI_API_KEY=...

# kabuステーション（自動売買連携で必要）
KABU_API_PASSWORD=...
# KABU_API_BASE_URL は省略可能（デフォルト http://localhost:18080/kabusapi）

# Slack（通知等で必要）
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...

# DB ファイルパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

- `.env.example` を参考に `.env` を作成してください（コード中の _require() が未設定時に ValueError を投げます）。

---

## 使い方（簡易サンプル）

以下は主要ユーティリティの呼び出し例です。実際にはログ設定や例外処理を付けてください。

- 日次 ETL 実行（DuckDB 接続を渡す）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント（AI スコア）を取得して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {written} codes")
```

- 市場レジーム判定（regime score を market_regime テーブルへ書き込む）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

注意点:
- score_news および score_regime は OpenAI API キー（引数または環境変数 OPENAI_API_KEY）が必要です。
- これらの関数はルックアヘッドバイアスを避ける実装になっています（target_date 未満のデータのみ参照する等）。

---

## ディレクトリ構成（抜粋）

project-root/
- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数 / 設定読み込み
    - ai/
      - __init__.py
      - news_nlp.py                 # ニュースセンチメント（OpenAI）
      - regime_detector.py          # 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント + 保存
      - pipeline.py                 # ETL パイプライン（run_daily_etl など）
      - etl.py                      # ETL 結果クラスのエクスポート
      - news_collector.py           # RSS 収集
      - calendar_management.py      # 市場カレンダー管理
      - quality.py                  # 品質チェック
      - stats.py                    # 汎用統計ユーティリティ
      - audit.py                    # 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py          # ファクター計算（momentum/value/volatility）
      - feature_exploration.py      # 将来リターン / IC / 統計サマリー
    - research/...                   # 他の研究ユーティリティ等
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトにより異なる）
- .env.example                      # 環境変数サンプル（存在しない場合は作成推奨）

---

## 実装上の注意 / ベストプラクティス

- 環境分離:
  - 本番（live）とテスト（development / paper_trading）は `KABUSYS_ENV` で切替。実際の発注（kabu station 連携）や本番 API キーの管理は慎重に行ってください。
- キー管理:
  - OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN は安全に保管し、リポジトリに含めないでください。
- 自動環境読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。テストでこれを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト容易性:
  - OpenAI 呼び出しや HTTP 呼び出し箇所（news_nlp._call_openai_api 等）はモックしやすいよう分離されています。ユニットテストではこれらを patch して外部依存を排除してください。
- データベース操作:
  - DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、実装は空チェックを行っています。DuckDB バージョン互換性に注意してください。

---

もし README に含めたい追加の利用例や、デプロイ／CI／ロギング設定のテンプレート（systemd / cron / GitHub Actions 等）があれば教えてください。必要に応じてサンプル .env.example も作成します。