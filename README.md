# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得（ETL）・品質チェック・特徴量計算・ニュースベースの自然言語処理（LLM）・市場レジーム判定・監査ログなどを備えた自動売買基盤のライブラリ群です。主に DuckDB をデータプラットフォームとして利用し、J-Quants API / RSS / OpenAI（gpt-4o-mini）を連携して、研究（Research）・運用（Execution）・監視（Monitoring）向けの機能を提供します。

設計上のポイント
- ルックアヘッドバイアス回避（バックテストでの正当性を意識）
- DuckDB への冪等保存（ON CONFLICT / UPDATE）
- 外部 API 呼び出しに対するリトライ・バックオフ・レート制御
- ニュース収集での SSRF 対策、XML パース安全化（defusedxml）
- 監査ログと UUID によるトレーサビリティ

---

## 主な機能（抜粋）
- ETL（jquants_client 経由）
  - 株価日足（OHLCV）取得・保存（fetch / save）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分取得・バックフィル・ETL 実行エントリ（run_daily_etl）
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（news_collector）
  - RSS フィード収集、安全な URL 正規化・ID 生成・前処理・冪等保存
- ニュース NLP（ai.news_nlp）
  - OpenAI を用いた銘柄別ニュースセンチメントのバッチ評価（ai_scores へ保存）
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュース感情を合成して日次レジーム判定
- 研究用ユーティリティ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）等
- 監査ログ（data.audit）
  - signal_events / order_requests / executions テーブルの初期化とインデックス作成
- J-Quants クライアント（data.jquants_client）
  - レートリミッタ・認証（refresh token → id_token）・ページネーション対応

---

## 必要条件
- Python 3.10 以上
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

開発環境ごとに requirements.txt が用意されている場合はそちらを使用してください。最低限のインストール例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

パッケージとしてセットアップできる場合:
```bash
pip install -e .
```

---

## 環境変数（必須 / 重要）
このプロジェクトは .env（または環境変数）から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（Settings により参照される）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD — kabuステーション API のパスワード（注文連携用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（監視通知など）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス PID 保存ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

.env.example を参考に .env を作成してください。

---

## セットアップ手順（簡易）
1. リポジトリをクローン（またはソースを入手）
2. Python 環境を用意（venv など推奨）
3. 依存パッケージをインストール
   - pip install -r requirements.txt （あれば）
   - or pip install duckdb openai defusedxml
4. .env をプロジェクトルートに配置し必要なキーを設定
5. DuckDB 用ディレクトリ（デフォルト data/）を作成（必要なら）
   - mkdir -p data
6. 初期化（監査テーブル等が必要な場合）
   - 下記 Usage セクション参照

---

## 使い方（代表的な API）
以下はライブラリ呼び出しの簡易例です。実行は Python スクリプトや interactive セッションから行えます。

1) DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（AI）でスコアを付与する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} codes")
```

3) 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査 DB の初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以後 conn を使って監査テーブルへ書き込み / クエリ可能
```

注意点
- OpenAI 呼び出しには API キーが必要です（api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定）
- ETL / AI 呼び出しは外部 API を使うため実行時のネットワーク環境とレート制限に注意
- DuckDB のバージョン依存で executemany の挙動が変わる場合があるため、大きなバルク操作は考慮が必要

---

## ディレクトリ構成（主要ファイルと説明）
（リポジトリの src/kabusys 以下を抜粋）

- src/kabusys/__init__.py
  - パッケージ定義、エクスポート
- src/kabusys/config.py
  - 環境変数 / .env の自動読み込み、Settings クラス
- src/kabusys/ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.py — MA200 とニュースセンチメントを合成し market_regime を作成
- src/kabusys/data/
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL のメイン実行ルーチン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理・保存ロジック（SSRF 対策等）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付整合性）
  - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
  - calendar_management.py — 市場カレンダー管理と営業日ロジック
  - audit.py — 監査ログテーブル定義 / 初期化
- src/kabusys/research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - __init__.py — 主要ユーティリティのエクスポート

（上記以外に execution, monitoring, strategy 等のサブパッケージが想定されますが、今回の提供コードでは一部モジュールが中心です）

---

## 実装上の注意（運用・拡張）
- Look-ahead バイアス回避のため、関数は基本的に target_date を明示的に受け取り、内部で date.today() を参照しないよう設計されています。
- 外部 API 呼び出しは堅牢化（リトライ、バックオフ、401 リフレッシュ対応、レートリミッタ）されているため、運用時はログを確認して問題を特定してください。
- ニュース周りは LLM の返答整形・バリデーションを行っており、異常時はフェイルセーフ（スコア 0.0）にフォールバックします。
- DuckDB スキーマやテーブル作成は audit.init_audit_schema 等で行えます。既存データの扱いに注意してください（DDL の冪等性は考慮されていますが、運用時はバックアップ推奨）。

---

## テスト・モックについて
- OpenAI 呼び出しやネットワーク I/O を含む部分はユニットテストでモックしやすいようインターフェースや内部呼び出し関数（例: _call_openai_api, _urlopen）を分離してあります。CI 上ではこれらをモックしてテストを実行してください。

---

ライセンス: このリポジトリ内に明示的なライセンスファイルがない場合は、使用前にライセンス条件を明確にしてください。

問題や追加で README に含めたい情報（セットアップスクリプト例、完全な requirements.txt、運用手順など）があれば教えてください。README を用途（開発者向け / 運用者向け / ユーザー向け）に合わせて調整できます。