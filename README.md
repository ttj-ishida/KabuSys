# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB を中心とした ETL、ニュース収集・NLP、ファクター計算、監査ログ（オーダー追跡）、J-Quants / OpenAI / kabuステーション 等との連携ヘルパーを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() に依存しない設計）
- DuckDB を単一の分析ストアとして利用（ETL は冪等、ON CONFLICT を多用）
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを実装
- テスト容易性を考慮して API 呼び出しや時間参照を差し替え可能

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数のラッパ（settings オブジェクト）

- データ取得 / ETL（kabusys.data.pipeline）
  - J-Quants から株価（日足）・財務・マーケットカレンダーの差分取得
  - 差分保存・バックフィル・品質チェック（欠損・重複・スパイク・日付整合性）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news / news_symbols への冪等保存
  - SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント付与
  - バッチ処理、リトライ、レスポンス検証、ai_scores への保存

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
  - OpenAI を用いたマクロセンチメント評価

- 研究用指標（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）やファクター統計サマリー
  - zscore_normalize（クロスセクション Z スコア正規化）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - J-Quants からの夜間更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化可能

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出し、ページネーション、トークン自動リフレッシュ、保存ユーティリティ

---

## 必要条件 / 依存ライブラリ

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, logging, datetime など

（プロジェクトの pyproject.toml / requirements.txt に合わせてインストールしてください）

例:
```bash
python -m pip install duckdb openai defusedxml
```

---

## 環境変数

主要な環境変数（必須なもの／用途）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector 等）に使用
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーションのベース URL（省略可）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL — ログレベル ("DEBUG" / "INFO" / ...)

自動で .env / .env.local をプロジェクトルートから読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

settings オブジェクトは kabusys.config.settings でアクセスできます。

---

## セットアップ手順（ローカル向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements / pyproject があればそれを使用
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を配置するか、OS 環境変数を設定します。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB の初期スキーマ（監査ログなど）を用意する場合は init_audit_db を使用します（例は下記）。

---

## 使い方（例）

以下はライブラリを直接インポートして使う簡単な例です。実行は Python スクリプト内で行います。

- DuckDB 接続を開いて ETL を実行する（日次 ETL）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数に設定されていれば api_key=None でも動作します
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

- 市場レジーム判定を走らせる:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査用 DuckDB を初期化する（監査テーブル作成）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# conn は DuckDB 接続。以後の操作で signal_events / order_requests / executions を使用可能。
```

- settings を参照する:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意:
- OpenAI を呼び出す関数は api_key を引数で渡すことも可能です（テスト時は差し替えが容易）。
- ETL／AI 呼び出しはネットワーク依存のため適切な例外ハンドリングを行ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主なモジュール構成：

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py (score_news エクスポート)
    - news_nlp.py                  — ニュースNLP（OpenAI 呼び出し、ai_scores への書き込み）
    - regime_detector.py           — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - pipeline.py                  — ETL メイン / run_daily_etl 等
    - etl.py                       — ETLResult の再エクスポート
    - jquants_client.py            — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py            — RSS 収集・前処理
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py       — マーケットカレンダー管理
    - audit.py                     — 監査（audit）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value 等
    - feature_exploration.py       — forward_returns / calc_ic / factor_summary / rank
  - ai/ (上記)
  - research/ (上記)
  - その他: strategy, execution, monitoring などのサブパッケージは __all__ に含まれます（将来拡張を想定）

---

## 運用上の注意

- 環境変数の自動読み込みはプロジェクトルートの検出 (.git または pyproject.toml) を行っています。CI / テストで自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用する箇所は API コスト・レート制限に注意してください（モジュール側でリトライ等しているものの、運用設定の確認を推奨します）。
- ETL は部分失敗を許容する設計です。run_daily_etl の戻り値（ETLResult）を確認して品質問題の有無を監視してください。
- DuckDB ファイルのバックアップやスキーマ変更には注意してください（audit テーブルは削除しない前提の設計です）。

---

## 貢献 / テスト

- ユニットテストやモックを用いたテストを推奨します。AI / ネットワーク呼び出し箇所は差し替え可能（関数を patch するなど）な設計になっています。
- コードスタイルや型アノテーションが豊富に使われています。pull request の際はローカルテストを行ってください。

---

README はこのリポジトリの現状コードを基に書かれています。利用・運用にあたっては各モジュールのドキュメント文字列（docstring）を参照してください。質問や追加で README に載せたいサンプルがあれば教えてください。