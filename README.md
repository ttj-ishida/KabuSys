# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J‑Quants）、ETL、ニュースNLP、レジーム判定、リサーチ用ファクター計算、監査ログなどのユーティリティを提供します。

- 開発フェーズ: 初期版（v0.1.0）
- 対象: DuckDB を用いたローカルデータプラットフォーム、OpenAI によるニュース NLP、J‑Quants API 経由の市場データ取得

---

## 主な機能

- 環境変数 / .env 自動読み込みと設定管理（kabusys.config）
- J‑Quants API クライアント（取得・保存・認証・レート制御・リトライ）: kabusys.data.jquants_client
- ETL パイプライン（市場カレンダー、日足、財務データ、品質チェック）: kabusys.data.pipeline
- データ品質チェック（欠損・スパイク・重複・日付不整合）: kabusys.data.quality
- ニュース収集（RSS）と前処理、raw_news への保存: kabusys.data.news_collector
- ニュース NLP（OpenAI）による銘柄別センチメントスコア生成: kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）: kabusys.ai.regime_detector.score_regime
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）: kabusys.research.*
- 監査ログ（signal → order_request → executions）テーブル初期化ユーティリティ: kabusys.data.audit

---

## 動作要件（推奨）

- Python 3.10+
- 依存パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J‑Quants API、OpenAI、RSS フィード）

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトフォルダに移動

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   あるいはプロジェクトの依存ファイルがあれば:
   - pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN … J‑Quants のリフレッシュトークン
   - KABU_API_PASSWORD …… kabu ステーション API のパスワード（発注等で使用）
   - SLACK_BOT_TOKEN … Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID … 通知先 Slack チャネル ID
   - OPENAI_API_KEY … OpenAI API を利用する場合に必要（score_news / score_regime）
   - （任意）DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

   簡易的な .env.example:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下はライブラリを利用する上での典型的なコードスニペットです。

- 設定にアクセスする
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV == 'live' で True
```

- DuckDB 接続を作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn: duckdb connection を用意しておく
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄別スコア）を実行
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すことも、環境変数 OPENAI_API_KEY を使うことも可
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定を実行
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（別 DB を利用する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル初期化済みの接続を返す
```

- リサーチ用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## 環境変数と設定の挙動

- 自動 .env ロード
  - 自動的にプロジェクトルート（.git または pyproject.toml を探索）を検出し、優先順位は:
    1. OS 環境変数
    2. .env.local
    3. .env
  - テストや特別な状況で自動ロードを無効化する場合:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

- Settings API
  - kabusys.config.settings 経由で各種設定を取得できます（プロパティとして公開）。
  - KABUSYS_ENV の許容値: development / paper_trading / live
  - LOG_LEVEL の許容値: DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## ディレクトリ構成（抜粋）

プロジェクト主要モジュール（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J‑Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン / run_daily_etl
    - etl.py                        — ETLResult の公開
    - news_collector.py             — RSS 収集・前処理
    - calendar_management.py        — マーケットカレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore など）
    - audit.py                      — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラ/バリュー計算
    - feature_exploration.py        — 将来リターン・IC 等
  - research/（その他ファイル）
  - ... その他モジュール（strategy, execution, monitoring などをエクスポート予定）

各モジュールはドキュメンテーションコメント（docstring）を含み、関数の引数・戻り値・例外動作が明記されています。

---

## 注意点 / 設計方針（抜粋）

- Look-ahead bias 対策が各所に組み込まれています:
  - target_date の扱いにおいて datetime.today() を直接参照しない
  - データ取得 / 計算において過去データのみ参照する条件が適用
- ETL・API 呼び出しはフォールトトレラント:
  - API の一時エラーや JSON 解析エラー時は適切にロギングしフェイルセーフ動作（ゼロ埋めやスキップ）する実装が多くあります
- DuckDB への保存は冪等（ON CONFLICT）で行われます
- ニュース RSS 収集は SSRF・XML インジェクション・Gzip Bomb 対策が一部実装済み

---

## 開発・運用に関する補足

- ロギング: 各モジュールで logger を使用。LOG_LEVEL で出力レベルを制御可能。
- テスト: モジュールは外部呼び出し箇所（OpenAI 呼び出し、HTTP リクエスト等）を差し替え可能な設計（テスト時にはモックを利用）。
- 発注関連（kabu ステーション等）は別モジュール（execution）で扱われる想定。実際の発注は live 環境での注意が必要。

---

## 参考（よく使う API）

- kabusys.config.settings — 各種設定の取得
- kabusys.data.pipeline.run_daily_etl — 日次 ETL（メイン入り口）
- kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes — J‑Quants の取得・保存
- kabusys.ai.news_nlp.score_news — ニュース NLP による ai_scores 生成
- kabusys.ai.regime_detector.score_regime — 市場レジームの判定・保存
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログ初期化

---

README に記載のないユーティリティや詳細については、各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、README を拡張して例や運用手順（cron ジョブ / CI 設定 / Slack 通知フロー等）を追加します。