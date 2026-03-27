# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・LLM ベースの NLP スコアリング、ファクター計算、監査ログなどを提供します。

※ 本 README はパッケージ内の実装（src/kabusys 以下）をもとに要点を日本語でまとめたものです。

---

## 主要な機能

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS からニュースを収集し raw_news / news_symbols に保存
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロセンチメントを重み付け合成して 'bull'/'neutral'/'bear' を判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン計算・IC（Information Coefficient）や統計サマリー
- 監査（トレーサビリティ）
  - signal_events / order_requests / executions など監査テーブルの初期化・管理
  - order_request_id による冪等制御
- 設定管理
  - .env / .env.local / 環境変数から設定自動ロード（プロジェクトルート検出）

---

## 必須（および主要）環境変数

設定は環境変数またはルートの `.env` / `.env.local` から自動ロードされます（無効化可: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

主要なキー（Settings クラス参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（省略時: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（省略時: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI 呼び出し時に使用）

例（`.env`）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（代表例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、環境変数を直接設定します。

   自動ロードは、package の config モジュールが .git または pyproject.toml を探索してプロジェクトルートを決定します。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB 初期スキーマ等
   - ETL / audit 初期化時に必要なテーブルを作成する関数を呼ぶことで初期化されます（例を参照）。

---

## 使い方（代表的な API / 実行例）

以下は Python REPL やスクリプトから利用する際の簡単な例です。OpenAI 呼び出しを行う関数は `api_key` 引数を直接渡すか、環境変数 `OPENAI_API_KEY` を設定してください。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None で今日
print(result.to_dict())
```

- ニュース NLP スコア（ai_scores へ書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB 初期化（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit_duckdb.duckdb"))
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- レポジトリ内のログレベルや環境を設定する:
  - 環境変数 `LOG_LEVEL` / `KABUSYS_ENV` を設定して挙動を制御します（`settings` 経由で参照）。

注意点:
- 各 ETL / AI 関数はルックアヘッドバイアスを避けるため内部で date.today() を無闘用せず、外部から `target_date` を与える設計になっています（バックテスト用に重要）。
- OpenAI 呼び出しはネットワーク・API エラー時にフォールバック／リトライロジックがありますが、API キーがなければ ValueError を投げます。テスト時は内部の _call_openai_api をモック可能です。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数 / 設定管理（.env 自動ロード・Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析（OpenAI JSON Mode）
  - regime_detector.py — ETF MA とマクロセンチメントを合成した市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダーの判定・更新ロジック
  - etl.py — ETL インターフェース再エクスポート
  - pipeline.py — 日次 ETL パイプライン（prices/financials/calendar + 品質チェック）
  - stats.py — zscore など統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログテーブル定義・初期化 utilities
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
  - news_collector.py — RSS 収集、前処理、SSRF 対策、DB 保存
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリューの計算
  - feature_exploration.py — 将来リターン, IC, 統計サマリー 等
- monitoring / execution / strategy / (他のモジュール群) — メインの戦略・実行・監視（プロジェクト拡張領域）

---

## 実運用上の注意

- 本ライブラリは実際の発注を含む環境（kabu API 等）と連携するため、本番環境での利用時は十分に検証してください。`KABUSYS_ENV` を `paper_trading` に設定してペーパートレードで動作検証することを推奨します。
- OpenAI / J-Quants の API キーは適切に保護し、ログやリポジトリに平文で保存しないでください。
- DuckDB ファイルはバックアップ・アクセス制御を検討してください（監査ログ等は削除しない前提）。
- news_collector は外部 HTTP を扱うため SSRF 対策やレスポンスサイズ上限、XML パースの安全対策（defusedxml）を組み込んでいますが、実行環境のプロキシ等も含め十分に監視してください。

---

## 開発 / テスト

- 各モジュールは外部依存（OpenAI, J-Quants API, ネットワーク）を注入可能な設計（例: api_key 引数、モック化ポイント）になっています。ユニットテストでは外部呼び出し関数（_call_openai_api、_urlopen、jquants_client._request 等）をモックしてください。
- ローカル開発では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効にするとテストが安定します。

---

必要であれば README にサンプルスクリプト、より詳しい設定（例えば DuckDB スキーマ初期化スクリプトや crontab / Airflow 用の実行例）、および各モジュールの API ドキュメント（関数シグネチャや戻り値の詳細）も追加できます。どの部分を拡張したいか教えてください。