# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J‑Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP スコアリング、ファクター計算、監査（オーディット）スキーマ、そして市場レジーム判定など、バックテスト〜実運用に必要な基盤処理群を提供します。

主な目的は「データプラットフォーム + 研究（Research） + 戦略（Strategy） + 発注監視（Audit/Execution）」を分離したモジュール設計で実装し、ルックアヘッドバイアスや冪等性、外部 API の頑健な取り扱いを重視したことです。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（必要に応じて無効化可）
  - 必須環境変数の明示・取得ヘルパ

- データ取得・ETL（J‑Quants）
  - 株価日足（OHLCV）の差分取得・保存（ページネーション・レート制御・リトライ）
  - 財務データの差分取得・保存
  - JPX マーケットカレンダー取得・保存（ON CONFLICT による冪等保存）
  - ETL パイプライン（run_daily_etl）と品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS 取得（SSRF 対策、リダイレクト検査、サイズ制限）
  - テキスト前処理・記事 ID 正規化
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント -> ai_scores テーブルへの書き込み
  - レート制限・リトライ・レスポンス検証実装

- 市場レジーム判定（Regime Detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で 'bull' / 'neutral' / 'bear' 判定
  - OpenAI API 呼び出しに対するリトライ・フォールバック実装

- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算（duckdb を用いた SQL + Python 実装）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査（Audit）スキーマ
  - signal_events / order_requests / executions を含む監査テーブルの初期化ユーティリティ（DuckDB）
  - 監査用のインデックスと制約、冪等性設計

---

## 動作環境・依存

- Python 3.10 以上
  - 型ヒント（A | B 形式）や一部の記法を利用しているため 3.10+ を推奨します。
- 主な Python パッケージ（インストール例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J‑Quants API、OpenAI、RSS ソース、kabu ステーション等）

requirements.txt がない場合は最低限以下をインストールしてください（例）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

パッケージを editable インストールするにはリポジトリルートで:

```bash
pip install -e .
```

（セットアップスクリプトが存在する場合はそちらを利用）

---

## 環境変数（主要）

config.Settings から参照される主要環境変数:

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視等の SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等の監視設定
- KABUSYS_ENV: environment （development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（ai モジュール内で参照）

自動 .env 読み込みについて:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <repo_url>
cd <repo_root>
```

2. Python 仮想環境の作成・有効化

```bash
python -m venv .venv
source .venv/bin/activate
```

3. 依存パッケージをインストール

```bash
pip install -r requirements.txt   # もし用意されていれば
# または最低限:
pip install duckdb openai defusedxml
```

4. 環境変数の準備

- `.env.example` を参考に `.env` を作成し、上記の必須環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）を設定します。
- または CI/実行環境のシークレットとして設定してください。

5. DuckDB の初期化（監査 DB 例）

Python REPL またはスクリプトで:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

---

## 使い方（主な関数・例）

以下はライブラリ関数の簡単な利用例です。多くは duckdb 接続を受け取るため、まず DuckDB を開くことが前提です。

- DuckDB 接続を作る:

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（J‑Quants からデータ取得〜品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア生成（score_news）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
print(f"書込件数: {n_written}")
```

- 市場レジーム判定（score_regime）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
```

- 研究用ファクター計算（例: モメンタム）:

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
```

- 統計ユーティリティ（Zスコア正規化）:

```python
from kabusys.data.stats import zscore_normalize

normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
```

- 監査スキーマ初期化（既存 DB に追加）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注:
- OpenAI 呼び出しを行う関数（score_news, score_regime など）は API キーを引数で渡すか、環境変数 `OPENAI_API_KEY` を設定しておく必要があります。
- J‑Quants 実行関数（fetch/save 等）は settings.jquants_refresh_token を参照します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソースは `src/kabusys` に配置されています。主なファイル／モジュールは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J‑Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult などの公開インターフェース
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py             — RSS 収集・整形
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility 計算
    - feature_exploration.py        — 将来リターン、IC、統計サマリー
  - ai/ (詳述済)
  - research/ (詳述済)

（実際のリポジトリにはさらに strategy / execution / monitoring などのモジュールが想定されています。__all__ に含まれている名前からも構成方針が読み取れます）

---

## 設計上の注意点・運用のポイント

- ルックアヘッドバイアス対策
  - 多くの関数は内部で現在時刻を直接参照せず、引数の target_date を基準に処理します。バックテストや日次バッチで正しく再現性を保つための設計です。

- 冪等性
  - J‑Quants からの保存処理は ON CONFLICT DO UPDATE を利用しており、再実行しても重複や二重書き込みが起きないようにしています。

- フォールバック / フェイルセーフ
  - OpenAI 呼び出しや API 失敗時は、完全停止ではなくフォールバック値（例: macro_sentiment=0.0）で継続する実装が多く含まれます。運用ではログ監視を必須にしてください。

- セキュリティ
  - RSS 取得では SSRF 対策（ホストがプライベートかの検査、リダイレクト検査、許可スキームの制限等）を実装しています。
  - XML パースには defusedxml を利用しています。

---

## 追加情報 / 開発者向け

- 自動 .env 読み込み
  - プロジェクトルートを `.git` または `pyproject.toml` によって検出し `.env` / `.env.local` を自動読み込みします。テスト時や特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化可能です。

- ロギング
  - 各モジュールは標準ライブラリの logging を利用しています。アプリケーション側でハンドラ・フォーマット・ログレベルを設定してください。

- テスト
  - OpenAI / ネットワークリソース呼び出し部はモックしやすいように内部呼び出しを分離しています（例: _call_openai_api をパッチする等）。

---

この README はコードベースの実装に基づいた概要ドキュメントです。個別の関数やスキーマの詳細は該当モジュールの docstring を参照してください。必要があれば導入手順のスクリプト化、コンテナ化、CI 設定例 などの追補ドキュメントを作成できます。必要であれば続けて作成します。