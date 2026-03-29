# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注追跡）など、売買システムに必要な基盤処理を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPX マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション対応、リトライ／レート制御内蔵
- データ品質チェック（quality）
  - 欠損、重複、スパイク、日付不整合の検出
- ニュース収集（news_collector）
  - RSS フィード収集、SSRF や XML 攻撃対策、URL 正規化、冪等保存
- ニュースNLP（news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出、ai_scores に保存
- 市場レジーム判定（regime_detector）
  - ETF（1321）の200日MA乖離 + マクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）判定
- 研究（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算、将来リターン計算、IC / 統計サマリー
- 監査ログ（audit）
  - シグナル → 発注要求 → 約定を追跡する監査用テーブル群（DuckDB）と初期化ユーティリティ
- 環境設定管理（config）
  - .env / .env.local / OS 環境変数から設定を読み込み（自動ロード、優先順位あり）

---

## 要求環境

- Python 3.10+
- 主な依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt にまとめてください）

例（仮の requirements）:
```
duckdb
openai
defusedxml
```

---

## セットアップ

1. リポジトリをクローン（開発パッケージがある想定）
2. 仮想環境を作成して有効化
3. 必要な依存をインストール

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発中であれば:
# pip install -e .
```

### 環境変数（.env）

プロジェクトルートの `.env` と `.env.local` は自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。  
自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくとも実行する機能に応じて設定してください）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行・発注関連）
- SLACK_BOT_TOKEN — Slack 通知（必要時）
- SLACK_CHANNEL_ID — Slack チャネル ID（必要時）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）

システム設定:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

データベースパス（デフォルト値、環境変数で上書き可）:
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 SQLite, デフォルト: data/monitoring.db)

例 `.env`（テンプレート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## データベース初期化

監査ログ専用 DB を初期化する例（DuckDB）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 返回された conn は DuckDB 接続
```

既存の DuckDB 接続に監査スキーマを追加する:
```python
from kabusys.data.audit import init_audit_schema
# conn は duckdb.connect(...) の接続
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要 API の例）

前提: DuckDB 接続は `duckdb.connect(<path>)` によって得られます。

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを算出して ai_scores に保存:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
```

- ファクター計算（例: モメンタム）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026,3,20))
# records は各銘柄の辞書リスト
```

- 統計ユーティリティ（Z-score 正規化）:
```python
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m"])
```

注意: OpenAI を呼ぶ関数（news_nlp.score_news, regime_detector.score_regime）は API キーを引数 `api_key` で渡すか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライ/フォールバック処理を持ちますが、API 使用料とレート上限に注意してください。

---

## ディレクトリ構成（概要）

以下は主要なモジュールと役割の抜粋です（src/kabusys 以下）。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数／設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを集約して OpenAI に投げ、銘柄別スコアを ai_scores テーブルへ保存
    - regime_detector.py — ETF MA とマクロニュースを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得／保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - news_collector.py — RSS 収集と raw_news 保存
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore）
    - audit.py — 監査ログスキーマの定義と初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatilityなどの計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/* など（分析用途）

各モジュールは基本的に DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。バックテストや戦略実行とは分離された設計です。

---

## 運用上の注意

- Look-ahead バイアス対策:
  - モジュールの多くは date 引数を明示的に受け取り、内部で datetime.now()/today() を参照しない方針です。バックテスト実行時は過去データのみを用いるよう注意してください。
- API キー・レート制御:
  - J-Quants と OpenAI のレート／料金に注意してください。jquants_client は 120 req/min の制限に合わせたレート制御を実装しています。
- 自動 .env 読み込み:
  - プロジェクトルート（.git / pyproject.toml の親ディレクトリ）を探索して `.env` / `.env.local` を読み込みます。テスト時など自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- セキュリティ:
  - news_collector は SSRF や XML 攻撃対策（ホスト検査、defusedxml、リダイレクト検査、レスポンス上限）を備えていますが、運用環境でのネットワーク制御や監査は別途必要です。

---

## 開発・テスト

- 単体テストやモックを使う際は、OpenAI 呼び出しやネットワーク関係の内部関数をモックすることで外部 API 依存を切り離せます（例: patch で _call_openai_api や _urlopen を差し替え）。
- 自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をテスト環境で設定すると環境変数の読み込みを防げます。

---

README はプロジェクトの導入メモとして最小限にまとめています。実運用やデプロイ時は、API キー管理、ログの集約、監視、定期的なジョブ実行（ETL・calendar_update 等）を追加で整備してください。必要であれば、README に追記するテンプレートやデプロイ手順（systemd / Airflow / cron など）も作成できます。