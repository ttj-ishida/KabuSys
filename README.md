# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（一部モジュール群）。  
本リポジトリはデータ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ等のユーティリティを提供します。

> 注意: このパッケージは「取引ロジック／ブローカー接続」を含む完全な運用システムの一部です。実際の発注を行う前に十分な確認とテストを行ってください。

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価日足・財務データ・マーケットカレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損データ、スパイク（急騰／急落）、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集・処理
  - RSS フィード取得、前処理、raw_news への冪等保存（news_collector.fetch_rss ほか）
  - SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去等の安全設計
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント評価（gpt-4o-mini を想定）：score_news
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM を合成）：score_regime
  - API 呼び出し時のリトライ・フォールバック実装
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等ファクター計算（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）、Zスコア正規化等
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化・管理（data.audit.init_audit_db / init_audit_schema）
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト（kabusys.config.settings）
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要環境

- Python >= 3.10（typing の | を使用しているため）
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで十分な箇所もありますが、上記は主要依存）

インストール方法はプロジェクトの配布方法に依存しますが、開発中は src レイアウトに対して editable インストールすることが便利です。

例:
```
python -m pip install -U pip
python -m pip install -e ".[dev]"   # setup.cfg/pyproject で extras があれば
# または最低限:
python -m pip install duckdb openai defusedxml
python -m pip install -e .
```

（リポジトリに requirements.txt / pyproject.toml があればそれに従ってください）

---

## 環境変数（必須 / 任意）

kabusys は環境変数から設定を読み込みます（.env / .env.local も自動で読み込みます。プロジェクトルートに .git または pyproject.toml がある場合）。

主な必須変数（実行する機能により異なります）:

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（ETL、jquants_client.get_id_token）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabu ステーション API を使う場合
- OPENAI_API_KEY — OpenAI を用いる機能（score_news / score_regime 等）で必要

システム設定（任意）:

- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite DB パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動読み込みを無効化

例 .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（基本的な流れ）

1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - python -m pip install -r requirements.txt もしくは個別インストール
4. .env を作成して必要な環境変数を設定
   - .env.example があれば参照して作成
5. DuckDB データディレクトリを準備（デフォルトは data/）
   - mkdir -p data
6. （オプション）監査データベースを初期化
   - python スクリプト上で data.audit.init_audit_db("data/audit.duckdb") を呼ぶ

---

## 使い方（主要な API と実行例）

以下はライブラリの代表的な使い方例です。実行は Python スクリプトや Cron / ワーカー内で行います。

- DuckDB 接続の作成例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI 必須）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY を使用するか、api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} stocks")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

moms = calc_momentum(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
```

- データ品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- 監査データベース初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はスキーマを作成し接続を返します
```

- 設定値へのアクセス:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV の判定
```

---

## ディレクトリ構成（主要ファイル・説明）

（src レイアウトを想定）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングする主関数 score_news（バッチ／チャンク処理、検証、DB 書込）
    - regime_detector.py — MA200 とマクロニュースを合成して market_regime を算出する score_regime
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・レート制限）
    - pipeline.py — ETL パイプライン（run_daily_etl / 個別 ETL 実行）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS フィード取得・前処理・安全対策
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック群（各チェックは QualityIssue リストを返す）
    - audit.py — 監査ログスキーマの作成 / 初期化ヘルパー
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー 等
  - ai/（上記と同列）や research/ は研究・分析用途のモジュールが中心

---

## 運用上の注意点 / ベストプラクティス

- OpenAI キーや J-Quants のトークンは機密情報です。CI/CD や運用環境では Secrets マネージャーを利用してください。
- .env の自動読み込みは便利ですが、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして無効化できます。
- DuckDB のスキーマ設計（テーブル作成）は別のスクリプト / migration で管理する想定です。本ライブラリは ETL/保存ロジックを提供しますが、初期スキーマ定義は適宜用意してください。
- LLM/API 呼び出しはコストとレイテンシーが発生します。バッチサイズ・リトライ設定等は実運用に合わせて調整してください。
- 本コードベースは Look-ahead Bias を避ける設計（target_date 未満しか参照しない等）を重視しています。バックテスト等で使用する際はその設計方針に従ってください。

---

もし README に追加したい内容（例: 実際のテーブルスキーマ、運用 Cron の例、CI テストコマンド、開発環境のセットアップ手順の詳細）があれば教えてください。必要に応じて .env.example のテンプレートや簡易の起動スクリプト例も作成できます。