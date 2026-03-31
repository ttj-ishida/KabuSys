# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、リサーチ用ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを含むモジュール群を提供します。

主にバックテストや運用バッチ、戦略実行のための共通ユーティリティ群を収めたパッケージです。

---

## 主な機能（抜粋）

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）
- データ取得・ETL（J-Quants API）
  - 株価日足（OHLCV）取得 / 保存（raw_prices）
  - 財務データ取得 / 保存（raw_financials）
  - JPX マーケットカレンダー取得 / 保存（market_calendar）
  - 差分更新・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集（RSS）と前処理
  - RSS フィード取得、URL 正規化、SSRF 対策、前処理、raw_news への保存（news_collector）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュース + ETF(1321) の MA200 乖離を組み合わせた市場レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode を利用し、リトライやフェイルセーフを備える
- リサーチ / ファクター計算
  - Momentum, Volatility, Value 等のファクター計算（research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - z-score 正規化ユーティリティ（data.stats）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合検出（data.quality）
- 監査ログ / トレーサビリティ
  - signal_events / order_requests / executions の監査スキーマ初期化（data.audit）
  - 監査 DB 初期化ユーティリティ（init_audit_db）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部で union 型や型ヒントを多用）
- DuckDB（Python パッケージ）
- OpenAI の Python SDK（openai / OpenAI client）
- defusedxml（XML パースの安全化）

例: 仮想環境を使ったセットアップ例

1. 仮想環境作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt が無い場合の最小例）
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを開発インストール（ローカルで import 可能にする）
   プロジェクトルートに `pyproject.toml` または `setup.py` がある想定で:
   ```
   pip install -e .
   ```
   ない場合は直接 `src` を PYTHONPATH に追加するか、プロジェクトルートで実行してください。

4. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を作成することで自動読み込みされます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の主な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API を利用する機能（news_nlp, regime_detector）で必要

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視など）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

.env 例（.env.example を参照して作成してください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す想定です。DuckDB コネクションは kabusys の関数に直接渡します。

- ETL（日次パイプライン）の実行例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（銘柄ごとスコア）の実行例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```
- 市場レジーム判定の実行例:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（監査専用 DB を分けて使う例）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn に対して監査テーブルが作成済み
```

- 研究用ファクター計算例:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
val = calc_value(conn, target)
vol = calc_volatility(conn, target)
```

注意:
- AI（OpenAI）を使う関数は API キーを引数で渡すこともできます（引数優先）。環境変数 OPENAI_API_KEY に設定が無い場合は ValueError を送出します。
- 各処理はルックアヘッドバイアスを避ける設計になっており、内部で date.today() を勝手に参照しない関数が多く、target_date を明示することが推奨されます。

---

## 実装に関する重要な設計方針（要点）

- Look-ahead バイアス防止:
  - AI・ETL・リサーチ関数は target_date を明示的に受け取り、データ選択時は target_date 未満 / 以前などを厳格に扱います。
- フェイルセーフ:
  - OpenAI API 呼び出しや外部 API の失敗時には例外を投げずフォールバック（ゼロスコア等）する実装箇所があるため、バッチが全面停止しない設計です。ただし重大な DB 書き込み失敗等は例外を伝播します。
- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE 等で冪等性を確保しています（ETL 再実行が安全）。
- セキュリティ:
  - RSS 取得では SSRF 対策、受信サイズ制限、defusedxml による安全な XML パースを行います。
- リトライ / レート制御:
  - J-Quants クライアントはレート制限（120 req/min）を守る内部スロットリング、HTTP の一部コードに対する指数バックオフリトライを備えます。
- DuckDB 前提:
  - データ永続化・集計は DuckDB を使用することを前提としています。

---

## ディレクトリ構成（主要ファイル）
（プロジェクトルート直下が `src/` をルートにした構成を想定）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）処理
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & DuckDB 保存
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETL 結果クラス再エクスポート（ETLResult）
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理 / 営業日判定
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/、data/、research/ はそれぞれ上記の公開 API を提供

---

## 開発・運用メモ

- .env 自動ロード:
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml の存在）を検出して `.env` / `.env.local` を順に読み込みます。OS 環境変数は `.env.local` による上書きから保護されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- テスト・モック:
  - OpenAI の呼び出しや外部 HTTP 呼び出しはモジュール内で分離され、テスト時に unittest.mock.patch で差し替え可能です（_call_openai_api や _urlopen 等）。
- ロギング:
  - Settings.log_level やアプリ側での logging 設定で詳細なログ制御が可能です。
- DuckDB の互換性:
  - 一部の実装（executemany の空リスト等）で DuckDB バージョン差異を考慮したガードが入っています。DuckDB のバージョン更新時は互換性に注意してください。

---

必要であれば、README に追加する内容（例: API のより詳細な使用例、SQL スキーマ定義、CI/CD 手順、デプロイ手順、.env.example の完全テンプレートなど）も作成します。どの情報を追加したいか教えてください。