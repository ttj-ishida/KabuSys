# KabuSys

日本株向け自動売買・データプラットフォーム（モジュール群）の参照実装です。  
主にデータ収集（J-Quants／RSS）、品質チェック、特徴量計算、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（発注→約定トレース）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date/target_date を明示的に受け取る）
- DuckDB を中核データベースに利用（オンディスクまたはインメモリ）
- 外部 API 呼び出しは冪等・リトライ・レート制御を備える
- 品質チェック・監査ログにより運用観点で安全性を高める

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のアクセスラッパー（kabusys.config.settings）

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動更新、レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダーの管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS パーサ、SSRF 対策、トラッキングパラメータ除去、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブルの初期化・管理）
  - 汎用統計ユーティリティ（Z スコア正規化 等）

- AI（kabusys.ai）
  - news_nlp.score_news: OpenAI を使ったニュースベースの銘柄センチメント算出（ai_scores テーブルへ書込）
  - regime_detector.score_regime: ETF（1321）200日MA とマクロニュース（LLM）を合成して日次市場レジーム判定（market_regime へ書込）
  - 抜け耐性（API エラー時のフォールバック、リトライなど）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（情報係数）計算、ファクターサマリ

- パッケージ基盤
  - kabusys パッケージエントリポイント: data, strategy, execution, monitoring を想定（現コードベースでは data / ai / research 等が実装済み）

---

## セットアップ手順

前提
- Python >= 3.10（PEP 604 の union 型表記（A | B）を使用しているため）
- Git（プロジェクトルート検出に使用）

1. リポジトリをクローン / checkout
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 推奨パッケージ（最低限）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （必要に応じて slack-sdk などを追加でインストールしてください）

4. 環境変数設定
   - プロジェクトルートに `.env` を配置すると自動で読み込まれます（`.env.local` は上書き）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必要な環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に必要）
     - KABU_API_PASSWORD — kabu ステーション API のパスワード（運用用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（運用用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（運用用）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — 監視DB 等のパス（必要時）

   - 簡易 `.env.example`（参考）
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

5. データベース初期化（監査ログなど）
   - 監査ログ専用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

   - メインの DuckDB ファイルは settings.duckdb_path（デフォルト data/kabusys.duckdb）を利用してください。

---

## 使い方（簡単な例）

以下は代表的なユースケースのサンプルコードです。

- 日次 ETL の実行（株価・財務・カレンダーの差分取得・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP による銘柄スコア算出（OpenAI API キーが環境変数に設定されていること）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"written: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査DBの初期化（発注監査テーブルの作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn に対してアプリから order_requests / executions を記録していく
```

注意点：
- AI 呼び出しは API キー（OPENAI_API_KEY）を必要とします。
- ETL / API 呼び出しはネットワークを使用するため、適切なエラー処理・リトライ設定を運用側で行ってください。
- テスト時は環境変数自動読み込みを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py                (ETLResult re-export)
    - pipeline.py           (run_daily_etl, run_prices_etl 等)
    - stats.py              (zscore_normalize 等)
    - quality.py            (品質チェック)
    - audit.py              (監査ログ初期化)
    - jquants_client.py     (J-Quants API クライアント, save_*/fetch_* 等)
    - news_collector.py     (RSS 収集、正規化、保存処理)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (strategy/, execution/, monitoring/ はパッケージの public API に含まれる想定)

各モジュールの役割はファイル冒頭の docstring に詳細な設計方針・処理フローが記載されています。実装や拡張の際はそちらを参照してください。

---

## 運用・開発上の補足

- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- KABUSYS_ENV（development / paper_trading / live）により実行環境を区別できます。settings.is_live / is_paper / is_dev が利用可能。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- テスト時は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモック化できるよう、内部で呼び出し箇所が関数化されています（例: _call_openai_api, _urlopen 等を patch）。

---

この README はコードベースの概要・導入の手引きに重点を置いています。各モジュールの詳細（関数引数、戻り値、DB スキーマなど）はソースの docstring と型注釈を参照してください。質問や追加で載せたい利用例があれば教えてください。