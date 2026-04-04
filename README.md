# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。J-Quants や RSS、OpenAI（LLM）を活用したデータ ETL、ニュース NLP、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日時は呼び出し側で与える）
- DuckDB を中心としたローカル DB ベースの ETL/分析
- 外部 API 呼び出しに対してリトライ・レートリミット対策を実装
- 冪等性を重視（DB 保存は ON CONFLICT / INSERT/DELETE の扱い）

---

## 機能一覧

- データ収集 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、マーケットカレンダーを差分取得・保存
  - RSS によるニュース収集（SSRF対策、トラッキングパラメータ除去）
  - ETL パイプライン（差分取得・保存・品質チェック）
- ニュース NPL / LLM
  - 銘柄別ニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores に保存（score_news）
  - マクロニュースと ETF (1321) の MA200 乖離を合成して市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON モード + リトライ・フォールバック有り
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損、重複、スパイク、将来日付・非営業日の検出
- カレンダー管理
  - JPX 市場カレンダーの DB 管理、営業日判定・前後営業日の取得
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティ用テーブル定義・初期化ユーティリティ

---

## 依存関係（主な Python パッケージ）

- python >= 3.10（型注釈で union | を利用）
- duckdb
- openai
- defusedxml

（その他標準ライブラリで実装している部分が多いです。setup.py/pyproject.toml を参照して下さい）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repository-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. パッケージのインストール
   - pip install -e .[dev]  （プロジェクトが editable インストール可能な場合）
   - または最低限:
     - pip install duckdb openai defusedxml

4. 環境変数の準備
   - プロジェクトルートの `.env`（または `.env.local`）に必要なキーを設定します。
   - 自動でルートの .env を読み込む仕組みがあります（CWD に依存しない探索）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（またはよく使う）環境変数の例：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリングを行う場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系機能を使う場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite ファイルパス（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV: development | paper_trading | live

例 .env:
    JQUANTS_REFRESH_TOKEN=xxxx
    OPENAI_API_KEY=sk-xxxx
    DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡単なコード例）

以下はライブラリ関数を直接呼ぶ例です。各関数は DuckDB 接続を受け取る形です（Look-ahead を避けるため target_date を明示する設計）。

- DuckDB 接続の作成（設定経由でパス取得）:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（カレンダー・株価・財務・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

today = date(2026, 3, 20)  # 実行対象日を明示
result = run_daily_etl(conn, target_date=today)
print(result.to_dict())
```

- ニュースの AI スコアリング（score_news）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

target = date(2026, 3, 20)
n_written = score_news(conn, target_date=target, api_key=None)  # None → 環境変数 OPENAI_API_KEY を使用
print(f"written {n_written} ai_scores")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

target = date(2026, 3, 20)
score_regime(conn, target_date=target, api_key=None)
```

- 監査ログ DB の初期化（監査用専用 DB を作る場合）:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って監査テーブルへ書き込めます
```

注意点：
- 各 AI 呼び出しは OpenAI API キー（api_key 引数、または環境変数 OPENAI_API_KEY）を必要とします。未設定だと ValueError が出ます。
- 関数群は内部で datetime.today() を参照しない設計です（必ず target_date を与えるか、run_daily_etl のように呼び出し側が日付を決めます）。バックテストや再現性のためこの仕様を守ってください。

---

## 設定と自動 .env 読み込み

- 実行時、`kabusys.config` はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数（優先）→ .env → .env.local（.env.local で上書き）
  - テストや明示的な制御のため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードは無効になります。

- 環境変数の必須チェックは `kabusys.config.Settings` のプロパティで行われます。未設定の必須値（例: JQUANTS_REFRESH_TOKEN）を参照した場合は ValueError が発生します。

---

## 主要 API の挙動メモ

- J-Quants クライアントはレートリミット（120 req/min）を内部で守り、再試行（指数バックオフ）、401 時はトークン自動リフレッシュを行います。
- OpenAI 呼び出しは JSON Mode を使い、429/ネットワーク/タイムアウト/5xx に対するリトライとフォールバック（失敗時は中立スコア 0.0）を実装しています。
- ETL 保存処理は冪等（ON CONFLICT DO UPDATE）を意識して実装されています。
- ニュース収集は SSRF 対策・トラッキング除去・最大レスポンスサイズ制限などを行います。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings 定義（J-Quants / OpenAI / DB パス等）
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄別ニュースの LLM スコアリング（score_news）
    - regime_detector.py
      - ETF とマクロニュースを合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - 日次 ETL の実装（run_daily_etl, run_prices_etl, ...）および ETLResult
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付整合性）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログスキーマ定義・初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数 等

（上記は主要モジュールの概要です。各モジュール内にさらに詳細な関数・ユーティリティが実装されています。）

---

## 注意事項・運用上のヒント

- 本ライブラリは外部 API（J-Quants, OpenAI）と連携します。API キーの管理、利用制限、コストに注意してください。
- テストやデバッグ時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、明示的に環境変数を注入することで動作を制御できます。
- OpenAI 呼び出しはレスポンス形式やモデル仕様の変化により挙動が変わる可能性があります。レスポンスのバリデーションは実装されていますが、モデルの更新には注意してください。
- DuckDB のバージョン差異が影響する箇所（executemany の空リスト等）に対して既知の回避策が実装されていますが、環境によっては注意が必要です。

---

この README はコードベースの主要な使い方・設計意図をまとめたものです。詳細な API ドキュメントや実行スクリプトは各モジュールの docstring を参照してください。必要であれば、導入手順の具体的なスクリプトやサンプルワークフロー（cron/job で ETL を回す例等）を追加で作成します。