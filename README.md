# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム／データ基盤のライブラリ群です。ETL（J-Quants からのデータ取得）、ニュース収集 & NLP（OpenAI を用いたセンチメント解析）、ファクター研究、監査ログ（発注→約定のトレーサビリティ）など、トレーディングシステムに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分・バックフィル機能、取得済みデータの冪等保存（ON CONFLICT）
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP
  - RSS フィードからの安全なニュース収集（SSRF対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）による銘柄別センチメント解析（ai_scores へ保存）
  - ニュースウィンドウ管理（前日15:00 JST ～ 当日08:30 JST のウィンドウ）

- 市場レジーム判定
  - ETF（1321）の200日移動平均乖離とマクロニュースの LLM センチメントを合成し、
    日次で 'bull' / 'neutral' / 'bear' を判定して market_regime に保存

- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計要約
  - クロスセクション Z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化関数
  - 発注フローの完全トレースをサポート（UUID ベースで冪等キー管理）

- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ内で自動ロード）
  - 必須変数は Settings クラスで明示（例: JQUANTS_REFRESH_TOKEN）

---

## セットアップ

前提
- Python 3.10+（型ヒントで `X | None` を使用しているため）
- ネットワークアクセス（J-Quants, OpenAI など）

推奨パッケージ（代表）
- duckdb
- openai
- defusedxml

例: 仮想環境作成・依存インストール（プロジェクトに requirements.txt が無い場合は代表パッケージをインストールしてください）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# optional: pip install -e .
```

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くことで自動的に読み込まれます（環境変数が優先）
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に参照）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL

簡単な .env 例
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_BASE_URL=http://localhost:18080/kabusapi
KABU_API_PASSWORD=your_pw
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API）

以下はライブラリを直接利用する最小の使用例です。実行には必要な環境変数が設定されていることを前提とします。

DuckDB 接続例
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

日次 ETL を実行（株価・財務・カレンダー取得＋品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース（AI）スコアリング（指定日）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で上書き可。None なら OPENAI_API_KEY を参照
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

監査ログ DB 初期化（監査用 DuckDB を作成してスキーマを適用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて発注・約定履歴を保存/参照できます
```

設定オブジェクト（環境変数参照）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

注意点
- AI 呼び出し（OpenAI）には API キーが必要です。score_news / score_regime は api_key 引数で注入可能（テスト向け）。
- ニュース収集や ETL は外部 API を叩くため、レート制限や鍵の管理に留意してください。
- run_daily_etl は内部で market_calendar を参照して target_date を営業日に調整するため、先にカレンダーが更新されます。

---

## ディレクトリ構成

主要なソース構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの集約・OpenAI を使った銘柄センチメント解析
    - regime_detector.py            — ETF MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py        — JPX カレンダー（営業日判定、next/prev/get）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 再エクスポート
    - jquants_client.py             — J-Quants API クライアント（取得・保存関数）
    - news_collector.py             — RSS 収集（SSRF 対策・前処理・保存）
    - quality.py                    — データ品質チェック（欠損・重複・スパイク等）
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Value / Volatility 等のファクター実装
    - feature_exploration.py        — 将来リターン, IC, 統計サマリ等

各モジュールはドメインごとに責務を分けており、DuckDB 接続や API キーは明示的に引数で注入可能な設計（テスト容易性を重視）です。

---

## 開発・テスト・運用上の注意

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）から探索します。テスト時などに自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の呼び出しはリトライやフェイルセーフを実装していますが、API 利用料やレート制限には注意してください。テスト時は _call_openai_api をモックする設計です。
- J-Quants API 呼び出しは内部でレートリミッタとリトライを入れています。id_token の自動リフレッシュをサポートします。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン依存の留意点（コード内でガードしています）。
- 本ライブラリ単体は「発注」機能の実行エクスポートを含みますが、実際に売買を実行する際はリスク管理とバックテストを十分に行ってください。KABUSYS_ENV による環境（paper_trading / live）の設定を活用してください。

---

この README はプロジェクト内の docstring とモジュール構成に基づいて作成しました。より詳しい仕様（API レートや SQL スキーマ、運用フロー等）はソースコードの各モジュールの docstring を参照してください。質問や追加のドキュメント化が必要であれば教えてください。