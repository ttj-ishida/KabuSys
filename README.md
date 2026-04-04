# KabuSys

日本株向けの自動売買・データ基盤ライブラリ兼ツール群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLPによる銘柄センチメント評価、マーケットレジーム判定、監査ログ（発注/約定トレーサビリティ）、リサーチ（ファクター計算）などを含みます。

主な設計方針：
- ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB をデータ基盤として使用（ローカルファイルまたはインメモリ）
- API 呼び出しはリトライ・レート制御・フェイルセーフ機構を備える
- ニュース収集は SSRF / XML 攻撃 / 大量レスポンスなどの安全対策を実装
- 監査ログは冪等性・トレーサビリティ重視（UUID ベース連鎖）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - 設定値は `kabusys.config.settings` から取得
- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー、上場銘柄情報）
  - 差分取得・ページネーション対応・トークン自動リフレッシュ・レート制御
  - ETL パイプライン（calendar / prices / financials の差分取得、品質チェック）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合チェック
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF / プライベートアドレス対策、XML サニタイズ、レスポンスサイズ制限
- ニュースNLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini）に送りセンチメントを算出し ai_scores に保存
  - チャンク処理、バッチ/リトライ、レスポンス検証
- 市場レジーム判定（AI + 指標）
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントを合成して日次レジーム（bull/neutral/bear）を算出
- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 監査ログ（audit）
  - signal_events, order_requests, executions など監査用テーブルの初期化・管理
  - すべて UTC タイムスタンプ、冪等性・索引定義済み

---

## 動作要件（主な依存）

- Python >= 3.10（PEP 604 の union 型（|）などを使用）
- duckdb
- openai (OpenAI Python SDK v1系想定)
- defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

簡単な例（pip で個別にインストール）:
```bash
pip install duckdb openai defusedxml
```

プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを取得
2. 依存パッケージをインストール（上の例参照）
3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を作成して設定可能。自動ロードはデフォルトで有効。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETL 用）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 使い方（基本例）

以下は Python REPL やスクリプトから呼び出す例です。

- 設定値を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作成する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（特定日分の ai_scores を生成）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使用して監査テーブルへ書き込み
```

- リサーチ（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(records[:5])
```

ログレベルや挙動は環境変数（LOG_LEVEL, KABUSYS_ENV 等）で調整してください。

---

## 注意点 / 実運用上のポイント

- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必須です。API 呼び出しは挙動をリトライ・フェイルセーフ（失敗時はスコア 0 で継続）していますが、コストやレートに注意してください。
- J-Quants API にはレート制限があるため、ETL は RateLimiter を使用して間隔調整します。ID トークンの自動リフレッシュ・リトライも実装済みです。
- ニュース収集は外部 URL を扱うため SSRF 対策（プライベートIPブロック、リダイレクト検査）や XML の安全パース（defusedxml）を行っています。
- データ品質チェックの結果（QualityIssue）は ETL の結果として返されるため、自動運用時は alerts / monitoring と連携してください。
- DuckDB のバージョン差異により executemany の挙動などが影響する箇所があるため、動作確認したバージョンで運用してください。

---

## ディレクトリ構成

主要なファイル / モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースNLP（銘柄スコア）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL 結果クラス公開
    - calendar_management.py — マーケットカレンダー管理
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ
    - audit.py               — 監査ログ（テーブル初期化）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/*               — リサーチ用ユーティリティ群
- pyproject.toml（想定）
- .env.example（推奨で用意）

各モジュールは docstring と設計方針コメントが豊富に記載されており、用途ごとに分離された構成です。

---

## 開発 / 貢献

- コードのスタイルは PEP8 準拠を前提にしてください。
- テストはユニットレベルで API 呼び出し等はモックすること（news_nlp/regime_detector の _call_openai_api などは差し替え可能に設計済み）。
- .env などの秘密情報は Git に含めないでください。CI / 本番ではシークレット管理システムを利用してください。

---

必要であれば、README に具体的な .env.example のテンプレート、docker-compose の設定例、CI / systemd サービス用の起動例、または各 API 用のサンプルスクリプト（バッチ実行、監視）を追加します。どれを優先して追加しますか？