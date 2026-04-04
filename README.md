# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、売買パイプラインおよびリサーチ用途のユーティリティを提供します。

---

## 主要機能（抜粋）

- データ ETL（J-Quants）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ニュース収集と NLP（OpenAI）
  - RSS からの安全なニュース収集（SSRF 対策、トラッキング除去）
  - ニュースを銘柄ごとに集約し LLM でセンチメント（ai_scores）生成
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを組み合わせて日次で判定
- ファクター計算（Research）
  - Momentum / Value / Volatility / Liquidity などの定量ファクター計算
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを担保する監査スキーマ
- 汎用ユーティリティ
  - 統計ユーティリティ（Z スコア正規化）、市場カレンダー管理、DuckDB 初期化等

---

## 必要環境 / 依存パッケージ

- Python 3.10+
- 主な依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある想定でインストールしてください。簡易例:）
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / 設定

設定は環境変数かプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはデフォルトで有効です（CWD ではなくパッケージ位置からプロジェクトルート（.git / pyproject.toml）を探索します）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants（必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- kabu ステーション API
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に使用）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベース / パス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db
- 監視 / PID
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- 動作モード / ログ
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

必須の環境変数が不足していると Settings が ValueError を投げます。

---

## セットアップ手順（最小例）

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存関係インストール
   ```bash
   pip install -r requirements.txt
   # または最低限:
   pip install duckdb openai defusedxml
   ```

4. `.env` を作成（プロジェクトルート）
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. DuckDB 用ディレクトリを作る（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（コード例）

以下は主要なユースケースの最小サンプルです。DuckDB 接続に標準的な duckdb.connect を使用します。

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(__import__('kabusys').config.settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（ai_scores へ書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored", count, "codes")
```

- 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ専用 DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# conn をアプリの監査操作に使用
```

- ファクター計算 / リサーチユーティリティ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

注意:
- score_news / score_regime は OpenAI API へアクセスします。OPENAI_API_KEY を設定するか、api_key 引数にキーを渡してください。
- すべての関数はルックアヘッドバイアスに配慮して実装されています（内部で datetime.today() を直接参照しない等）。

---

## ディレクトリ構成（概要）

（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py : パッケージ定義（バージョン 0.1.0）
  - config.py : 環境変数 / 設定管理（自動 .env 読込、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py : ニュースセンチメントスコア生成（score_news）
    - regime_detector.py : ETF MA とマクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）
    - etl.py : ETLResult の再公開
    - calendar_management.py : マーケットカレンダーの管理（営業日判定など）
    - news_collector.py : RSS ニュース収集と前処理
    - stats.py : 統計ユーティリティ（zscore_normalize）
    - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py : 監査ログ用スキーマ初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py : Momentum / Value / Volatility 等
    - feature_exploration.py : 将来リターン / IC / 統計サマリ等

各モジュールはドキュメント文字列（docstring）に設計方針と処理フローが記載されています。プロジェクトの機能はサブモジュールごとに分離され、DB（DuckDB）接続を引数に取ることで副作用を最小化しています。

---

## 運用上の注意

- OpenAI 呼び出しにはレート制限とエラーハンドリング（リトライ）が組み込まれているものの、コストやレートには注意してください。
- J-Quants API はレート制限があるため、jq クライアントは固定間隔スロットリングを実装しています。複数インスタンスで同時実行する場合は考慮が必要です。
- データ品質チェック（quality）により重大な問題が検出された場合は ETLResult.has_quality_errors を確認して適切に対処してください。
- 監査ログは削除しない前提で設計されています。スキーマ変更時の互換性に注意してください。

---

## 開発 / テスト

- モジュール内部ではテスト容易性のために外部呼び出し（OpenAI / urllib 等）をラップしており、ユニットテストでは該当関数をモックして差し替え可能です（例: news_nlp._call_openai_api の patch）。
- 自動 .env 読込を無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストの際に便利です）。

---

問題報告・コントリビュート、API 仕様の補足が必要でしたら、どの部分を掘り下げたいか教えてください。README の追加セクション（例: API の詳細、サンプル .env.example、運用手順）も作成可能です。