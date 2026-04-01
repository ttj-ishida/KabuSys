# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API や RSS ニュース、OpenAI（LLM）を組み合わせてデータ収集・品質チェック・特徴量生成・ニュースセンチメント評価・市場レジーム判定・監査ログ（トレーサビリティ）までを提供します。ライブラリとして他のアプリケーション（実行エンジン / ストラテジー / 実行モジュール）に組み込んで利用する想定です。

主な用途
- データ ETL（J-Quants → DuckDB）
- データ品質チェック
- ニュース収集・NLP による銘柄センチメント算出
- LLM を用いたマクロセンチメントと市場レジーム判定
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 監査ログ（信号→発注→約定のトレーサビリティ）スキーマ初期化

---

## 機能一覧

- 設定管理
  - .env ファイルや環境変数からの設定読み込み（自動ロード機能、無効化可）
- Data（jquants_client / ETL / quality / calendar / news_collector / audit）
  - J-Quants API クライアント（株価・財務・マーケットカレンダー）
  - 日次 ETL パイプライン（差分取得、保存、品質チェック）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - RSS ニュース収集（SSRF 対策・トラッキング除去・前処理）
  - 監査ログ（signal_events / order_requests / executions）のスキーマ・初期化
- AI（news_nlp / regime_detector）
  - ニュース文章の LLM によるセンチメント評価（gpt-4o-mini を想定、JSON Mode）
  - マクロセンチメントと ETF 1321 の MA200 乖離を統合した市場レジーム判定
- Research（factor_research / feature_exploration）
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 共通ユーティリティ
  - 統計ユーティリティ（z-score 正規化 等）
  - DuckDB を用いたデータ保存/読み出しに最適化された実装

---

## 動作環境・前提

- Python 3.10+
- 必要パッケージ（例 — 要インストール）
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリ中心だが、ネットワーク / LLM 呼び出しのためのライブラリが必要）

※ requirements.txt / pyproject.toml がプロジェクトに含まれている想定です。実運用ではそれらを参照して依存関係をインストールしてください。

---

## インストール

仮想環境を作成してからインストールします（パッケージ配布形式により変わります）。

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# ローカルパッケージとしてインストール（プロジェクトルートに pyproject.toml がある想定）
pip install -e .
# 必要な外部依存を個別に入れる例
pip install duckdb openai defusedxml
```

---

## 設定 (.env / 環境変数)

プロジェクトは環境変数または .env / .env.local から設定を自動で読み込みます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しで使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視/モニタリング用) パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
```

---

## セットアップ手順（簡易ガイド）

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。
2. .env をプロジェクトルートに配置して必要な環境変数を設定する。
3. DuckDB ファイルの場所（デフォルト data/kabusys.duckdb）へアクセス可能にする。
4. 監査用 DB 初期化（必要に応じて）:
   - 既存の DuckDB 接続に監査スキーマを追加するか、専用 DB を作成します。

---

## 使い方（コード例）

以下はライブラリを直接呼び出す例です。実行は CLI ではなく Python スクリプト/アプリケーションから行います。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を渡さないと today が使用されます
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date = 例: 2026-03-20
n_written = score_news(conn, date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY が使われる
print("書込み件数:", n_written)
```

- 市場レジーム判定を実行する:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, date(2026, 3, 20), api_key=None)
print("score_regime result:", res)
```

- 監査スキーマを初期化する:
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn, transactional=True)
```

- 研究用ファクターを計算する:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- カレンダー補助:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

---

## 注意点 / 設計方針（重要）

- ルックアヘッドバイアス防止
  - 多くの関数は内部で date.today() 等を参照せず、呼び出し元が明示的に target_date を渡すことでバックテスト時の参照バイアスを避ける設計です。
- フェイルセーフ設計
  - 外部 API（OpenAI / J-Quants）失敗時には例外を投げずフォールバック（0.0 やスキップ）する処理が多く、運用時の一部機能停止がシステム全体を停止させないようにしています。
- 冪等性
  - ETL・保存処理は可能な限り冪等（ON CONFLICT DO UPDATE / INSERT ... DO UPDATE）で実装されています。
- DuckDB 前提
  - 内部データ保存は DuckDB を想定。監査用 DB は専用 DuckDB でもよいです。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（version 等）
- config.py — 環境変数 / 設定読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM センチメント評価、ai_scores への書き込み
  - regime_detector.py — ETF MA200 とマクロセンチメントを合成して market_regime を算出
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント、保存関数（raw_prices / raw_financials / market_calendar 等）
  - pipeline.py — ETL パイプライン／run_daily_etl 等
  - etl.py — ETL インターフェース（ETLResult のエクスポート）
  - news_collector.py — RSS 取得・正規化・raw_news 保存ロジック
  - calendar_management.py — 市場カレンダー管理・営業日判定
  - quality.py — データ品質チェック（欠損・スパイク等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — 将来リターン、IC、サマリー等
- research パッケージは data.stats を再利用して統計処理を提供

（各モジュールは README で概説した機能を実装しています。実際のメソッド・引数はソースを参照してください）

---

## ログ・モード

- KABUSYS_ENV により env を切り替えられます（development / paper_trading / live）。
- LOG_LEVEL 環境変数でロギングレベルを制御します。

---

## テスト / デバッグ

- OpenAI 呼び出しや外部 HTTP のインターフェースは内部で分離されており、ユニットテスト時は該当関数をモックして置換できます（ソース内にその意図のコメントあり）。
- 自動環境変数ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。

---

## 補足

この README はコードベースの主要な機能と使い方を簡潔にまとめたものです。各モジュールには詳細な docstring と実装コメントがありますので、より深い利用方法や内部仕様（例: 各 SQL クエリの振る舞い、リトライ戦略、バックオフ、フェイルセーフ挙動など）は該当モジュールソースを参照してください。必要であれば個別の使い方やサンプルスクリプト（ETL 定期実行、監視ジョブ、戦略連携サンプル）も作成します。