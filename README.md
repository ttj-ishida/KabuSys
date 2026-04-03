# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータパイプラインと戦略実装に必要な共通機能群をまとめた Python パッケージです。主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存／品質チェック
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント解析（銘柄ごとの ai_score）
- マーケットレジーム判定（ETF とマクロニュースの組合せ）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 監査ログ（signal → order_request → execution）のテーブル定義・初期化

設計上の重要なポイント:
- ルックアヘッドバイアスを排除する（target_date を明示的に渡す設計）
- API 呼び出しに対するリトライ＆フェイルセーフ（OpenAI / J-Quants）
- DuckDB による冪等保存（ON CONFLICT を利用）
- セキュリティ対策（RSS の SSRF 対策等）

---

## 主な機能一覧

- ETL（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分取得・バックフィル・品質チェック（kabusys.data.quality）
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_* / save_*（daily quotes, financial statements, market calendar）
  - レートリミット／リトライ／トークン自動更新
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・raw_news への冪等保存
  - SSRF 対策、応答サイズ制限、ID 生成（URL 正規化＋SHA256）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント（ai_scores へ書き込み）
- レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離 + マクロニュースセンチメントの合成スコア
- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ
- 環境設定（kabusys.config）
  - .env 自動ロード（プロジェクトルート検出）と Settings ラッパー

---

## セットアップ手順（開発環境）

以下は推奨手順の一例です。実際のプロジェクトでは requirements.txt や poetry/poetry.lock を使って依存管理してください。

1. Python 仮想環境を作成して有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   ※実際はプロジェクトで管理している requirements を参照してください。

3. 開発モードでパッケージをインストール（プロジェクトルートにて）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` に設定を書くと自動でロードされます（kabusys.config）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の外部サービス:
- J-Quants（API トークン）
- OpenAI（API キー） — ニュース NLP / regime 判定を使う場合
- kabuステーション API（発注を使う場合）

---

## 必要な環境変数

kabusys.config.Settings で参照される主な環境変数（.env に記載する例）:

- JQUANTS_REFRESH_TOKEN (必須: J-Quants リフレッシュトークン)
- KABU_API_PASSWORD (kabuステーション API 用パスワード)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI を使う場合の API Key)
- LINE_CHANNEL_ACCESS_TOKEN (通知用、任意)
- LINE_USER_ID (通知先、任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 SQLite データベースパス、デフォルト: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

注意:
- .env.local は .env の上書き（優先）で読み込まれます。
- .env ファイルのパースは細かい仕様（export 形式・クォート・コメント）に対応しています。

---

## 使い方（代表的な例）

以下は Python インタープリタやスクリプトから利用する基本例です。

1) DuckDB 接続の作成（例）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 監査 DB を初期化（監査用 DB を別に作る場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db(":memory:")  # またはファイルパス
```

3) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4) ニューススコアリング（OpenAI API キーが必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written", n_written)
```

5) レジーム判定（OpenAI API キーが必要）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

6) リサーチ関数の実行例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

---

## 自動 .env 読み込みの挙動

- パッケージインポート時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を読み込みます。
- 読み込み順（優先度低→高）: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下に存在します）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境設定・.env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント解析（OpenAI）
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント + DuckDB 保存
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - news_collector.py       — RSS ニュース収集
    - quality.py              — データ品質チェック
    - stats.py                — 汎用統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py  — マーケットカレンダー管理（営業日ロジック）
    - audit.py                — 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - ai/..., research/..., data/... (その他補助ファイル)

---

## 注意点 / 運用上のポイント

- OpenAI の呼び出しや外部 API はコストとレート制限があるため、バッチ化・リトライロジックが組み込まれています。運用時は API 料金とレートを確認してください。
- DuckDB を単一ファイルで使う想定ですが、バックアップ・ロック等も考慮した運用が必要です。
- ETL / 研究関数は Look-ahead バイアスを避ける設計になっています。target_date を適切に与えてください。
- news_collector は RSS フィード取得時に SSRF 対策を行っていますが、追加ソースを登録する際は信頼できるフィードを使用してください。

---

## サポート / 貢献

- バグ報告・改善提案は issue を立ててください。
- 新機能はまず設計方針を Issue に記載し、合意ののち Pull Request をお願いします。

---

README はここまでです。必要であれば、インストール用の requirements.txt、CI/CD スクリプト、実行例の Jupyter ノートブック等のテンプレートも追加できます。どの部分を詳細化しましょうか？