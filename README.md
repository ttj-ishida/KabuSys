# KabuSys

日本株向けの自動売買 / データパイプライン用ライブラリ群です。  
ETL（J-Quants）・ニュース収集＆NLP（OpenAI）・ファクター計算・市場レジーム判定・監査ログ等を含む、研究〜運用までの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を用いた銘柄毎のニュースセンチメント評価（ai_scores）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントの合成）
- ファクター（モメンタム・バリュー・ボラティリティ等）計算およびリサーチ用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / execution）用 DuckDB スキーマと初期化ユーティリティ
- 環境設定の自動読み込み（.env / .env.local）と集中管理

主な設計方針として、ルックアヘッドバイアス回避・冪等性（DB 保存の ON CONFLICT）・フェイルセーフ（外部 API 失敗時は処理を継続）を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch / save（差分取得・ページネーション・認証・レート制御）
  - カレンダー管理: 営業日判定 / next/prev trading day / calendar_update_job
  - ニュース収集: RSS 取得・正規化・SSRF 対応・前処理・DB 保存
  - データ品質チェック: 欠損 / スパイク / 重複 / 日付不整合
  - 監査（audit）: 監査テーブル DDL / インデックス / 初期化ユーティリティ
  - 統計ユーティリティ: zscore_normalize
- ai
  - ニュース NLP: score_news（OpenAI を用いた銘柄毎センチメント）
  - レジーム判定: score_regime（ETF MA200 と LLM マクロセンチメントを合成）
- research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラス: 環境変数の集中管理、.env 自動読み込みロジック（.env / .env.local 優先順）

---

## セットアップ手順

前提
- Python 3.10 以上（型注記に | を用いているため）
- duckdb, openai, defusedxml 等の依存ライブラリ

1. リポジトリをクローン / ソース配置
   - 例: git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限:
     - pip install duckdb openai defusedxml
   - 推奨（開発用）:
     - pip install pytest black isort など（プロジェクトに合わせて）

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると、自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   推奨される最低限の .env 例 (.env.example):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   OPENAI_API_KEY=your_openai_api_key
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 説明:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須運用時）
     - OPENAI_API_KEY: OpenAI 呼び出しに必要（score_news / score_regime を使う場合）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - そのほかデータベースパスや監視閾値等は Settings で確認できます

---

## 使い方（サンプル）

以下は典型的な利用例です。DuckDB 接続を生成してモジュール関数を呼びます。

- ETL（日次パイプライン）の実行例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコア付与:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
print(f"written {written} codes")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 環境設定参照例:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

ログレベルや KABUSYS_ENV により動作（本番/ペーパー/開発）や出力が変わります。

---

## 主要な環境変数

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for kabu integration) — kabu ステーション API のパスワード
- OPENAI_API_KEY — OpenAI クライアント（score_news, score_regime）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログ出力レベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

Settings クラスにプロジェクト内で参照される全設定プロパティがあります（src/kabusys/config.py を参照）。

---

## ディレクトリ構成

概観（主要ファイルのみ抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント集計・OpenAI 呼び出し
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロ NLP）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント / 保存ロジック
    - pipeline.py              — ETL パイプライン / run_daily_etl
    - calendar_management.py   — 市場カレンダー管理・営業日判定
    - news_collector.py        — RSS 取得・前処理・保存
    - quality.py               — データ品質チェック
    - stats.py                 — zscore_normalize 等の汎用統計
    - audit.py                 — 監査テーブル定義・初期化（signal/order/execution）
    - etl.py                   — ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py       — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   — calc_forward_returns / calc_ic / factor_summary / rank

各モジュールは責務を分離しており、研究用途（research）と運用用途（data / ai）を分けて利用できます。

---

## 注意点・運用メモ

- Python バージョンは 3.10 以上を推奨（型注記で PEP 604 の | を使用）。
- OpenAI の呼び出しはレスポンス検証とリトライを実装していますが、API キーのレート制限・課金には注意してください。
- J-Quants API はレート制限があり、jquants_client は固定間隔の RateLimiter を使用しています。長時間バッチ実行時はこの点を考慮してください。
- DuckDB に対する executemany の挙動（空リスト不可など）をコード内で考慮しています。DuckDB バージョンの違いに注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から行います。CI／テスト時は環境変数で制御するか KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 外部ネットワーク取得（RSS）では SSRF 対策、コンテンツサイズ上限、defusedxml による XML セキュリティ対策を実装していますが、運用時のソース追加は慎重に行ってください。

---

## 貢献 / 開発

- コードを変更・追加する際は単体での関数テストを推奨します（外部 API 呼び出しはモック化）。
- OpenAI / J-Quants 呼び出し箇所はリトライや例外処理を持っているため、テストでは各 _call_* 関数を patch/モックすることを想定しています。
- 監査スキーマや ETL の DDL/DDL 実行は冪等に設計されています。初期化ユーティリティを利用して DB を作成してください。

---

この README はリポジトリ内の docstring / モジュール実装（src/kabusys 以下）に基づいて作成しています。必要であれば、導入手順（requirements.txt / Dockerfile / systemd unit 等）のテンプレートも追加できます。必要な場合は実行環境や想定ワークフロー（バッチ/常駐/コンテナ）を教えてください。