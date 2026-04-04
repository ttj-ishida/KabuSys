# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）

短い概要とユーティリティ群を含み、データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを提供します。設計では「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時は継続）」を重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価・財務データ・市場カレンダー）
  - 差分ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集・NLP
  - RSS 収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いたニュースセンチメント（銘柄毎スコア: score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離とマクロニュースの LLM センチメントを統合（score_regime）
- 研究ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計
- 監査（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（init_audit_schema / init_audit_db）
- 環境変数管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出、優先度 OS > .env.local > .env）
  - 自動読み込み無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要環境 / 依存パッケージ（例）

- Python 3.10+（型ヒントで | 型を使うため）
- 主要依存（抜粋）
  - duckdb
  - openai (v1 SDK)
  - defusedxml
- その他: 標準ライブラリ（urllib, datetime, logging など）

requirements.txt の例（プロジェクト側で管理してください）:
```
duckdb
openai
defusedxml
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt
   ```
   （または個別に pip install duckdb openai defusedxml 等）

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. 必須の環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等がある場合）
   - その他（オプション）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB 用）
     - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEM/DISK 閾値 等

.env の簡単な例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=passwd123
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL から呼び出す例です。DuckDB のパスは settings.duckdb_path に合わせてください。

- DuckDB 接続の準備
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # ファイル DB または ":memory:"
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026,3,20))
print(res.to_dict())
```

- ニュースセンチメントをスコア付け（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジームスコアを計算（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20), api_key="sk-xxxx")
```

- カレンダー更新ジョブ（夜間バッチの一部）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("保存件数:", saved)
```

- 監査用 DB 初期化（監査専用ファイル）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit に対して監査ログを保存できます
```

- データ品質チェック（全チェック）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- score_news / score_regime は OpenAI API キー（api_key 引数 または 環境変数 OPENAI_API_KEY）が必要です。未設定だと ValueError を投げます。
- 多くの関数は「ルックアヘッドバイアス防止」のため datetime.today() / date.today() を直接参照せず、target_date を明示することを推奨します。
- J-Quants API 呼び出しにはレート制限やリトライが組み込まれていますが、ID トークンの自動リフレッシュやキャッシュ動作を把握しておいてください。

---

## ディレクトリ構成（主要ファイル）

（src/ 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- 市場カレンダー管理（is_trading_day 等）
    - news_collector.py             -- RSS 収集・前処理
    - quality.py                    -- データ品質チェック
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - audit.py                      -- 監査ログスキーマ初期化 / init_audit_db
    - etl.py                        -- ETLResult エクスポート
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py        -- 研究用ユーティリティ（forward returns, IC, summary）
  - ai/、research/、data/ はさらに細かいユーティリティや SQL を含みます。

---

## 設計上の重要な注意点（運用・開発者向け）

- ルックアヘッドバイアス防止: 多くの関数は target_date を明示することを前提とし、内部で現在日時を勝手に使いません。バックテストや再現性のために target_date を指定してください。
- 冪等性: ETL の保存処理や監査スキーマは可能な限り冪等（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING）で実装されています。
- エラー戦略: 外部APIの失敗時はフェイルセーフで継続する（スコアを 0 にフォールバックしたり、失敗したチャンクだけスキップする等）。重要な致命エラーはログに上げ、戻り値・ETLResult で把握できるようにしています。
- セキュリティ:
  - RSS 取得には SSRF 対策（プライベートIP拒否、リダイレクト検査）を実装しています。
  - defusedxml を使って XML 脅威に備えています。
- テスト時の挙動:
  - 環境変数自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（ユニットテストで .env を読み込ませたくない場合など）。

---

## 追加情報 / 貢献

- この README はコードベースの公開API と内部設計のサマリを目的としています。実際の運用では追加の監視、ロギング設定、リトライポリシー調整、シークレット管理（Vault 等）を行ってください。
- バグ修正や機能追加は PR ベースで歓迎します。変更を行う際は既存のルックアヘッドバイアス・冪等性の前提を破らないよう注意してください。

---

必要であれば、README に具体的な .env.example、より詳細な API 使用例（J-Quants のレスポンスフォーマットを踏まえた ETL フローの実例）、あるいは Docker / systemd の運用例（監視・PID 管理など）を追加できます。どの情報が欲しいか教えてください。