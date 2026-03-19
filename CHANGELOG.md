CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース: kabusys 初期モジュール群を追加。
  - src/kabusys/__init__.py にバージョン定義とサブパッケージ公開設定を追加。
- 環境設定管理:
  - src/kabusys/config.py を追加。
    - プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みする仕組みを実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。
    - .env の柔軟なパースを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント処理等）。
    - OS 環境変数を保護する protected 上書き制御、必須環境変数チェック関数 _require、enum のような妥当性検査（KABUSYS_ENV、LOG_LEVEL）を提供。
    - settings オブジェクトによるプロパティアクセス（J-Quants トークン、kabu API 設定、Slack、DB パス、実行環境判定等）。
- データ取得・永続化:
  - src/kabusys/data/jquants_client.py を追加。
    - J-Quants API クライアント（価格・財務・カレンダー取得）。
    - 固定間隔のレートリミッタ（120 req/min）実装。
    - リトライ（指数バックオフ）ロジック、HTTP 408/429/5xx の再試行対応、429 の Retry-After 優先処理。
    - 401 受信時にリフレッシュトークンで自動的に id_token を更新して再試行する仕組み（1 回だけ）。
    - ページネーション対応で複数ページを結合して取得。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。fetched_at を UTC ISO 形式で記録し、ON CONFLICT による冪等保存を実現。
    - パースの堅牢化ユーティリティ (_to_float, _to_int) を提供（不正値・空値の安全なハンドリング）。
  - src/kabusys/data/schema.py に DuckDB の初期スキーマ（raw レイヤー等、raw_prices, raw_financials, raw_news, raw_executions 等の DDL）を追加（CREATE TABLE IF NOT EXISTS）。
- ニュース収集:
  - src/kabusys/data/news_collector.py を追加。
    - RSS フィード収集パイプライン（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
    - URL 正規化・トラッキングパラメータ除去、記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - defusedxml を利用した XML パース（XML Bomb 等の防護）。
    - SSRF 対策: 初回検証とリダイレクト時のスキーム検査・プライベートアドレス検査（_is_private_host, _SSRFBlockRedirectHandler）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - 記事テキストの前処理（URL除去・空白正規化）、4桁の銘柄コード抽出ロジック、DB へのバルク挿入をトランザクションで行い INSERT ... RETURNING により実際に挿入された件数を返す。
- 研究（Research）モジュール:
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL で一括取得）、スピアマンランク相関による IC 計算 calc_ic、ランク変換ユーティリティ rank、ファクター統計サマリー factor_summary を実装。
    - 標準ライブラリのみで実装する設計方針（外部ライブラリに依存しない）。
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（calc_momentum: 1M/3M/6M リターン、MA200乖離）、ボラティリティ/流動性（calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比）、バリュー（calc_value: PER/ROE）を実装。
    - prices_daily / raw_financials テーブルのみ参照し、本番 API にはアクセスしない設計。
    - 一部（PBR・配当利回り）は現バージョンでは未実装と明記。
  - src/kabusys/research/__init__.py でユーティリティを公開。
- パッケージ構成:
  - strategy, execution, monitoring サブパッケージのプレースホルダ（__init__.py）を追加して構成を整理。

Changed
- 設計におけるセキュリティと堅牢性の強化。
  - 外部データ取り込み部分に対して SSRF/サイズ攻撃/XML 攻撃対策を盛り込んだ。
  - データ取得・保存は冪等性を重視し、DuckDB 側での重複更新ルール（ON CONFLICT）を採用。

Fixed
- 仕様上のエッジケース対処を多数導入。
  - .env パーサでのクォート・エスケープや行内コメントの誤解析を改善。
  - fetch_rss の gzip 処理や Content-Length の不正値への耐性を追加。
  - jquants_client のページネーション中のトークン共有・キャッシュ処理で無限再帰を防止する allow_refresh 制御を導入。

Security
- defusedxml を用いた XML パース（XML 害悪入力対策）。
- RSS フェッチにおける SSRF 対策（スキーム検証・プライベートアドレス拒否・リダイレクト検査）。
- レスポンスサイズ制限（メモリDoS 対策）および Gzip 解凍後の再チェック。

Notes / Limitations
- research モジュールは標準ライブラリのみで実装されており、大規模データ処理でのパフォーマンス調整や pandas 等による高速化は今後の改善対象。
- factor_research の一部指標（PBR、配当利回り等）は現時点で未実装。
- raw テーブル以外の processed / feature / execution レイヤーの完全な DDL は今後拡張予定（現行は Raw Layer を中心に実装）。

ファイル一覧（主な追加/変更ファイル）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/__init__.py
- src/kabusys/strategy/__init__.py
- src/kabusys/execution/__init__.py

問い合わせ・貢献
- バグ報告や改善提案は issue を通してお願いします。README / ドキュメントに従い、テストと KABUSYS_DISABLE_AUTO_ENV_LOAD を使った検証が可能です。