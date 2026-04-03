# KabuSys

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注トレース）など、システム全体のデータ管理と研究ワークフローを支援するモジュール群を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得 / ETL
  - J-Quants API からの株価日足、財務情報、マーケットカレンダーの差分取得（ページネーション・レート制御・リトライ対応）
  - DuckDB へ冪等的に保存（ON CONFLICT ベース）
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント算出（ai_scores へ保存）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）を合成して日次レジーム（bull/neutral/bear）を算出
- リサーチ支援
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
- 監査ログ（トレーサビリティ）
  - signal → order_request → executions の階層を管理する監査スキーマ初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数からの設定読み込み（プロジェクトルート自動検出）
  - 必須環境変数チェック

---

## 必要条件

- Python 3.10 以上（typing の | 記法などを使用）
- 推奨ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの requirements.txt がある場合はそれに従ってください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 開発用でパッケージ化されている場合:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を用意するか、OS 環境変数を設定してください。
   - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN = J-Quants のリフレッシュトークン（ETL 実行に必須）
   - KABU_API_PASSWORD = kabuステーション／発注 API のパスワード（発注機能を使う場合）
   - OPENAI_API_KEY = OpenAI API キー（ニュース NLP / レジーム判定で必須）
   - その他（任意・デフォルトあり）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - KABUSYS_ENV (development / paper_trading / live)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知連携のため）

   例 `.env`（最小）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な呼び出し例）

以下は Python スクリプトから直接呼び出す例です。各関数は DuckDB の接続を受け取ります。

- DuckDB 接続の作成例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日を対象に実行
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（ai_scores に書き込み）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20))  # 指定日のニュースウィンドウを処理
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime に書き込み）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査用 DuckDB を新規作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以後 audit_conn を使って監査テーブルへ書き込み・参照が可能
```

- 研究用関数（ファクター計算等）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

注意:
- OpenAI を使う機能は `OPENAI_API_KEY` が必要です。関数の api_key 引数で明示的に渡すこともできます。
- ETL / データ取得は J-Quants トークンが必要です（`JQUANTS_REFRESH_TOKEN` 経由で id token を自動取得します）。
- モジュールはルックアヘッドバイアスを避ける設計です（内部的に date.today() を使わない等の配慮があります）。

---

## 重要な設計上の注意点

- ルックアヘッドバイアス防止
  - AI スコア算定やファクター計算では target_date より未来のデータを参照しないように設計されています。
- フェイルセーフ
  - OpenAI 呼び出し失敗や API エラー時には例外を必要以上に投げずフェイルセーフ（0やスキップ）で継続する設計の箇所があります。
- 冪等性
  - DuckDB への保存は可能な限り ON CONFLICT による上書きで冪等に行われます。
- セキュリティ
  - RSS フィード取得では SSRF 対策・XML パースの安全化（defusedxml）などを行っています。

---

## 主要ディレクトリ構成

（リポジトリの `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込み、Settings クラス定義
  - ai/
    - __init__.py
    - news_nlp.py           : ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py    : 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     : J-Quants API クライアント（fetch / save / auth）
    - pipeline.py           : ETL パイプライン（run_daily_etl 等）
    - etl.py                : ETLResult の再エクスポート
    - news_collector.py     : RSS ニュース収集
    - stats.py              : 統計ユーティリティ（zscore 正規化）
    - quality.py            : データ品質チェック
    - calendar_management.py: 市場カレンダー管理（営業日判定等）
    - audit.py              : 監査ログスキーマ初期化（監査テーブル定義）
  - research/
    - __init__.py
    - factor_research.py    : モメンタム / ボラティリティ / バリュー 等
    - feature_exploration.py: 将来リターン、IC、統計サマリー

---

## 開発者向けメモ

- .env のパーシングはシェル風の `export KEY=val` や引用符、コメントなどに対応しています。
- 自動 .env 読み込みはプロジェクトルートを `.git` または `pyproject.toml` から探索して行います。CI／テストで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出し部分はテスト容易性を考慮してラッパー関数に分けられており、ユニットテスト時に差し替え可能です（mock で置き換え）。

---

## ライセンス / 貢献

この README はコードベースからの抜粋に基づく概要を示します。実際の運用にあたってはセキュリティ（API キーの管理）、レート制御、バッチ運用、ログ監視などを十分に検討してください。貢献やバグ報告はリポジトリの Issue / Pull Request を通してお願いします。