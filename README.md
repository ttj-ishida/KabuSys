# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを統合的に提供します。

---

## 特徴（機能一覧）

- Data ETL
  - J-Quants からの株価（日足）・財務情報・上場情報・マーケットカレンダー取得（ページネーション対応）
  - 差分更新・バックフィル・保存（DuckDB への冪等保存）
- データ品質チェック
  - 欠損・重複・日付不整合・スパイク検出
  - QualityIssue として詳細を収集
- ニュース収集 & 前処理
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini, JSON mode）→ ai_scores テーブルへ保存
  - エラー時フェイルセーフ（失敗をスキップして継続）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出・保存
- 研究用ツール群
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー、Zscore 正規化
- 監査ログ（トレーサビリティ）
  - signal_events, order_requests, executions 等の監査テーブル定義と初期化ユーティリティ
  - 監査用専用 DuckDB の初期化関数を提供
- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数をラップする Settings オブジェクト

---

## 必要条件（依存関係の例）

主に以下のパッケージを使用します（プロジェクトの pyproject.toml / requirements.txt を参照してください）:

- Python 3.9+（型ヒントで | を使用しているため 3.10 推奨）
- duckdb
- openai
- defusedxml

その他標準ライブラリ（urllib, json, logging, datetime, etc）を使用。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトに requirements.txt / pyproject.toml があれば:
     - pip install -e .
4. 環境変数を用意（.env ファイルをプロジェクトルートに置くことを推奨）
   - 自動ロード順序: OS 環境 > .env.local > .env
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（必要なキーの一覧）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# Kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...
# Slack（通知等に利用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# データベースパス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境 (development | paper_trading | live)
KABUSYS_ENV=development

# ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
LOG_LEVEL=INFO
```

---

## 使い方（主要 API / 例）

下記はライブラリの代表的な使い方サンプルです。実行前に環境変数を設定してください。

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続作成（例）
```python
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None, id_token=None)
print(result.to_dict())
```

- ニュース NLP スコア付与（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date は日付（例: バックテスト用に指定）
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 監査テーブルが作成される
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility

mom = calc_momentum(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
```

- カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trade = is_trading_day(conn, date(2026,3,20))
nxt = next_trading_day(conn, date(2026,3,20))
```

注:
- OpenAI の呼び出しは api_key 引数が None の場合、環境変数 OPENAI_API_KEY を参照します。
- API 呼び出しが失敗した場合は多くの関数で「安全側のフォールバック」を行う（例: スコア 0.0、処理スキップ）ため、完全な成功を期待する場合はログや戻り値で確認してください。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabuAPI ベース URL（省略時はローカルのデフォルト）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development|paper_trading|live）
- LOG_LEVEL: ログレベル

---

## ディレクトリ構成

（プロジェクトの主要ファイル・モジュール構成を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄ごとスコアリング）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult 再エクスポート
    - calendar_management.py — マーケットカレンダー管理 / 営業日判定
    - stats.py               — 統計ユーティリティ（zscore 等）
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - ai/ (上記)
  - その他:
    - monitoring/（SQLite などでの監視用コードは別モジュールに存在する想定）
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートに存在する想定）
- .env.example（プロジェクトルートに置くことを推奨）

---

## ロギング・デバッグ

- 標準の logging モジュールを使用。環境変数 LOG_LEVEL でレベルを制御できます（INFO デフォルト）。
- 開発中は LOG_LEVEL=DEBUG を指定すると詳細な内部ログが出力されます。

---

## テスト・モックについて

- OpenAI や外部 HTTP 呼び出しは各モジュール内でラップされており、ユニットテスト時は該当関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.data.news_collector._urlopen 等）をモックすることを想定しています。
- ETL などは DuckDB のインメモリ接続（":memory:"）でテスト可能です。

---

## 注意点 / 設計上の方針

- ルックアヘッドバイアス対策: 多くの関数は date.today() を直接参照せず、呼び出し側が target_date を渡す設計です。
- 冪等性: DuckDB への保存は基本的に ON CONFLICT を使った上書きで冪等に実装されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時はプロセス全体を止めず、可能な限りログ出力して部分的に継続します。
- セキュリティ: RSS 取得の際は SSRF 対策・サイズ制限・defusedxml による XML 攻撃対策を導入しています。

---

この README は本コードベースに含まれるモジュール群と主要な使い方を簡潔にまとめたものです。詳細な API やスキーマ、実運用設定（kabuステーション連携や Slack 通知のフロー等）は各モジュールの docstring を参照してください。必要であればサンプルの .env.example やデプロイ手順、運用チェックリストも作成できます。