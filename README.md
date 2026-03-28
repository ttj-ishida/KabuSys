# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ取得、DuckDB による ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ファクター研究・特徴量解析、監査ログ（発注・約定トレーサビリティ）などを提供します。

主に内部で使うモジュール群をまとめたライブラリで、バッチ ETL や研究用途、AI を使ったニュース解析やレジーム判定を行えます。

---

## 主要機能一覧

- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得・DuckDB に保存（冪等）
  - 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS からニュース取得（SSRF 対策・トラッキング除去）と raw_news 保存ロジック
  - OpenAI を使ったニュースごとのセンチメント評価（score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、Zスコア正規化等
- 監査ログ（オーダー・約定）
  - signal_events / order_requests / executions の DDL と初期化関数（init_audit_schema, init_audit_db）
  - 発注フローを UUID ベースでトレース可能にする監査設計
- 設定管理
  - .env（プロジェクトルートの .env / .env.local）自動ロードと Settings オブジェクト経由の取得

設計上の注意点（抜粋）
- ルックアヘッドバイアス対策：多くのモジュールが date 引数を受け入れ、datetime.today() を直接参照しない設計
- 冪等性：DB 保存は ON CONFLICT / DELETE→INSERT 等で冪等化
- フェイルセーフ：外部 API の失敗は多くの場合フォールバック値を使って処理継続

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS）

依存関係はプロジェクトの配布方法に合わせて requirements.txt や pyproject.toml に記載してください。

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）
2. 仮想環境作成・アクティベート（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

4. 環境変数を設定
   - プロジェクトルート（.git もしくは pyproject.toml のあるディレクトリ）に `.env`、あるいは環境変数で設定します。
   - 自動ロードはデフォルトで有効。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

推奨される .env の例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 主要な環境変数（Settings）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABUSYS_ENV — one of: development, paper_trading, live (デフォルト: development)
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)
- OPENAI_API_KEY — OpenAI API キー（AI を使う機能で必要）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

設定はライブラリ内で `from kabusys.config import settings` を使って取得できます。

---

## 使い方（代表的な例）

以下は簡単な Python 例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る（デフォルトパスは settings.duckdb_path）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl

# target_date を省略すると今日が対象（内部では trading day に調整される）
result = run_daily_etl(conn)  # ETLResult を返す
print(result.to_dict())
```

- ニュース NLP スコアを算出して ai_scores テーブルへ書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは OPENAI_API_KEY 環境変数か api_key 引数で指定
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化（監査ログ用 DB を別途用意したい場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
```

- 研究用：ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

- 設定参照例:
```python
from kabusys.config import settings
print(settings.env, settings.log_level, settings.duckdb_path)
```

注: 各関数は DuckDB の特定テーブル（例: raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）を参照・更新します。事前にスキーマ作成や初期データのロードが必要です。

---

## 実装上のポイント / 備考

- 多くの関数は「ルックアヘッドバイアス」を避けるため、明示的な target_date 引数を取る設計になっています。テストやバッチ処理では必ず日付を固定して使うことが推奨されます。
- 外部 API 呼び出し（J-Quants / OpenAI）はリトライやバックオフ、401 リフレッシュなどの堅牢な制御が実装されていますが、API キーやレート制限に注意してください。
- news_collector は RSS の取り扱いで SSRF 対策や圧縮サイズチェック、トラッキング除去など安全性に配慮しています。
- ETL の保存処理は冪等化されているため、同一データの再投入で上書きされます（ON CONFLICT 等）。
- データ品質チェック（quality.run_all_checks）は ETL 後に実行して問題を検出可能です。重大な品質問題は ETLResult に反映されます。

---

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py — 市場レジーム判定ロジック
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — JPX カレンダー管理・営業日ロジック
    - stats.py — 汎用統計ユーティリティ（Zスコア正規化 等）
    - quality.py — データ品質チェック
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存ユーティリティ
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai, data, research 以下に細かい関数群が収まっています

---

## ライセンス / 注意事項

- 本リポジトリは金融・取引に関するロジックを含みます。実際の売買や資金投入を行う場合は十分なテストとリスク管理を実施してください。
- OpenAI / J-Quants 等の外部 API 利用に関しては各サービスの利用規約・料金体系を遵守してください。

---

必要に応じて README を拡張して、セットアップ用の requirements.txt やデータベース初期スキーマ作成手順、運用スケジュール（cron／Airflow など）や Slack 通知の使用例を追加できます。必要があれば追記します。