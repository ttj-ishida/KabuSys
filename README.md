# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。J-Quants / JPX / RSS / OpenAI を組み合わせて、データ ETL、ニュース NLP（AI ベースのセンチメント）、市場レジーム判定、ファクター計算、監査ログスキーマなどを提供します。

## 概要

KabuSys は以下の目的を持つモジュール群を含みます。

- データ取得・ETL（J-Quants） → DuckDB へ保存、品質チェック
- ニュース収集・前処理（RSS）と LLM を使った銘柄単位センチメントスコア化
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- ファクター計算 / 研究用ユーティリティ（モメンタム、バリュー、ボラティリティ、IC 等）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ用スキーマ初期化）
- 環境設定管理（.env 自動読み込み、settings オブジェクト）

設計方針としては、バックテストや本番運用での「ルックアヘッドバイアス回避」を重視し、DB クエリは target_date 未満／以前のみ参照するなどの配慮がなされています。

## 主な機能一覧

- data:
  - ETL パイプライン（日次 ETL: run_daily_etl）
  - J-Quants クライアント（fetch/save の自動レート制限・リトライ・トークンリフレッシュ）
  - market_calendar 管理・営業日判定ユーティリティ
  - news_collector: RSS 収集、前処理、SSRF 対策
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログ用テーブル定義と初期化
  - stats: z-score 正規化など汎用統計
- ai:
  - news_nlp.score_news: 銘柄単位ニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュース LLM を合成して market_regime に保存
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - settings: 環境変数をラップした accessor（JQUANTS_REFRESH_TOKEN などを必須にする）

## セットアップ手順（開発環境）

以下は一般的なセットアップ例です。プロジェクトに requirements.txt / pyproject.toml がある場合はそちらに従ってください。

1. Python（推奨: 3.10+）をインストール
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージのインストール（代表例）
   - pip install duckdb openai defusedxml
   - 他にテスト用モジュールやロギング等が必要であれば追加
4. パッケージを開発インストール（パッケージ化されている想定）
   - pip install -e .

### 環境変数（.env）

プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。`.env.example` を参考に作成してください（リポジトリに例がある前提）。主要なキー:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD — kabu ステーション等の API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視・プロセスマネジメント関連
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

## 使い方（コード例）

以下は主要な機能の簡単な使い方例です。

- DuckDB 接続の作成（settings からパスを取得）
```python
import duckdb
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 19))
print(f"wrote scores for {n_written} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 19))
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は各銘柄ごとの dict のリスト
```

- 監査ログ DB の初期化（監査用専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 市場カレンダーの判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI を呼ぶ関数は API キーが必須です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、内部でガードされています。API をそのまま利用してください。

## ディレクトリ構成（主要ファイル）

下記はリポジトリ内の主要モジュール・ファイルの一覧です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETLResult re-export)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファイル群: factor/feature 関連）
- その他:
  - pyproject.toml / setup.py（プロジェクトルートにある想定）
  - .env.example（存在する場合はこれを参考に .env を作成）

（上記はコードベースの抜粋に基づく表記です。実際のリポジトリでは追加のユーティリティやテスト等が存在する可能性があります。）

## 運用上の注意・ポイント

- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索して行います。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）を守る実装になっています。get_id_token はリフレッシュロジックを内包しています。
- LLM 呼び出し（OpenAI）はレスポンスパース失敗や API エラー時にフェイルセーフでゼロ（中立）にフォールバックする実装が多く、安全性を考慮しています。
- ETL / quality チェックは Fail-Fast ではなく全チェック収集モデルを採用しており、呼び出し元が検出結果に基づきアクションを判断します。
- timestamp は監査 DB で UTC 固定（init_audit_schema で SET TimeZone='UTC' が実行されます）。

## 貢献・テスト

- ユニットテストやモックに対応するよう、外部 API 呼び出しは内部関数へ抽象化されている箇所が多く、テスト時は unittest.mock.patch で差し替え可能です（例: kabusys.ai.news_nlp._call_openai_api のモック等）。
- PR を作成する際は、既存の設計方針（ルックアヘッドバイアス回避、冪等性、フェイルセーフ）を尊重してください。

---

何か特定の章（例: .env.example のテンプレート、より詳しい ETL 実行の CLI 例、依存パッケージの完全なリスト）を README に追記したい場合は教えてください。必要に応じて例やコマンドを追記します。