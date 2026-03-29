# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

KabuSys は日本株向けのデータパイプライン、ファクター/リサーチ、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含む自動売買プラットフォーム用の内部ライブラリ群です。本リポジトリは各機能をモジュール化しており、ETL → 品質チェック → 研究 → 戦略 → 発注フローの基盤となるユーティリティを提供します。

主な設計方針（抜粋）
- Look-ahead bias を避ける設計（内部で datetime.today() を直接参照しない等）
- DuckDB をデータレイク／分析 DB として使用
- J-Quants API（株価・財務・カレンダー）との差分ETL・安全なリトライ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- 冪等性・監査トレース（UUIDチェーン）による注文追跡

---

## 機能一覧

- data
  - ETLパイプライン（差分取得、保存、品質チェック）
  - J-Quants API クライアント（レート制御・自動トークンリフレッシュ・ページング）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 監査ログ初期化／管理（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（Zスコア正規化 等）

- ai
  - news_nlp: ニュース記事を銘柄別にまとめて OpenAI でセンチメント評価→ ai_scores に書込
  - regime_detector: ETF(1321) の MA200 乖離とマクロニュースの LLMセンチメントを合成して市場レジーム判定→ market_regime に保存

- research
  - factor_research: Momentum / Value / Volatility / Liquidity などのファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）、統計サマリー、ランク付けユーティリティ

- config
  - .env または環境変数からの設定読み込み、自動ロード（.env/.env.local）と設定プロパティ群

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の型記法（X | Y）を利用）
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がない場合は上記パッケージを pip install してください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

下記は本システムで参照される主要環境変数の例です（.env に記載して管理する想定）。

- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD：kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV：環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL：ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")
- OPENAI_API_KEY：OpenAI API キー（news_nlp, regime_detector で使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1：パッケージインポート時の .env 自動ロードを無効化（テスト時に便利）

注意：.env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境作成・有効化、依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

3. 設定ファイル (.env) を用意
   - リポジトリルートに `.env` または `.env.local` を作成し、必要な環境変数を設定してください（.env.example がある場合はそれを参考にしてください）。
   - 例（実運用では安全に保管）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な操作例）

以下は Python REPL／スクリプトから呼ぶ例です。DuckDB 接続はファイルパスまたは ":memory:" を指定できます。

- 日次 ETL を実行（データ取得 → 保存 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（OpenAI）で銘柄ごとのスコアを取得して DB に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {written} codes")
```

- 市場レジーム判定（ma200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("ok" if res == 1 else "failed")
```

- 監査ログ用 DuckDB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # parent dir is auto-created
```

- 研究用ファクター計算の例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# レコードは dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意点
- OpenAI API 呼び出しはコストがかかります。api_key を必ず適切に設定し、呼び出し頻度に注意してください。
- 実行時に必要なテーブル（raw_prices, raw_news, news_symbols, ai_scores, prices_daily, market_regime, raw_financials, market_calendar 等）が存在することを確認してください。ETL や初期化関数で作成されることもあります。

---

## ディレクトリ構成

概略（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定ロード
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの OpenAI スコアリング（ai_scores 書き込み）
    - regime_detector.py    — マーケットレジーム判定（1321 MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETL の公開ラッパ（ETLResult 再エクスポート）
    - news_collector.py     — RSS ニュース収集（SSRF対策・前処理）
    - calendar_management.py— マーケットカレンダー処理（is_trading_day 等）
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査テーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Value/Volatility ファクター
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - research/*, ai/*, data/* の各モジュールに詳細実装（DuckDB クエリ、トランザクション制御、ロギング、フェイルセーフ設計など）

（実際のファイル・サブモジュールはリポジトリ内の src/kabusys 配下を参照してください）

---

## 運用上の注意

- 本ライブラリは外部 API（J-Quants、OpenAI、RSS ソース）へアクセスします。API キーやトークンの管理、リクエスト頻度管理、コスト／レート制限に注意してください。
- 自動売買を実際に稼働させる際は、paper_trading モードや入念なリスク管理ルールを整備してください（KABUSYS_ENV による運用モード切替を利用）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを防げます。OpenAI 呼び出し等はモック化してテストすることを推奨します。

---

## 貢献・拡張

- バグ修正、機能追加、ドキュメント改善は歓迎します。まず Issue を立て、主要な変更は Pull Request で提案してください。
- 外部インテグレーション（ブローカー API／kabu ステーションとの実際の発注モジュール）は本パッケージには含まれていないため、execution・strategy 層として別モジュールを実装して統合してください（__all__ に execution/strategy/monitoring 等が想定されています）。

---

## ライセンス

リポジトリにライセンス表記がない場合は、使用・配布条件が未定義です。商用利用や再配布を行う前にライセンスを確認・追加してください。

---

README の補足やコードの説明、利用例の追加を希望される場合は、どのモジュール（ETL / news_nlp / regime_detector / jquants_client / audit / research 等）に注力してほしいか教えてください。