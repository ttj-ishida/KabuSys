# KabuSys

KabuSys は日本株向けのデータプラットフォームと研究・自動売買支援ライブラリです。J-Quants / RSS / OpenAI など外部データを取り込み、DuckDB ベースで ETL、品質チェック、ニュース NLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ管理などを提供します。

このリポジトリはライブラリとして組み込み可能で、ローカル ETL ジョブや研究用スクリプト、戦略コンポーネントの基盤として利用できます。

## 主な特徴（機能一覧）
- データ取得・ETL
  - J-Quants から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（ページネーション・リトライ・レート制御対応）。
  - ETL 結果を表す ETLResult を提供し、品質チェックと併用可能。
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合などを検出して QualityIssue を返す。
- ニュース収集
  - RSS フィードから記事を収集し raw_news / news_symbols に保存（SSRF 対策、トラッキングパラメータ除去、最大サイズ制限）。
- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄別センチメントスコアリング（batch 化、リトライ、JSON モードの検証）。
  - マクロニュースを使った市場レジーム判定（MA200 乖離と LLM センチメントを合成）。
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー、Zスコア正規化等。
- カレンダー管理
  - market_calendar を用いた営業日判定、次/前営業日取得、期間内営業日列挙、JPX カレンダー差分取得バッチ。
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までトレーサビリティを維持する監査スキーマ（DuckDB）を初期化。
- 設定管理
  - .env ファイルまたは環境変数からの設定読み込み（プロジェクトルートを自動検出、読み込み優先度: OS 環境 > .env.local > .env）。自動読み込みは環境変数で無効化可能。

---

## 依存関係（主なライブラリ）
- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

（パッケージ化されていない場合は requirements.txt を作成して管理してください。例: duckdb, openai, defusedxml）

---

## 環境変数 / .env
主要な環境変数（必須は README 内で明示）:

必須（実行する機能に応じて必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注機能を使う場合）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector 等）

その他（デフォルト値あり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定するとパッケージインポート時の自動 .env ロードを無効化

自動ロードについて:
- パッケージの config モジュールはパッケージファイル位置から親ディレクトリに .git または pyproject.toml を探し、プロジェクトルートを特定して .env / .env.local を順に読み込みます。
- テストや CI で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env 例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. Python のインストール（推奨: 3.10 以上）
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージのインストール
   - pip install duckdb openai defusedxml
   - （その他、プロジェクトで必要なパッケージがあれば追加）
4. 本リポジトリをインストール（開発モード）
   - pip install -e .
   （pyproject.toml / setup.cfg がある場合）
5. 環境変数を設定
   - プロジェクトルートに .env または .env.local を配置するか、OS 環境変数で設定
6. DuckDB 用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（サンプル）

以下は主要機能を Python で呼び出す例です。実行する際は必要な環境変数（特に API キー）を設定してください。

- DuckDB 接続を開く（設定に基づくパスを使用）:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース NLP スコアリング（target_date: datetime.date）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print(f"scored {n} symbols")
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（独立 DB を作る場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または in-memory:
# audit_conn = init_audit_db(":memory:")
```

- 研究用ファクター計算:
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- カレンダー関連ユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI API 呼び出しはリトライやフォールバックが実装されていますが、API キーが未設定の場合は ValueError を返します。
- ETL / 保存処理は DuckDB に対して idempotent（ON CONFLICT DO UPDATE）で動作します。
- news_nlp / regime_detector はルックアヘッドバイアスを避けるため、内部で date.today() を直接参照しない設計です（target_date を明示してください）。

---

## トラブルシューティング（よくある問題）
- .env が読み込まれない:
  - パッケージはプロジェクトルートを .git または pyproject.toml で検出します。ルートが見つからない場合は自動ロードをスキップします。必要なら明示的に環境変数を設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI の呼び出しでエラーが出る:
  - OPENAI_API_KEY を設定しているか確認してください。API の一時的なエラーは内部でリトライし、致命的な失敗時はスコアを 0.0 にフォールバックする箇所があります（警告ログが出ます）。
- DuckDB への保存でエラー:
  - ディレクトリの権限、パス文字列、または渡しているデータのスキーマ不整合を確認してください。conn.executemany に空リストを渡すと問題になるケースがあるため、ライブラリ側で対応済みです。

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内部の主要モジュールと役割の概観（src/kabusys）:

- kabusys/
  - __init__.py — パッケージメタ情報（version, __all__）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（銘柄別センチメントの取得）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL パイプライン（run_daily_etl 等、ETLResult）
    - etl.py — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py — RSS ニュース収集
    - quality.py — データ品質チェック（QualityIssue）
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Value/Volatility ファクター
    - feature_exploration.py — 将来リターン、IC、rank、summary

---

## 開発・拡張のヒント
- テスト: OpenAI 呼び出し等は内部のラッパー関数を patch してモック可能（ユニットテストでの差し替えを想定）。
- DuckDB スキーマ: 初回は data/schema 初期化処理（別ファイルで定義）を実行しておくと良いです（本サンプルでは audit の初期化 API を提供）。
- セキュリティ: news_collector は SSRF 対策・圧縮サイズ制限・XML の安全パーサを使用しています。外部 URL を扱うときは注意を怠らないでください。
- ロギング: settings.log_level を使ってログ出力を制御します。運用時は INFO 〜 WARNING、デバッグ時は DEBUG に設定してください。

---

必要であれば、README に含める実行コマンド（例: cron / systemd / Airflow のジョブサンプル）やより詳細な .env.example、DuckDB スキーマ初期化スクリプトのテンプレートも作成します。どの情報を追加しますか？