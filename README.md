# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ集です。  
ETL（J-Quants）, ニュースセンチメント（OpenAI）, ファクター計算や監査ログ等、アルゴリズム取引に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AIベースのニュース評価・市場レジーム判定・監査ログなどを統合的に扱うためのモジュール群です。主な用途はバックテストや研究環境、ペーパー・ライブ運用のデータ基盤と戦略レイヤーの補助です。

設計上のポイント：
- DuckDB をデータレイクとして利用（ローカルファイルまたは :memory:）
- J-Quants API 経由で株価・財務・市場カレンダーを差分取得（レート制御・リトライ実装）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode 利用）
- ルックアヘッドバイアスに配慮（内部で date.today() を直接参照しない設計）
- ETL / 品質チェックは失敗時も全体を停止せず問題を収集する方式

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からのデータ取得 / DuckDB への保存（差分更新・ページネーション対応）
  - pipeline: 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - news_collector: RSS 収集 → 前処理 → raw_news 保存（SSRF 対策、トラッキング除去）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: z-score 正規化などの統計ユーティリティ
  - audit: 取引フローの監査テーブル初期化・管理（signal / order_request / execution）

- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを生成し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を作成

- research
  - factor_research: momentum / value / volatility / liquidity 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー

- config
  - 環境変数管理（.env の自動読み込み / 必須変数チェック / env モード判定）

---

## セットアップ手順

以下は基本的な導入手順の例です。実際のプロジェクトでは仮想環境やバージョン管理を推奨します。

1. Python バージョン
   - Python 3.10+ を想定（typing 機能を利用）

2. リポジトリをクローンしてパッケージをインストール
   - 開発中: pip install -e .
   - 依存パッケージ（例）:
     - duckdb
     - openai
     - defusedxml
   - 実際の requirements はプロジェクトに合わせて管理してください。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 読み込み順序（優先度）: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須 for ETL）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - KABU_API_BASE_URL: kabuステーションの Base URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: プロセス監視関連
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

4. データベースディレクトリ作成
   - DUCKDB_PATH（例: data/）の親ディレクトリを作成しておくと便利です。

---

## 使い方（主要な例）

以下は Python スクリプトやインタラクティブシェルからの呼び出し例です。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア生成（OpenAI API キーは環境変数 OPENAI_API_KEY で指定可能）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査ログスキーマ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

テスト上のヒント:
- OpenAI 呼び出しは内部で _call_openai_api を使用しているため、unittest.mock.patch で差し替えることで外部APIへの依存を排除できます（news_nlp と regime_detector はそれぞれ独立した private 関数を持っています）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（OpenAI）
    - regime_detector.py              — 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - pipeline.py                     — ETL パイプライン・run_daily_etl 等
    - calendar_management.py          — 市場カレンダー管理・営業日ユーティリティ
    - news_collector.py               — RSS 収集・前処理
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore）
    - audit.py                        — 監査ログテーブル定義 / 初期化
    - etl.py                          — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum/value/volatility）
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー
  - ai/、research/、data/ 以下に補助モジュール多数

---

## 運用上の注意・設計上の特記事項

- ルックアヘッドバイアス防止
  - 多くの関数は内部で date.today() を直接参照しないよう設計されています。バックテスト用途では target_date を明示的に渡してください。

- API キーの取り扱い
  - J-Quants は refresh token を使用し id_token を自動取得してページネーション間で使い回します。
  - OpenAI の呼び出しは gpt-4o-mini（JSON mode）を想定しています。レスポンスのバリデーションを厳格に行います。

- エラーハンドリング
  - ETL・品質チェックは fail-fast せず問題を収集して呼び出し元に戻すことで運用判断を柔軟に行えるようにしています。
  - 外部 API 呼び出しにはリトライやバックオフを実装しています（J-Quants は 120 req/min のレート管理）。

- テストとモック
  - ネットワーク呼び出しや OpenAI 呼び出しは差し替え可能なプライベート関数で分離されているためユニットテストが容易です。

---

## サポート / 拡張ポイント

- 監視（monitoring）や実際の発注（execution）モジュールは別途統合して運用することを前提としています。
- ニュースソースや RSS リストは news_collector の DEFAULT_RSS_SOURCES を拡張してください。
- ファクター群やモデルは research 以下を拡張して追加できます。

---

必要であれば、以下も作成できます：
- .env.example（推奨する環境変数テンプレート）
- Docker / systemd ユニットの実行例
- サンプル ETL 実行スクリプトや cron 設定例

ご要望があれば README に追記・具体化します。