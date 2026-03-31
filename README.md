# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
J-Quants / RSS / OpenAI（LLM）などからデータを収集・整備し、ファクター計算・ニュースセンチメント・市場レジーム判定、監査ログの初期化など自動売買システムで必要となる機能群を提供します。

---

## 主な特徴

- データETL
  - J-Quants API から株価（日足）・財務データ・市場カレンダーを差分取得して DuckDB に保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行
- ニュース処理（News NLP）
  - RSS 収集 → 前処理 → OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出して ai_scores に保存
  - API障害・リトライ・レスポンス検証を実装
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して daily レジーム（bull/neutral/bear）を算出
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン、IC・統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - strategy → signal → order_request → execution のトレーサビリティを取る監査スキーマを DuckDB に初期化
- 安全対策
  - RSS の SSRF 防止・XML の安全パース、API レート制御・リトライ、LLM 呼び出しのフォールバックなど

---

## 機能一覧（抜粋）

- kabusys.config
  - settings（環境変数ベースの設定取得、.env 自動ロード）
- kabusys.data
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client: API 呼び出し・保存処理（fetch/save 系）
  - news_collector: RSS 取得・前処理・保存
  - quality: データ品質チェック
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 監査テーブル作成 / init_audit_db
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

---

## 前提（Prerequisites）

- Python 3.10+
- 必要なライブラリ例（最小限）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / 各RSS）

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## インストール

開発環境での例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要パッケージをインストール
pip install duckdb openai defusedxml
# ローカル開発用にパッケージをインストール（プロジェクトルートで）
pip install -e .
```

---

## 環境変数 / 設定

設定は環境変数、またはプロジェクトルートに置かれた `.env` / `.env.local` から自動ロードされます。
自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用）。

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabuAPI の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY (必須 for LLM calls unless passed to functions) — OpenAI API キー

kabusys.config.settings を通じてこれらにアクセスできます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.jquants_refresh_token)  # 必須: 未設定だと ValueError
```

自動ロードの挙動:
- プロジェクトルートは現在ファイルの親ディレクトリ群内の `.git` または `pyproject.toml` を基準に探索
- 読み込み順: OS 環境 > .env.local > .env
- `.env` のパースはシェル風の `KEY=val`、引用符や # コメントなどに対応

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローン
2. 仮想環境を作る & アクティベート
3. 依存パッケージをインストール（duckdb, openai, defusedxml 等）
4. プロジェクトルートに `.env` を作成（.env.example があればそれを参考）
5. DuckDB データベースの作成・スキーマ初期化はアプリ側で行う（必要に応じて init_audit_db などを実行）

例: .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的なユースケースの例）

- DuckDB に接続して日次 ETL を実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today(), id_token=None)
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（OpenAI キーは環境変数か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime returned", res)
```

- 監査ログ用 DuckDB 初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成される
```

- 研究用ファクター計算例

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
```

注意点:
- 各関数はルックアヘッドバイアスを避ける設計（内部で date.today() に依存しない or 明示的 target_date を使う）
- OpenAI 呼び出しはネットワーク/429/5xx を考慮しており、テスト時は内部の _call_openai_api をモックできます

---

## 設定例（ログ出力）

```
export LOG_LEVEL=DEBUG
export KABUSYS_ENV=development
```

Python 内から logging を設定することで、各モジュールのログ出力を確認できます。

---

## テスト / モックのヒント

- LLM 呼び出しは各モジュール内の _call_openai_api を unittest.mock.patch で差し替え可能（news_nlp / regime_detector 共に専用のラッパーを持つ）
- .env の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
- news_collector ではネットワーク依存部分（_urlopen）をテストでモック可能

---

## ディレクトリ構成（主要ファイル）

概略:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ pipeline.py
   │  ├─ etl.py
   │  ├─ news_collector.py
   │  ├─ calendar_management.py
   │  ├─ quality.py
   │  ├─ stats.py
   │  ├─ audit.py
   │  └─ ...
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ monitoring/      (実装想定／監視関連)
```

各サブパッケージの責務:
- ai: LLM を使ったニュース解析・レジーム判定
- data: データ取得・保存・ETL・品質チェック・カレンダー管理・監査ログ
- research: ファクター計算・特徴量探索

---

## 開発・運用上の注意

- 本ライブラリは実際の売買システムの一部機能を提供しますが、発注・約定処理（broker 接続等）は別モジュール／運用設計と合わせて厳重に検証してください。
- OpenAI / J-Quants / kabuAPI の使用はそれぞれの利用規約を遵守してください。
- 本番運用（is_live）では設定やログの取り扱いに注意し、機密情報（APIキー等）は安全に管理してください。

---

README の追加要望や、具体的な実行例（ETL スケジュール設定、Docker 化、CI テスト例など）をご希望でしたら教えてください。必要に応じてサンプル .env.example や簡易スクリプトも作成します。