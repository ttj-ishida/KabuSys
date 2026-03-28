# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ）です。  
データETL、ニュースの NLP スコアリング、ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定など、アルゴリズム取引の上流〜中流処理に必要な機能群を提供します。

主な設計思想
- DuckDB を中心としたローカルデータ格納（look-ahead bias に配慮）
- J-Quants API 等からの差分 ETL（レート制限・リトライ・トークンリフレッシュ対応）
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価（JSON Mode を想定）
- 監査ログ（signal → order_request → execution）を永続化してフローを追跡可能にする
- テスト容易性と安全性（SSRF 対策、XML 脆弱性対策、環境自動ロード等）

---

## 機能一覧

- data
  - ETL パイプライン（株価、財務、マーケットカレンダーの差分取得・保存）
  - J-Quants クライアント（認証 / ページネーション / 保存関数）
  - ニュース収集（RSS、SSRF 対策、前処理、raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev/trading days）
  - 監査ログ（監査テーブル作成、監査専用 DB 初期化）
  - 汎用統計ユーティリティ（Zスコア正規化等）
- ai
  - news_nlp: ニュースを銘柄ごとに集約し LLM でセンチメントを評価、ai_scores テーブルへ保存
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して日次で市場レジーム判定
- research
  - factor_calculation（モメンタム / ボラティリティ / バリュー）
  - feature_exploration（将来リターン計算、IC、統計サマリー）
- config
  - 環境変数の自動読み込み（.env / .env.local をプロジェクトルートから読み込み）
  - settings オブジェクトで構成値を提供

主な特徴
- DuckDB を使ったローカル分析・ETL（挿入は冪等な INSERT ... ON CONFLICT）
- OpenAI 呼び出しに対する冗長性（リトライ、バリデーション、JSON モード処理）
- Look-ahead bias を避ける設計（関数は明示的な target_date を受け取り、date.today() を参照しない部分が多い）

---

## 必要条件 / 依存関係（代表）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK; モジュールは API 呼び出しで使用)
- defusedxml
- （標準ライブラリで多くを実装しているため、上記が主要パッケージになります）

projects に requirements.txt がある場合はそれを使用してください。例:
pip install -r requirements.txt

なければ最低限:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. ソースをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install -r requirements.txt
   または最低限:
   pip install duckdb openai defusedxml

4. パッケージのインストール（開発モード推奨）
   pip install -e .

5. 環境変数 / .env の準備
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。  
   必要な主要環境変数（抜粋）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（環境切替）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   .env の書式は shell 形式（KEY=value、export KEY=val にも対応、コメント行は # で可）。詳細は kabusys.config の自動ロード実装をご参照ください。

---

## 使い方（簡単な例）

以下は Python スニペット例です。プロジェクト内部に CLI は用意していないため、スクリプトや scheduler（cron 等）から直接関数を呼び出します。

- DuckDB 接続の作成（デフォルトの DB パスを使用する場合）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL（株価 / 財務 / カレンダー / 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DB の初期化（監査専用の DuckDB を作る）
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn は初期化済みの DuckDB 接続を返す
```

注意点
- ai モジュールは OpenAI の API キー（OPENAI_API_KEY）を参照します。api_key を明示的に渡すことも可能です。
- 多くの関数は target_date を明示的に受け取り、ルックアヘッドバイアスを避ける設計になっています。バックテスト用途でもこの点に留意してください。

---

## 設定挙動の補足

- 環境変数の自動ロードは kabusys.config がプロジェクトルートから `.env` / `.env.local` を読み込みます。OS 環境変数は優先され、.env.local は .env を上書きします。
- テスト・開発で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings で値が必須のものは未設定時に ValueError を投げます（早期検出）。

---

## ディレクトリ構成（要約）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP / ai_scores 書き込み
  - regime_detector.py           — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETLResult の再エクスポート
  - news_collector.py            — RSS 収集・前処理
  - calendar_management.py       — マーケットカレンダー管理
  - quality.py                   — データ品質チェック
  - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                     — 監査ログテーブル初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py           — モメンタム / ボラティリティ / バリュー
  - feature_exploration.py       — 将来リターン / IC / サマリー
- research/*, ai/* 等が提供する高レベル API を import して使います

（上記は主要モジュールを抜粋した構成です。実際のリポジトリにはさらに補助モジュールやテスト等が含まれる場合があります）

---

## 開発 / テストに関するメモ

- 単体テストでは外部 API 呼び出しをモックすることを想定しています（例: kabusys.ai.news_nlp._call_openai_api を patch、kabusys.data.news_collector._urlopen を patch 等）。
- 自動環境変数読み込みはテストの副作用となる場合があるため、必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。
- DuckDB のバージョン依存（executemany の空リスト等）に注意した実装箇所があります。CI 環境の DuckDB バージョンを統一すると安定します。

---

必要があれば、README にサンプル .env.example、requirements.txt の具体例、cron / systemd タスクのサンプル、ETL の運用手順（ログ管理 / 再実行方法）などを追加で作成します。どの情報を優先して追加しますか？