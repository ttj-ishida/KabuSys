# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、マーケットカレンダー管理、J-Quants / kabu API クライアント等の機能を提供します。

---

目次
- プロジェクト概要
- 主な機能
- 要件
- セットアップ手順
- 環境変数（設定項目）
- 使い方（簡易サンプル）
- ディレクトリ構成（主要ファイル説明）
- 注意事項 / 設計方針の要点

---

## プロジェクト概要

KabuSys は日本株に特化したデータパイプラインと研究（Research）・戦略（Strategy）開発のための共通ライブラリ群を提供します。主な用途は以下の通りです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）および市場レジーム判定
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）用の DuckDB スキーマ初期化
- kabuステーション等の発注インターフェースや監視は別モジュール（execution/monitoring）で想定

設計上、バックテスト・ルックアヘッドバイアスを避けるために「target_date を明示して過去データだけを参照する」設計になっています。また、API 呼び出しはフェイルセーフ（失敗時はスキップやデフォルト値）になるよう意図されています。

---

## 主な機能（一部）

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（トークン管理、ページネーション、レート制御、保存関数）
  - market_calendar 管理（営業日判定・next/prev_trading_day 等）
  - ニュース収集（RSS, SSRF 対策, 正規化）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ用スキーマの初期化（init_audit_db / init_audit_schema）
  - 統計ユーティリティ（zscore 正規化 など）
- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でスコアリング、ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量探索（forward returns, IC, rank, summary）

---

## 要件

- Python 3.10+
- 利用推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / OpenAI / RSS フィード等）
- J-Quants リフレッシュトークン、OpenAI API キーなどの認証情報

（プロジェクトをパッケージ化している場合は requirements.txt を用意してください。ここでは主要な依存を上に示します。）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （パッケージ化されている場合は pip install -e . や requirements.txt を使用）

4. 環境変数を準備
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると自動的に読み込まれます（OS 環境変数 ＞ .env.local ＞ .env の優先順）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（settings で参照される主なキー）

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabu API のパスワード（発注関連で使用）

任意（デフォルトあり／機能に応じて使用）
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用。関数引数でも渡せます）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（設定していないと通知は行われません）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意: Settings クラスは未設定の必須変数に対して ValueError を送出します（例: JQUANTS_REFRESH_TOKEN が無いと get_id_token が失敗します）。

---

## 使い方（簡易サンプル）

以下は最小限の呼び出し例（DuckDB を使う想定）です。

1) DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニューススコアリング（target_date を明示）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーを環境変数に設定するか、api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 19))
print("scored stocks:", n)
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 19))  # OpenAI API key must be set or passed
```

5) 監査 DB を初期化（監査用の DuckDB ファイルを作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

--- 

## ディレクトリ構成（主要ファイルと役割）

（ライブラリのルートが `src/kabusys` である想定）

- src/kabusys/__init__.py
  - パッケージ定義、version

- src/kabusys/config.py
  - 環境変数読み込みロジック（.env 自動読み込み）、Settings クラス（全設定を集中管理）

- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
  - news_collector.py — RSS フィード収集・前処理（SSRF 対策、正規化）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログ（テーブル定義・初期化・init_audit_db）
  - その他（podium 用ユーティリティ等）

- src/kabusys/ai/
  - news_nlp.py — ニュースを銘柄ごとに集約して OpenAI でセンチメントスコアを算出、ai_scores に保存
  - regime_detector.py — ETF MA200 とマクロニュース LLM を合成して market_regime を算出
  - __init__.py — score_news の公開

- src/kabusys/research/
  - factor_research.py — モメンタム、ボラティリティ、バリュー系ファクター定義
  - feature_exploration.py — 将来リターン計算、IC、ランク関数、統計サマリ
  - __init__.py — 研究用公開 API

- src/kabusys/ai, /data, /research はそれぞれの責務ごとにモジュールが整理されています。

---

## 注意事項 / 設計方針（抜粋）

- ルックアヘッドバイアス対策：多くの関数は内部で date.today() を参照せず、target_date を明示することを前提に実装されています。バックテスト利用時は target_date を必ず明示してください。
- 自動 .env 読み込み：プロジェクトルート（.git または pyproject.toml の存在）を基準に .env / .env.local を自動ロードします。CWD に依存しない探索です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- API 呼び出しの堅牢性：OpenAI / J-Quants の呼び出しにはリトライ・指数バックオフ・レート制御等が組み込まれており、429 / タイムアウト / 一時的なネットワークエラーを考慮します。LLM の応答パース失敗時はフェイルセーフでデフォルト値やスキップを行います。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE）で実装されています。
- ニュース収集では SSRF 対策、トラッキングパラメータ除去、XML パースの安全化（defusedxml）を行っています。

---

## よくある利用例（ヒント）

- バッチで毎朝 run_daily_etl を実行してデータ更新 → その後研究モジュールでファクターを計算 → 戦略層でシグナル生成 → 監査テーブルに書き出してから発注処理へ。
- OpenAI を使う処理は API キーを環境変数にセットするか、関数呼び出し時に api_key を渡すことが可能です（テストでキーを差し替えたい場合などに便利）。

---

README は概要と利用方法を中心にまとめました。より詳しい API ドキュメントや開発ガイド（ユニットテスト、CI 設定、パッケージング手順など）が必要であれば、追加で作成します。