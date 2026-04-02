# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）

概要、機能、セットアップ、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量計算、ニュースNLP（OpenAI）によるセンチメント評価、マーケットレジーム判定、監査ログ（発注／約定のトレーサビリティ）を備えた自動売買／リサーチ向けのライブラリ群です。DuckDB を中心にローカル DB へデータを蓄積し、ETL パイプラインや分析ユーティリティ、外部 API クライアント（J-Quants / OpenAI / kabuステーション）を提供します。

設計上のポイント:
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しないなど）
- 冪等性（ETL 保存は ON CONFLICT / upsert を利用）
- フェイルセーフ（外部 API エラー時は影響を限定して継続）
- テストしやすさ（API 呼び出し箇所は差し替え可能に実装）

---

## 主な機能一覧

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務諸表、JPX マーケットカレンダー取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ実装
- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー→価格→財務→品質チェック）
  - 差分更新・バックフィル対応
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue を返す）
- ニュース収集 & NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）による銘柄別センチメント評価（ai_scores に保存）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュース LLM スコアを組み合わせて日次レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC 計算、Z スコア正規化など
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルで戦略→発注→約定のトレーサビリティを担保
- kabuステーション API 用の設定管理（KABU_API_PASSWORD 等）
- Slack 通知用設定（SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- （システム）ネットワークアクセス: J-Quants API、OpenAI API など
- ローカルに DuckDB ファイルや SQLite（監視用）を作るためのファイル書き込み権限

依存は pyproject.toml / requirements.txt に合わせてインストールしてください。開発環境では通常 pip を使います:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .         # プロジェクトルートに pyproject.toml がある前提
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存せず __file__ を基準に探索）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN        : Slack Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID       : 通知先のチャンネル ID
- KABU_API_PASSWORD      : kabuステーション API パスワード（発注等を使う場合）

任意（デフォルトが設定されるもの）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト "INFO"
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

.env 自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップできます（テストなどで便利）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール（pyproject.toml / requirements.txt に合わせて）
4. プロジェクトルートに `.env` を作成（.env.example を参照）
5. DuckDB 用ディレクトリ作成（デフォルト: data/）
6. 初期スキーマ（監査ログなど）を作成する場合は init 関数を呼ぶ

例（Linux/macOS）:

```bash
git clone <repo_url>
cd <repo_root>
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install duckdb openai defusedxml
mkdir -p data
# .env を作成し必須環境変数を設定
```

---

## 使い方（主要な利用例）

以下はライブラリを直接インポートして使うサンプルです。実行は Python スクリプトやジョブランナーから呼び出す想定です。

- DuckDB 接続を準備（例）:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア（ai_scores へ書き込む）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定（market_regime テーブルへ書き込み）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（監査用 DB を別ファイルで作成する場合）:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn にスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- カレンダー / 営業日判定:

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI API を使う関数（score_news / score_regime）は OPENAI_API_KEY を参照します。引数 api_key に直接渡すことも可能です。
- ETL やニュース取得は外部 API にアクセスするためネットワーク・認証情報が必要です。
- 本リポジトリに含まれる研究用モジュールは実際のオーダー実行とは分離されています。発注処理を行う際は必ずリスク管理や paper_trading 環境での確認を行ってください。

---

## よく使う API（抜粋）

- kabusys.data.pipeline.run_daily_etl(...) → ETL 実行（ETLResult を返す）
- kabusys.data.jquants_client.fetch_daily_quotes(...) → J-Quants から日次株価取得
- kabusys.data.jquants_client.save_daily_quotes(conn, records) → DuckDB 保存
- kabusys.data.quality.run_all_checks(conn, ...) → 品質チェックの実行
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) → ニュース NLP スコアリング
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) → レジーム判定
- kabusys.research.calc_momentum / calc_value / calc_volatility → ファクター計算

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースセンチメント・AI スコアリング
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL 結果 型再エクスポート
    - calendar_management.py         — マーケットカレンダー管理（営業日判定）
    - news_collector.py              — RSS ニュース収集（SSRF 対策等）
    - quality.py                     — データ品質チェック
    - stats.py                       — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                       — 監査ログ（監査スキーマの定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Value / Volatility 等
    - feature_exploration.py         — forward returns, IC, summary
  - ai/, data/, research/ 以下のモジュールはさらに細部機能を提供

（上記は主要ファイルのみの抜粋です。細かいユーティリティ関数や定数、例外処理は各ファイル内をご参照ください。）

---

## 運用上の注意

- KABUSYS_ENV を "live" に設定すると実運用を示すフラグ等を有効化する設計になっている箇所があります。実際の発注ロジックを本ライブラリに追加する場合は、十分な検証・ログ監査・フェイルセーフを設けてください。
- 外部 API（OpenAI / J-Quants / kabu）にはレート制限や課金が伴います。実行頻度には注意してください。
- news_collector は SSRF 対策や受信サイズ制限を実装していますが、RSS ソースの信頼性・フォーマットの変化には注意してください。
- ETL / データ保存は DuckDB に依存します。バックアップやファイル管理を運用ルールとして整備してください。

---

## テスト・開発メモ

- OpenAI 呼び出しなどの外部 API はモックしやすい実装（内部呼出し関数を置換可能）になっています。unittest.mock などで差替えて単体テストを作成してください。
- `.env.local` はローカル上書き用途、`.env` は共通設定という優先順で自動読み込みされます。OS 環境変数は保護されます。

---

README の内容は主要な利用方法と設計方針の要約です。より詳細な実装（関数シグネチャや SQL スキーマ等）は各ソースファイルの docstring / コメントを参照してください。必要であればサンプルスクリプトや運用手順のテンプレートも作成します。どの部分の追加が必要か教えてください。