# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI によるセンチメント評価）、ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

---

## 主な特徴

- データ取得（J-Quants API）と冪等保存（DuckDB）
- ニュース収集（RSS）と前処理、LLM による銘柄別センチメントスコアリング
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレーサビリティ）
- 環境変数／.env 自動読み込み（プロジェクトルートベース）

---

## 必要条件

- Python 3.10 以上（PEP 604 の `X | Y` アノテーション使用のため）
- 主要な依存パッケージ例:
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime 等）

インストールはプロジェクトの pyproject.toml / requirements.txt を使用してください。簡易例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数

自動読み込み（.env / .env.local）を行います（プロジェクトルートは .git または pyproject.toml を探索して決定）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用する環境変数（必須は README 内で明示）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

例（.env）:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 依存パッケージをインストール
   ```bash
   pip install -r requirements.txt
   # または主要ライブラリのみ
   pip install duckdb openai defusedxml
   ```
4. .env を作成して必要な環境変数を設定（上記参照）
5. DuckDB ファイルや出力ディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下はライブラリの代表的な利用例です。すべての呼び出しは DuckDB の接続を渡して実行します。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーが環境変数に必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（MA とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査専用 DB の初期化も可能）
```python
from kabusys.data.audit import init_audit_db, init_audit_schema

# 監査専用ファイルを作る場合
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn にスキーマ追加する場合
init_audit_schema(conn, transactional=True)
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- Z スコア正規化ユーティリティ
```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点:
- score_news / score_regime は OpenAI API を使用するため、適切な API キーが必要です。
- ETL・ニュース収集などは Look-ahead bias を避ける設計になっており、内部で date.today() を直接参照しない関数が多くあります。テスト時は target_date を明示的に渡してください。

---

## ディレクトリ構成

主要なソースは src/kabusys 配下です。概略は次のとおり:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM センチメント評価（銘柄別 ai_scores 書込み）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 結果クラス再エクスポート（ETLResult）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - news_collector.py — RSS 取得・前処理・保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - audit.py — 監査ログスキーマの初期化 / audit DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー 等

（上記以外に strategy / execution / monitoring 等のパッケージが想定されていますが、本リポジトリの該当ファイルに従ってください。）

簡易ツリー（抜粋）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ calendar_management.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 運用上の注意

- J-Quants API と OpenAI API はリクエスト回数・費用が発生します。実行頻度には注意してください。
- J-Quants クライアントにレートリミットやリトライ実装がありますが、運用側でも呼び出し頻度を管理してください。
- 本ライブラリはバックテストや本番運用での look-ahead bias を防ぐために設計思想が組み込まれています（多くの関数で target_date を明示的に受け取る等）。
- DuckDB の executemany に関する互換性（空リスト不可など）を意識した実装が存在します。DuckDB バージョンにより挙動が異なる可能性があるため注意してください。

---

## 貢献・拡張

- strategy（シグナル生成）や execution（ブローカー接続）モジュールを追加してトレードフローを完成させることができます。
- news_collector の RSS ソース追加や NLP のプロンプト改善、OpenAI モデルの変更（gpt-4o-mini 等）により精度向上が期待できます。
- 監査ログ（audit）や監視（monitoring）を組み合わせて運用監視を強化してください。

---

必要であれば README に含める具体的なセットアップ手順（Docker / systemd ジョブ / CI 実行例）や、より詳細な API リファレンス、サンプル .env.example を作成します。どの情報を追加したいか教えてください。