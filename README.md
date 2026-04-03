# KabuSys

日本株向けのデータプラットフォーム／自動売買補助ライブラリです。  
ETL（J-Quants）で市場データを収集・品質チェックし、ニュースNLP・市場レジーム判定・ファクター計算などの研究 / 運用ユーティリティを提供します。監査ログや発注フローのためのスキーマ初期化機能も含みます。

---

## 主要機能（概要）

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・JPXマーケットカレンダーを差分取得・保存
  - DuckDB を用いた保存（冪等な SAVE 実装）
  - ETL 実行結果を表す ETLResult 型

- データ品質
  - 欠損 / スパイク / 重複 / 日付不整合のチェック（QualityIssue）

- ニュース収集・NLP
  - RSS 収集・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄単位で ai_scores へ書込）
  - ニュース時間ウィンドウ管理（JST⇄UTC）

- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull / neutral / bear）
  - OpenAI 呼び出しに対するリトライ・フォールバック実装

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン / IC / ファクター統計（Zスコア正規化等）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の DDL 定義と初期化関数
  - すべて UTC 保存、冪等初期化機能

---

## 必要な依存関係（推奨）

最低限以下をインストールしてください（バージョンはプロジェクト要件に合わせて調整してください）。

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

プロジェクトは .env / .env.local および OS 環境変数を自動で読み込みます（プロジェクトルートを .git または pyproject.toml で検出）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（代表例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須、ETL 用）
- OPENAI_API_KEY — OpenAI API キー（AI スコアリング用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注統合がある場合）
- KABU_API_BASE_URL — kabu API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / その他監視設定
- KABUSYS_ENV — environment: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

必須の環境変数が不足していると Settings が例外を投げます。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って自動読み込みを抑制すると便利です。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（またはソースを配置）
2. Python 仮想環境を作成・有効化
3. 必要ライブラリをインストール（上記参照）
4. .env をプロジェクトルートに作成して必要なキーを設定
5. DuckDB ファイル等の格納ディレクトリを作成（例: `mkdir -p data`）

例コマンド:
```
git clone <repo-url>
cd repo
python -m venv .venv
source .venv/bin/activate
pip install -e .  # setup がある場合
# あるいは: pip install duckdb openai defusedxml
mkdir -p data
cp .env.example .env
# .env を編集して JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY を設定
```

---

## 使い方（簡単なコード例）

以下はライブラリ内の主要関数の呼び出し例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB に接続して日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP（指定日分のスコアを ai_scores に書き込む）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"written codes: {n_written}")
```

- 市場レジーム判定:
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ用 DuckDB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# またはインメモリ:
# conn = init_audit_db(":memory:")
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定。API キーを環境変数または引数で渡してください。
- ETL / ニュース収集 / AI 呼び出しはネットワークアクセスが必要です。レート制限や API エラーに対するリトライが組み込まれていますが、API 料金や使用量に注意してください。

---

## 実行フロー（概念）

- run_daily_etl:
  1. カレンダー ETL（先読み）
  2. 株価（日次）差分 ETL
  3. 財務データ差分 ETL
  4. 品質チェック（任意）
  5. ETLResult を返す（ログと監査に利用）

- score_news:
  1. 前日 15:00 JST ～ 当日 08:30 JST の記事を集計
  2. 銘柄ごとに記事を結合し LLM に投げる（バッチ）
  3. レスポンスを検証し ai_scores に書き込む（DELETE→INSERT）

- score_regime:
  1. ETF 1321 の 200日 MA 乖離を計算
  2. マクロニュースのタイトルを抽出して LLM でセンチメント評価
  3. 重み付け合成して market_regime に保存

---

## 主要モジュール / ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLU / ai_scores 書き込み
    - regime_detector.py     — 市場レジーム判定（ma200 + macro sentiment）
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン、run_daily_etl 等
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - news_collector.py      — RSS 収集・前処理・DB 保存
    - quality.py             — データ品質チェック
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py               — 汎用統計（zscore_normalize）
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value の計算
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - ai/                      — (上記) LLM 関連
  - research/                — 研究ユーティリティ群
  - data/                    — データ取り込み・品質・保存・監査

---

## テスト / 開発ノート

- 自動環境読み込みは .env / .env.local の順で適用されます（OS 環境変数を優先）。テストで自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、ユニットテストではこれをモックして安定化できます（例: unittest.mock.patch）。
- DuckDB の executemany は空リストを受け付けないバージョン差異があるため、insert 前に空チェックを行っている箇所があります。テスト時に注意してください。
- RSS 取得は SSRF・XML攻撃対策を施しています。実ネットワークでの検証を行ってください。

---

## 免責 / 注意事項

- 本リポジトリはトレード・投資助言を目的としたものではありません。実際の売買に使用する場合は十分な確認と検証を行ってください。
- OpenAI / J-Quants / 証券会社 API の使用に伴う料金・レート制限に注意してください。
- 本ドキュメントはコードベースの抜粋に基づいて作成しています。実際の導入時は pyproject.toml / requirements.txt / CI 設定等を確認してください。

---

必要に応じて README に記載する追加項目（例: 開発用スクリプト、CI 実行方法、より詳細な環境変数説明、サンプル .env.example）を作成します。どの情報を追加しますか？