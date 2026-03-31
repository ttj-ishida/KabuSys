# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（モジュール群の実装サンプル）。

本リポジトリは、J-Quants などからデータを取得して DuckDB に保存する ETL、ニュースの NLP による銘柄センチメントスコアリング、LLM を用いた市場レジーム判定、研究（ファクター計算）および監査ログ（トレーサビリティ）機能などを提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得 / ETL
  - J-Quants API から株価（日足）・財務・カレンダー等をページネーション・レート制御・リトライ付きで取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）を提供

- ニュース収集 / NLP
  - RSS からニュースを収集して raw_news に保存（SSRF 対策、トラッキング除去、gzip など対応）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）

- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で market_regime を生成（score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリーのユーティリティ

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などを検出する品質チェックモジュール

- 監査ログ（Audit）
  - シグナル → 発注 → 約定のトレースが可能な監査テーブル定義と初期化ユーティリティ（init_audit_db / init_audit_schema）

- 設定管理
  - .env ファイルまたは環境変数から主要設定を自動ロード（.env.local が上書き、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）

---

## 必要環境 / 依存

- Python 3.9+
- 必要な Python パッケージ（代表）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。最小限の依存は上記です。）

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージのインストール

   プロジェクトが PEP 517/518 構成（pyproject.toml）を持つ場合:

   ```
   pip install -U pip
   pip install -e .
   ```

   あるいは最低限の依存のみをインストールする場合:

   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定

   プロジェクトルートに `.env`（およびローカルで上書きしたい場合は `.env.local`）を作成します。必要な環境変数の例:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development          # development | paper_trading | live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   自動ロードを無効にする場合:

   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   （プロジェクトは `.git` または `pyproject.toml` を基にプロジェクトルートを検出し、`.env` / `.env.local` を自動読み込みします。）

---

## 使い方（主要 API 例）

下記は最低限の利用例です。conn は DuckDB の接続オブジェクト（duckdb.connect(...)）を想定します。

- 日次 ETL を実行してデータを取得・保存する

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトパスは settings.duckdb_path
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI APIキーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（1321 の ma200 とマクロニュースを合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB の初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # :memory: も利用可能
# テーブル群が作成されます
```

- 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の mom_1m, mom_3m, mom_6m, ma200_dev 等を含む dict のリスト
```

---

## 重要な設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に必要
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必須）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite パス（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

環境変数が不足している場合、多くの関数は ValueError を出します。README に含める `.env.example` を参考に `.env` を作成してください。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み / Settings クラスを提供（自動 .env ロードの挙動含む）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを LLM で銘柄別にスコアリングして ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA とマクロニュースを合成して market_regime を作成
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py
      - run_daily_etl / 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
      - ETLResult dataclass
    - etl.py
      - ETLResult の再エクスポートインターフェース
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存（SSRF 対策・サイズ制限・トラッキング除去）
    - calendar_management.py
      - market_calendar の判定 / 更新ジョブ / 営業日ユーティリティ
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
      - 将来リターン計算, IC 計算, 統計サマリーなど
  - monitoring/ (本リポジトリ内では sqlite 用 path を設定するためのコードが参照されている；実装は別)
  - その他モジュール群（strategy / execution / monitoring といった名前空間はパッケージ公開に含まれる想定）

---

## 運用上の注意点

- Look-ahead バイアス防止
  - ほとんどの処理は内部で date.today() の利用を避け、引数で target_date を明示的に受け取ります。バックテストや再現性を考慮して利用してください。

- 冪等性・トランザクション
  - ETL / 保存処理は基本的に冪等（ON CONFLICT DO UPDATE）で実装されていますが、部分失敗時の整合性に注意してトランザクション管理を行ってください。

- API レート制限・リトライ
  - J-Quants はレート制限・リトライ、OpenAI もリトライ戦略を持っています。運用時は API キー・コスト・レートに注意してください。

- セキュリティ
  - news_collector は SSRF 対策や XML パースの安全対策（defusedxml）を講じていますが、運用時はファイアウォール・プロキシ設定などネットワーク面の対策も必須です。

---

## 貢献・拡張

- 新しいデータソース・ニュースソースの追加、戦略（strategy）や実行（execution）層の実装、監視 / アラート機能の追加などに拡張できます。
- テスト: モジュールの多くは外部 API 呼び出しを抽象化しているため、ユニットテストではモック差し替えが可能です（例: news_nlp._call_openai_api を patch）。

---

この README はリポジトリ内のコードを元にした概要です。詳細な API 引数や戻り値の仕様は各モジュール（src/kabusys 以下の各ファイル）の docstring を参照してください。補足のドキュメントや pyproject.toml / .env.example を用意している場合はそれも参照してください。