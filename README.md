# KabuSys

日本株向けの自動売買・データプラットフォームのライブラリセットです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを提供します。

> 注意: このリポジトリはライブラリ実装の抜粋です。実運用には各種 API キーの管理、運用監視、バックテスト、リスク管理ロジック等が必要です。

## 主な機能
- データ取得（J-Quants）と DuckDB への冪等保存
  - 株価日足（OHLCV）、財務（四半期）データ、JPX カレンダーなど
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分更新 / バックフィル / 品質チェックの統合実行（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue で集約）
- ニュース収集・前処理
  - RSS 取得、URL 正規化、SSRF 対策、記事の冪等保存
- ニュース NLP（OpenAI を用いたセンチメント）
  - 銘柄別ニューススコアリング（score_news）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定（score_regime）
- 監査ログ（信号→発注→約定のトレース可能なテーブル群）
  - audit スキーマ初期化、専用 DuckDB DB の作成ユーティリティ
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）、将来リターン、IC 計算、Zスコア正規化

## 必要条件
- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
（ネットワーク系は標準ライブラリを多用）

インストール例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# 開発環境としてパッケージを編集可能にインストールする場合
python -m pip install -e .
```

## 環境変数 / .env
自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN  — J-Quants リフレッシュトークン（fetch 系に必要）
- KABU_API_PASSWORD     — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN       — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      — Slack 送信先チャンネル ID
- OPENAI_API_KEY        — OpenAI 呼び出しに使用（score_news / score_regime で参照）

オプション
- KABUSYS_ENV           — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH           — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（"1" 等）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（簡易）
1. Python 3.10+ を用意
2. 依存ライブラリをインストール（上記参照）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB 用ディレクトリ作成（settings.duckdb_path の親ディレクトリ）
   - 例: data/ を作る（save 関数が自動で作成することもありますが、明示的に作るのが安全）
5. 必要に応じて監査 DB を初期化

## 使い方（代表的な例）

Python REPL やスクリプトから直接利用できます。以下はサンプル。

- 設定と接続の準備
```python
import duckdb
from kabusys.config import settings

# DuckDB に接続（ファイルまたは ":memory:"）
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を指定しなければ今日を対象に実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（前日 15:00 JST 〜 当日 08:30 JST）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

- 監査 DB の初期化（監査専用 DB を分けたい場合）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 監査用 DB を別ファイルで作る例
audit_conn = init_audit_db("data/audit.duckdb")
```

- OpenAI トークンを関数引数で直接指定することも可能（api_key 引数）。テスト時は関数をモック可能。

## ログと実行モード
- KABUSYS_ENV により is_live / is_paper / is_dev が切り替わります（設定チェック機能あり）
- LOG_LEVEL で出力レベルを制御できます（デフォルト INFO）

## テストとモック
- OpenAI 呼び出しやネットワーク呼び出しは内部でラップされており、ユニットテスト時は該当関数を patch して差し替え可能（例: kabusys.ai.news_nlp._call_openai_api をモック）。

## ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング
    - regime_detector.py            — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + 保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インターフェース (ETLResult)
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダー管理（営業日判定等）
    - news_collector.py             — RSS ニュース収集
    - audit.py                      — 監査ログスキーマ / 初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py         — 将来リターン、IC、統計要約
  - research: データ解析・研究向けユーティリティ群

（上記は主要モジュールの抜粋です。詳細はソースコードを参照ください）

## 注意事項 / 設計上のポイント
- Look-ahead bias（将来情報リーク）を避ける設計思想が随所に組み込まれています。
  - datetime.today() 等を暗に参照しない、DB クエリで date < target_date 等の排他条件を適用する等。
- API 呼び出しはフェイルセーフで、失敗時にシステム全体を停止させない設計（ログ記録・部分スキップ）です。
- DuckDB との互換性や executemany の挙動を考慮した実装がされています（例: 空パラメータの扱い注意）。
- ニュース収集では SSRF 防止、XML の安全なパース、サイズ制限などセキュリティ対策が実装されています。

## 開発・貢献
- コードはモジュールごとに単体テストが書きやすい設計になっています（依存注入 / API 呼び出しのラップ等）。
- PR や Issue による改善提案を歓迎します（この README はリポジトリ抜粋に基づく概要です）。

---

README の内容で追加したい項目（例: CI、詳しいデータベーススキーマ、実運用時の注意点など）があれば指示ください。必要に応じて具体的なコマンド例やサンプルスクリプトを追記します。