KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
=================================

概要
---
KabuSys は日本株向けのデータ基盤・リサーチ・AIセンチメント・監査・ETL を含む
モジュール群です。J-Quants / RSS / OpenAI を用いたニュースセンチメント集約や、
DuckDB を用いたデータ保存・品質チェック、監査ログ（シグナル→発注→約定）など
自動売買システムのバックボーンとなる機能群を提供します。

主な設計方針
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない）
- DuckDB を中心とした軽量かつ高速なデータ操作（SQL + Python）
- 外部 API 呼び出しはリトライ・レート制御を備えフェールセーフ化
- 各操作は冪等性（idempotent）を重視して設計

機能一覧
---
- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と Settings API
- データ ETL（J-Quants）
  - 株価日足（OHLCV）・財務データ・JPX カレンダーの差分取得と保存
  - ETL 結果を表す ETLResult クラス、品質チェックの自動実行
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、銘柄紐付け
  - SSRF 対策・受信サイズ制限・トラッキングパラメータ除去などの安全処理
- AI（OpenAI）を用いた NLP
  - 銘柄ごとのニュースセンチメント（ai_scores への書き込み）
  - マクロセンチメント + ETF MA200乖離を用いた市場レジーム判定（bull/neutral/bear）
  - API 呼び出しは JSON Mode・リトライ・フェイルセーフを実装
- リサーチ（ファクター計算）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 発注フローの完全トレースを想定した UUID ベースの設計

セットアップ手順
---
前提
- Python 3.10 以上（typing の | 記法、PEP 604 を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI 呼び出しを行う場合）
- ネットワークアクセス（J-Quants / RSS / OpenAI）

推奨インストール（仮想環境を使用）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. このリポジトリを開発モードでインストール（任意）
   - git clone <repo>
   - cd <repo>
   - python -m pip install -e .

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml の位置）から .env/.env.local を自動読み込みします。
  読み込み順は OS 環境変数 > .env.local > .env です。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

最低限必要な環境変数（例）
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...          （AI 機能を使う場合）
- KABU_API_PASSWORD=...        （kabuステーション API を使う場合）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi   （必要に応じて）
- DUCKDB_PATH=data/kabusys.duckdb   （デフォルト）
- SQLITE_PATH=data/monitoring.db    （監視 DB 用）

例 .env.template
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

使い方（簡単なコード例）
---
1) Settings の利用（環境変数読み込み）
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト

2) DuckDB 接続と日次 ETL 実行
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースセンチメントスコアを生成（AI 必須）
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ書き込まれます

5) 監査ログスキーマの初期化 / 監査 DB 作成
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db(settings.duckdb_path)  # 既存 DB に監査テーブルを作成
# transaction=True/False を選択するオプションあり

注意事項 / トラブルシューティング
- 環境変数未設定による例外
  - settings.jquants_refresh_token など必須変数が未設定だと ValueError が発生します。
- OpenAI / J-Quants API のレート制限・認証
  - J-Quants はレート制御（120 req/min）とトークンリフレッシュ対応を実装していますが、
    API キー・リフレッシュトークンは正しく設定してください。
  - OpenAI 呼び出しはリトライ実装がありますが、API の料金や利用制限に注意してください。
- DuckDB バージョンとの互換性
  - 一部 executemany の挙動やリストバインドの互換性に注意（コード内で対応済み）。
- ニュース収集
  - RSS の取得中に URL の検証（スキーム/プライベートIP 判定）やサイズ制限を行います。失敗時はログに出ます。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                         — 環境設定読み込み / Settings
- ai/
  - __init__.py
  - news_nlp.py                      — ニュースセンチメント（ai_scores 生成）
  - regime_detector.py               — マクロ + MA200 による市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
  - etl.py                           — ETL 結果クラス ETLResult のエクスポート
  - jquants_client.py                — J-Quants API クライアント / 保存ロジック
  - news_collector.py                — RSS 収集・整形・保存ロジック
  - calendar_management.py           — 市場カレンダー管理（営業日判定等）
  - quality.py                       — データ品質チェック
  - stats.py                         — 共通統計ユーティリティ（z-score）
  - audit.py                         — 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py               — Momentum/Value/Volatility 計算
  - feature_exploration.py           — 将来リターン・IC・統計サマリー
- research/* / ai/* / data/* ...     — その他ユーティリティ・補助関数

開発メモ
- テストでは API 呼び出しをモック（unittest.mock.patch）して外部依存を切り離す設計になっています。
- datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を渡すことでバックテストでも安全に利用できます。

ライセンス
---
（この README にはライセンス情報を含めていません。リポジトリの LICENSE ファイルをご確認ください）

お問い合わせ / 貢献
---
不具合・機能追加提案は issue を作成してください。プルリクエスト歓迎です。README の改善提案も歓迎します。

以上が簡易 README です。必要であれば利用例・API リファレンス・運用手順（cron/監視・ロギング設定・データバックアップ等）を追加で作成します。どの章を詳しくしたいか教えてください。