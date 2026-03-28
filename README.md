# KabuSys

日本株向け自動売買プラットフォームのライブラリ実装。データ取得（J-Quants）、ETL、ニュース収集・NLP、ファクター・リサーチ、監査ログ（約定トレーサビリティ）、および市場レジーム判定等のユーティリティ群を提供します。

主にバッチ ETL、研究（リサーチ）、および AI を用いたニュースセンチメント評価・市場レジーム判定を目的としたモジュール群で構成されています。

---

## 主な特徴

- データ取得 / ETL
  - J-Quants API から株価日足・財務データ・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - ETL の品質チェック（欠損、重複、スパイク、日付不整合）
  - market_calendar の自動更新ジョブ
- ニュース収集・NLP
  - RSS フィードから安全対策（SSRF、XML DoS 対策）を行いつつニュースを収集
  - OpenAI（gpt-4o-mini）による銘柄別ニュースセンチメント評価（JSON mode）
  - チャンク化・リトライ・レスポンス検証などの堅牢な実装
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成して日次レジーム判定
  - Look-ahead バイアス回避設計
- 研究 / ファクター
  - モメンタム・バリュー・ボラティリティ・流動性などのファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal → order_request → execution の階層的監査テーブルを DuckDB に初期化するユーティリティ
  - order_request_id を冪等キーとして二重発注防止
- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定は読み込み時に明示的エラーを出力

設計ポリシー（抜粋）
- ルックアヘッドバイアス回避（関数内で datetime.today()/date.today() を不用意に使わない）
- 冪等性（DB 書き込み）
- API レート制御・リトライ（指数バックオフ）
- 外部呼び出し失敗時のフェイルセーフ（可能な範囲で処理継続）

---

## 必要条件 / インストール

推奨 Python バージョン: 3.10+

必要な主な依存パッケージ（例）:
- duckdb
- openai
- defusedxml

requirements.txt の例:
```
duckdb>=0.10
openai>=1.0
defusedxml>=0.7
```

セットアップ手順（ローカル開発想定）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または個別に pip install duckdb openai defusedxml
3. パッケージを編集可能インストール（任意）
   - pip install -e .

---

## 環境変数 / .env

プロジェクトルート（.git または pyproject.toml がある場所）にある `.env` / `.env.local` を自動で読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主に利用される環境変数（必須・例）:
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      — kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID       — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL              — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- OPENAI_API_KEY         — OpenAI API キー（news_nlp, regime_detector で参照）

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な例）

以下はモジュールを直接呼び出して処理を行う最小例です。DuckDB 接続はライブラリ内でそのまま使用します。

- ETL（日次パイプライン）の実行例:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（銘柄別ニュースセンチメント）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {count}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、conn を使って監査テーブルが存在する状態で操作可能
```

注意点:
- OpenAI 呼び出しを行う関数は api_key 引数または環境変数 OPENAI_API_KEY のいずれかを参照します。キーが設定されていないと ValueError を送出します。
- ETL / API 呼び出しはネットワークや API レート制限の影響を受けます。ログとリトライ挙動を確認してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）
- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラスの提供（自動 .env ロード、必須項目チェック）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント評価（OpenAI を利用、チャンク/バリデーション付き）
  - regime_detector.py — ETF とマクロニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存関数、レート制御、リトライ）
  - pipeline.py — ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl 等）
  - calendar_management.py — 市場カレンダー管理・営業日判定ユーティリティ
  - news_collector.py — RSS ベースのニュース収集（SSRF/DoS 対策、正規化、保存）
  - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py — Zスコア等の統計ユーティリティ
  - audit.py — 監査ログのスキーマ初期化・ユーティリティ
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- research/、ai/、data/ はそれぞれ研究・AI・データパイプライン向けの機能群として設計されています。

---

## 実装上の注意・設計メモ

- Look-ahead バイアス防止:
  - score_news / score_regime 等は target_date に対して「過去のウィンドウ」を明示的に選択します。内部で date.today() を不用意に参照しない点に注意してください。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE または INSERT … ON CONFLICT を利用し、再実行可能になっています。
- API の堅牢性:
  - J-Quants クライアントは固定間隔の RateLimiter（120 req/min）とリトライ・トークン自動更新を行います。
  - OpenAI 呼び出しは JSON mode を用い、エラー・パース失敗時は安全にフォールバックします。
- ニュース収集の安全対策:
  - SSRF 対策、XML 脆弱性対策（defusedxml）、レスポンスサイズ上限、トラッキングパラメータ除去等の実装があります。

---

## 貢献・拡張案

- kabu ステーションへの実際の注文発行モジュール（execution 層）の追加
- Slack/監視系への通知ワークフローの強化
- 単体テスト・統合テストの整備（OpenAI / J-Quants 呼び出しをモック）
- バックテスト用の戦略実行エンジンとの連携

---

この README はコードベースの主要機能・使い方の概要を示しています。詳細な API ドキュメントや運用手順は各モジュールの docstring・関数コメントを参照してください。質問や追記があればお知らせください。