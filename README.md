# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL、ニュース収集、AIによるニュースセンチメント解析、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなど、アルゴリズムトレーディング基盤の主要機能を含みます。

---

## 主な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足・財務・マーケットカレンダーを差分取得・保存（ページネーション・レート制御・リトライ対応）
  - 日次の統合ETLエントリ（run_daily_etl）
- カレンダー管理
  - JPX カレンダーの夜間更新、営業日判定、前後営業日取得、期間内営業日の取得
- ニュース収集
  - RSS フィードから記事取得、URL 正規化、SSRF対策、前処理、raw_news への冪等保存
- AI（LLM）連携
  - ニュースごとの銘柄センチメント解析（news_nlp.score_news）
  - ETF（1321）MA とマクロニュースの組合せによる市場レジーム判定（regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を利用、JSON Mode / 再試行・フェイルセーフ実装
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化
- データ品質チェック
  - 欠損、主キー重複、スパイク、日付不整合（未来日付・非営業日データ）検出
- 監査ログ（Audit）
  - シグナル → 発注 → 約定を UUID でトレースする監査スキーマの初期化・管理（冪等）
- 設定管理
  - .env / .env.local / OS 環境変数からの読み込み、自動ロードの有効/無効切替

---

## 要件 / 依存関係

- Python 3.10+
- 必要パッケージ（一部抜粋）
  - duckdb
  - openai
  - defusedxml
- （その他）標準ライブラリを利用

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

---

## 環境変数（主なもの）

このパッケージは環境変数から設定を読み込みます。必須のもの：

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネルID（必須）
- OPENAI_API_KEY — OpenAI 呼び出し時に未指定の場合に参照される（news_nlp / regime_detector の使用時）

任意（デフォルトあり）:

- KABUSYS_ENV — 環境 "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

.env の自動読み込み:
- プロジェクトルートはこのファイルの位置から上位へ .git または pyproject.toml を探索して決定します。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   ```

3. .env を作成（.env.example を参考に）
   - 必須キーを設定してください（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）

4. DuckDB の初期化（監査DBなど）
   - 監査ログ専用 DB を作る例:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)  # もしくは別パス
     conn.close()
     ```

---

## 使い方（代表的な例）

以下は Python スクリプトや REPL での利用例です。各 API は duckdb.DuckDBPyConnection を受け取ります。

- 設定・接続準備:

```python
from kabusys.config import settings
import duckdb

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（run_daily_etl）:

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースのスコアリング（OpenAI キーを環境変数に設定していれば api_key 引数は不要）:

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを組合せ）:

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマ初期化（既存接続に追加）:

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

注意:
- AI関連関数（score_news / score_regime）は OpenAI API を呼び出します。APIキーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- これらの関数はルックアヘッドバイアスを避けるため、内部で date.today() を直接参照しない設計になっています。target_date を必ず指定するか、意図を明確にしてください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数読み込み・Settings オブジェクト
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント解析（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存関数）
  - pipeline.py — ETL の主要ロジック（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS の取得・前処理・保存
  - quality.py — データ品質チェック群
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログ用スキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — 将来リターン、IC計算、統計サマリー

上記以外にも strategy / execution / monitoring 等のサブパッケージが想定されています（パッケージの __all__ に含まれています）。

---

## 開発・貢献

- テスト: 関数は外部依存（OpenAI 呼び出し、ネットワーク）をモックするように設計されています。ユニットテストでは該当関数を patch して挙動を検証してください。
- コードスタイル / ドキュメント: docstring に設計方針・注意点が記載されています。重要な設計決定は docstring を参照してください。

---

## 注意事項 / オペレーショナルなポイント

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。
- J-Quants API はレート制限・トークン更新などの考慮が実装されていますが、実運用では ID トークン管理やリトライ設定、監視が必要です。
- AI 呼び出しはコストが掛かるため、バッチサイズや頻度、リトライ挙動に注意してください。失敗時はフェイルセーフで 0.0 スコア等にフォールバックします（例: news_nlp / regime_detector）。
- DuckDB のバージョン依存（executemany の空リスト等）に注意して実装されています。運用環境の DuckDB バージョンに応じたテストを行ってください。

---

ライセンスや詳細な設計ドキュメント（DataPlatform.md、StrategyModel.md など）がリポジトリにある場合はそちらも参照してください。追加で README に記載したい運用手順・設定テンプレート等があればお知らせください。