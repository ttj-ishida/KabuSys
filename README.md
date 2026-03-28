# KabuSys

日本株向けの自動売買・データプラットフォーム（ライブラリ形式）。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP、LLM を用いた市場レジーム判定、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などの機能を備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引基盤向けのオープンなコンポーネント群です。主に以下を提供します。

- J-Quants API との堅牢な連携（レートリミット、リトライ、トークン自動リフレッシュ）
- DuckDB を用いたローカルデータレイク（raw_prices / raw_financials / market_calendar など）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集・前処理と OpenAI を使った銘柄別ニュースセンチメント分析
- 市場レジーム判定（ETF とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions のトレーサビリティ）初期化ユーティリティ
- 環境設定管理（.env 自動読み込み、必須環境変数のラップ）

設計上、ルックアヘッドバイアスを避けるために関数は内部で date.today() を安易に参照せず、呼び出し側が基準日を明示することを想定しています。また、外部 API 呼び出しは冪等性／フォールトトレランスを重視した実装になっています。

---

## 主な機能一覧

- データ収集・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄一覧、JPX カレンダー取得
  - 差分取得・バックフィル・保存（DuckDB へ ON CONFLICT DO UPDATE）
  - 日次 ETL の統合実行（品質チェックを含む）

- データ品質チェック
  - 欠損データ検出（OHLC 欠損）
  - 前日比スパイク検出（閾値指定可能）
  - 主キー重複検出
  - 将来日付 / 非営業日データの検出

- ニュース処理 & AI
  - RSS からニュース収集（SSRF 対策、トラッキングパラメータ除去、gzip 制御）
  - ニュース前処理（URL 除去、空白正規化）
  - OpenAI（gpt-4o-mini）による銘柄別センチメントスコアリング（batch、JSON mode）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定

- リサーチ / ファクター
  - モメンタム、ボラティリティ、バリュー等の計算
  - 将来リターン計算、IC（Spearman）やファクター統計要約
  - z-score クロスセクション正規化ユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DB 初期化（UTC タイムスタンプ固定、トランザクションオプション）

- 設定管理
  - .env と OS 環境変数の読み込み（プロジェクトルートを自動検出）
  - 必須環境変数のアクセスラッパー

---

## 必要な環境変数

以下は主要な必須 / 推奨環境変数です（.env に設定する想定）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: 環境 (development | paper_trading | live)（省略時: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（省略時: INFO）

自動 .env ロードはデフォルトで有効です。無効化するには環境変数を設定します:
KABUSYS_DISABLE_AUTO_ENV_LOAD=1

（プロジェクトルートが .git または pyproject.toml を含むディレクトリとして検出される場合に .env/.env.local を自動読み込みします。.env.local は上書き優先）

---

## セットアップ手順

1. Python のセットアップ（推奨: 3.10+）
2. リポジトリをチェックアウト

3. 仮想環境の作成と依存導入（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要パッケージの例（プロジェクトの pyproject / requirements があればそちらを使用）
pip install duckdb openai defusedxml
# 開発インストール（パッケージとして利用する場合）
pip install -e .
```

4. .env を作成（リポジトリに .env.example があれば参照）
例: .env
```text
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB データベース用のディレクトリ作成（必要なら）
```bash
mkdir -p data
```

---

## 使い方（代表的なユースケース例）

以下は Python REPL やスクリプトからの利用例です。各関数は明示的に DuckDB 接続と target_date を受け取る設計です。

- DuckDB 接続の取得例
```python
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ETL を今日で実行
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定を実行する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))
```

- 監査ログ用 DuckDB 初期化（独立 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルが作成されていることを確認できます
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI を使う機能は API 呼び出しを含むため、実行には OPENAI_API_KEY が必要です。
- 各処理は外部 API に依存するため、ネットワーク状態や API レート制限に注意してください。

---

## 開発者向けメモ

- .env 読み込みルール:
  - 自動ロード順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- DuckDB 用の executemany は空リストを受け取れない箇所があるため、呼び出し側で空リストチェックを行っています（ETL/ai スコア保存など）。

- OpenAI 呼び出しは JSON mode を使って厳密な JSON 出力を期待する設計です。レスポンスの頑健なパースとバリデーション処理が含まれます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP / OpenAI 呼び出し、ai_scores 書込み
    - regime_detector.py            — マクロ + MA 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                      — 監査ログ定義・初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - research, monitoring, strategy, execution, monitoring ... （パッケージ公開対象として __all__ に設定）

（上記は主要モジュールの抜粋です。実際のリポジトリにはさらに補助モジュールやユーティリティが含まれる可能性があります）

---

## 注意事項 / ベストプラクティス

- 本ライブラリはデータ取得・解析・監査ログのユーティリティを提供しますが、実際の発注ロジック（ブローカー API 連携や資金管理）については別途実装が必要です。特に本番稼働（is_live）時の安全対策は十分に行ってください。
- OpenAI など外部 API をテストする場合はモック（unittest.mock.patch）を使って API 呼び出しを差し替えることを推奨します。コード内にもモック可能なラッパー関数が用意されています。
- DuckDB ファイルはバージョンやパスに依存します。バックアップ・マイグレーションは運用ポリシーに従ってください。

---

README は以上です。必要であればインストール用の requirements.txt / pyproject.toml や .env.example のテンプレートも作成しますか？