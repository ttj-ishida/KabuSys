# KabuSys

KabuSys は日本株のデータ取得・ETL・特徴量計算・ニュースNLP・市場レジーム判定・監査ログなどを備えた自動売買／リサーチ向けライブラリです。DuckDB を内部データストアとして利用し、J-Quants / JPY マーケットカレンダー / OpenAI（ニュース解析）などと連携する設計になっています。

---

## 主な特徴

- データ取得（J-Quants）
  - 日次株価（OHLCV）、財務データ、上場情報、JPX カレンダーの差分取得（ページネーション対応）
  - レート制限・再試行・リフレッシュトークン対応
- ETL パイプライン
  - 差分取得、冪等保存（ON CONFLICT）、品質チェックの統合
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出するチェック群
- ニュース収集・前処理
  - RSS フィード取り込み、URL 正規化、SSRF 予防、記事ID の冪等化
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメントを LLM で評価して ai_scores に保存
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と合わせて判定）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、Z スコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に初期化するユーティリティ

---

## 必要環境（推奨）

- Python 3.10+
- DuckDB
- openai（OpenAI の公式クライアント）
- defusedxml
- （標準ライブラリ以外の依存はプロジェクトで管理してください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要パッケージの例
pip install duckdb openai defusedxml
# 開発パッケージやプロジェクトを editable install する場合
pip install -e .
```

（実際の requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（モジュール `kabusys.config` が担当）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（モニタリング DB）パス（デフォルト: data/monitoring.db）
- その他監視設定（PID ファイル、閾値など）

例（`.env` の一部）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=...
```

注意:
- `.env` の読み込み順は OS 環境 > .env.local > .env です（module: kabusys.config）。
- 自動読み込みの挙動はプロジェクトルート（.git または pyproject.toml を探索）を基準にします。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - requirements.txt / pyproject.toml がある場合はそちらを利用
   ```bash
   pip install -r requirements.txt
   # または
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数として設定してください。
   - 例: `.env.example` を参考に作成します（リポジトリに例がない場合は上記の変数を利用）。

5. DuckDB データベースを作成（任意）
   - デフォルトのパスは `data/kabusys.duckdb`。必要であれば先にディレクトリを作成してください。
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な API / 実行例）

以下は主な機能の簡単な利用例です。各関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ることが多いです。

1. DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定するか省略して今日実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュース NLP スコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key 引数を渡すか、環境変数 OPENAI_API_KEY をセット
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} codes")
```

3. 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 監査ログデータベース初期化
```python
from kabusys.data.audit import init_audit_db

# 別 DB を監査用に作る場合
conn_audit = init_audit_db("data/audit.duckdb")
# または init_audit_db(":memory:")
```

5. ファクター計算・研究用ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.data.stats import zscore_normalize
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
```

ヒント:
- OpenAI の呼び出しを行う関数は api_key を直接渡せます（テスト時は mock 可能）。
- ETL / データ取得は外部 API に依存するため、認証トークンやネットワーク設定に注意してください。

---

## よく使うモジュール一覧（短い説明）

- kabusys.config
  - 環境変数の自動読み込みと Settings オブジェクトを提供
- kabusys.data.jquants_client
  - J-Quants API の取得・保存ユーティリティ（fetch_* / save_*）
- kabusys.data.pipeline
  - run_daily_etl を含む ETL パイプラインと ETLResult
- kabusys.data.quality
  - データ品質チェック群
- kabusys.data.news_collector
  - RSS 取得・前処理・保存ロジック
- kabusys.ai.news_nlp
  - ニュースを LLM で評価して ai_scores に書き込む
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 とマクロニュースで市場レジームを判定
- kabusys.research
  - ファクター計算と統計ユーティリティ

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは `src/kabusys/` に配置されています。主要ファイル / モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境設定（.env ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（スコアリング）
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py            — RSS 収集・前処理
    - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
    - quality.py                   — データ品質チェック
    - stats.py                     — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Value / Volatility 等
    - feature_exploration.py       — 将来リターン / IC / summary 等

---

## 注意点 / ベストプラクティス

- Look-ahead Bias 回避のため、多くの関数は内部で date.today() を参照せず、明示的な target_date を受け取る設計です。バックテストや過去検証時は必ず target_date を指定してください。
- OpenAI 呼び出しはコストがかかる・可変な応答があるため、テスト時はモック（unittest.mock.patch）することを推奨します。news_nlp と regime_detector はそれぞれ独自の内部 _call_openai_api を持ち、テスト差し替えがしやすくなっています。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、本実装では事前に空チェックを行っています。DuckDB のバージョン依存に注意してください。
- RSS 取得では SSRF 対策・受信サイズ制限・XML の安全パーサ（defusedxml）を採用していますが、運用時はソース URL の定期チェックと監視を行ってください。

---

## 貢献 / テスト

- コードを変更する際はユニットテスト・統合テストを追加してください（OpenAI / J-Quants 等外部 API はモック化）。
- ローカルでの開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして .env の自動読み込みを無効化できます（テストの独立性向上に有効）。

---

README に記載のない詳細な使い方や内部仕様（SQL スキーマ、パラメータチューニングなど）は各モジュールの docstring を参照してください。README に補足や追加したい項目があれば教えてください。