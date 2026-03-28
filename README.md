# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
データ収集（J-Quants / RSS）、品質チェック、特徴量計算、ニュースNLP / LLM を用いたスコアリング、監査ログ（発注 → 約定トレーサビリティ）など、自動売買システムの基盤的コンポーネントを提供します。

主な設計方針:
- ルックアヘッドバイアス防止（date.today() 等の直接参照を極力排除）
- DB への冪等書き込み（ON CONFLICT / DELETE→INSERT 等）
- 外部 API 呼び出しはリトライ・バックオフ・レート制御を実装
- セキュリティ考慮（SSRF対策、XMLパースの安全化等）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定を Settings 経由で取得
- データプラットフォーム（data）
  - J-Quants API クライアント（認証 / ページネーション / レート制御 / 保存）
  - ETL パイプライン（prices / financials / calendar）
  - 市場カレンダー管理（営業日判定、next/prev 等）
  - ニュース収集（RSS → raw_news、SSRF / Gzip / XML 対策）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
- AI / NLP（ai）
  - ニュースを LLM（gpt-4o-mini）でスコアリング（銘柄ごと）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
  - OpenAI 呼び出しは JSON Mode を想定、失敗時はフォールバック動作有り
- リサーチ（research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 汎用ユーティリティ
  - 統計関数（zscore 正規化等）
  - データベース初期化（監査用 DuckDB）など

---

## 必要な環境変数

Settings クラスから参照される主な環境変数（必須のものは README 例で必ず設定してください）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY (LLM を利用する場合必須) — OpenAI の API キー

オプション（デフォルト値あり）:
- KABUSYS_ENV (development / paper_trading / live) — 実行環境（デフォルト development）
- LOG_LEVEL (DEBUG/INFO/...) — ログレベル（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境）

1. Python（推奨: 3.10+）をインストール
2. リポジトリをクローン／配置し、プロジェクトルートに移動
3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
4. 依存パッケージをインストール
   - requirements.txt / pyproject.toml があればそれに従ってください。
   - 例: pip install -e .
   - OpenAI SDK・duckdb 等が必要です: pip install openai duckdb defusedxml
5. .env を作成（上記の必須環境変数を設定）
   - プロジェクトルートに .env / .env.local を置くと自動読み込みされます

注意:
- config モジュールは .git もしくは pyproject.toml を基準にプロジェクトルートを自動検出して .env を読み込みます。CWD に依存しません。
- 自動読み込みを無効にしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（代表的な例）

以下はライブラリの代表的な使い方例です。実行前に .env を設定してください。

- DuckDB 接続を作成し ETL を実行する（日次 ETL）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# デフォルト DuckDB ファイルを使う場合
conn = duckdb.connect('data/kabusys.duckdb')

# 当日（または指定日）の ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）を実行して ai_scores テーブルへ書き込む

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定を実行して market_regime テーブルへ書き込む

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/kabusys_audit.duckdb")
# conn を使って order_requests / executions 等を操作できます
```

- J-Quants から株価を直接取得する（認証は内部で処理）

```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date

records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(records), "件取得")
```

注意点:
- LLM を使用する関数（score_news / score_regime）は OPENAI_API_KEY を環境変数に設定するか、api_key 引数で明示してください。
- すべての DB 書き込みは冪等化を意識して実装されていますが、本番運用時は必ずバックアップ・テストを行ってください。

---

## ディレクトリ構成（概要）

以下は src/kabusys 配下の主要モジュールと役割の一覧です（抜粋）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込みと Settings 提供
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM センチメントスコアリング（ai_scores 書き込み）
    - regime_detector.py — ETF MA + マクロニュース合成による市場レジーム判定（market_regime 書き込み）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        — ETL パイプラインの主要処理（run_daily_etl 等）
    - etl.py             — ETLResult の公開
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py  — RSS ニュース収集（SSRF / Gzip / XML 対策）
    - quality.py         — データ品質チェック
    - stats.py           — 汎用統計ユーティリティ（zscore など）
    - audit.py           — 監査ログスキーマの作成 / 初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/、data/、research/ 内の各種ユーティリティや補助関数

（実際のファイル一覧はプロジェクトルートの src/kabusys 配下を参照してください）

---

## 実装上の主要な注意点（運用向け）

- Look-ahead bias の防止
  - 多くのモジュールで target_date 未満のデータのみを参照する設計になっています。バックテストや研究で日付の扱いに注意してください。
- 冪等性
  - J-Quants からの保存（save_*）は ON CONFLICT DO UPDATE 等で冪等化されています。
- レート制御・リトライ
  - J-Quants クライアントは rate limiting、指数バックオフ、401 発生時のトークンリフレッシュなどを実装しています。
  - OpenAI 呼び出しにもリトライ / フェイルセーフ（スコア=0）等の対策を行っています。
- セキュリティ
  - news_collector は SSRF 対策、XML の安全パーサ defusedxml、レスポンスサイズ制限などを実装しています。
- DB 互換性
  - DuckDB 特有の挙動（executemany の空リスト不可など）に配慮した実装があります。

---

## 貢献・拡張

- 新しいデータソース追加やフィルタリング、LLM モデルの変更、戦略ロジックの追加など拡張が可能です。
- テストを書く際は環境変数自動読み込みをオフにする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）か、設定用の .env.test を用意してください。
- OpenAI / J-Quants の呼び出しは外部依存のため、ユニットテストではモック化してテストしてください（コード中にモックしやすい設計が施されています）。

---

もし README のサンプル .env、具体的なスクリプト（CLI）やセットアップ用の pyproject.toml / requirements.txt のテンプレートが必要であれば、プロジェクト用途（開発/本番/CI）に合わせた例を作成します。どの部分を優先して詳しくしたいか教えてください。