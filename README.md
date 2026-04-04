# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ（約定トレース）、運用用設定管理などを含みます。

主な設計方針：
- ルックアヘッドバイアス回避（date.now を直接参照せず、target_date を明示する設計）
- DuckDB ベースのローカルデータストア（冪等保存 / ON CONFLICT を多用）
- 外部 API 呼び出しはリトライ・レート制御を備えた安全設計
- テスト容易性を意識したトークン注入 / モックポイントを提供

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検査（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）取得・保存（fetch/save）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新・バックフィル機能を備えた run_daily_etl 等のジョブ
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL 実行結果を ETLResult オブジェクトで返却
- ニュース収集（RSS）
  - RSS 取得、前処理、SSRF 対策、トラッキングパラメータ除去
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI を利用）
  - 銘柄ごとのニュース統合センチメントスコア生成（score_news）
  - レート制御 / バッチ処理 / JSON Mode を利用した結果検証
- 市場レジーム判定
  - ETF（1321）200日MA乖離 + マクロニュースセンチメントの合成による日次レジーム判定（score_regime）
  - LLM 呼び出しはフェイルセーフ（失敗時は中立扱い）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- 研究用（Research）
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC 計算、統計サマリー、Z スコア正規化

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があればそれを使ってください: pip install -r requirements.txt）

4. パッケージを開発モードでインストール（任意）
   - リポジトリルートで:
     - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます（読み込み順: OS env > .env.local > .env）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（少なくともテスト・実行する機能に応じて設定してください）:
- JQUANTS_REFRESH_TOKEN : J-Quants 用リフレッシュトークン（fetch/save に必要）
- KABU_API_PASSWORD : kabuステーション API を使う場合
- OPENAI_API_KEY : News NLP / Regime 判定で必要（score_news / score_regime にわたすことも可）

その他オプション:
- KABUSYS_ENV : development / paper_trading / live （デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH : デフォルト data/kabusys.duckdb
- SQLITE_PATH : 監視DB用デフォルト data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID : LINE 通知を使う場合

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な例）

以下はライブラリを直接 Python から呼ぶ基本例です。すべて target_date は明示的に与えることが推奨されています（ルックアヘッド回避）。

- DuckDB 接続を作る:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを計算して ai_scores に保存する:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていれば api_key は不要
n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

- 市場レジームをスコアリングする:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026,3,20))  # OpenAI のキーは環境変数または api_key 引数で指定
```

- 監査ログスキーマを初期化（別 DB にすること推奨）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn を使用して監査ログを操作
```

- ファクター計算（research）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

- マーケットカレンダーのユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_trading = is_trading_day(conn, date(2026,3,20))
next_day = next_trading_day(conn, date(2026,3,20))
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数でキーを注入可能。テスト時には該当モジュールの _call_openai_api を patch してモックすることが想定されています。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コードは空チェックを行っています。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETL の公開インターフェース（ETLResult 再エクスポート）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 共通統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

各モジュールは docstring と設計方針が充実しており、意図や使い方がコメントにまとまっています。

---

## 運用上の注意 / ベストプラクティス

- 環境（KABUSYS_ENV）は production/live と paper_trading を明確に分けて設定してください（is_live / is_paper プロパティあり）。
- OpenAI / J-Quants など外部 API のキーは secrets 管理（Vault 等）を推奨。ローカルでは .env.local を .env より優先して使うことで機密保持がしやすくなります。
- ETL は部分失敗しても他ステップを継続する設計です。ETLResult の errors / quality_issues を参照して運用判断を行ってください。
- news_collector は外部 URL をフェッチするため SSRF 対策（実装済）に依存しますが、実行環境のネットワークポリシーも合わせて調整してください。
- DuckDB のファイルはバックアップ / スナップショット運用を検討してください（データ損失リスク軽減）。

---

この README はコードの概要と利用の手引きに焦点を当てています。より詳しい設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がある場合はそちらも参照してください。質問や改善案があればお知らせください。