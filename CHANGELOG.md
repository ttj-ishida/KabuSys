# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な注記:
- 本リリースはパッケージの初期公開版に相当します。
- 日付は本 CHANGELOG 作成日です。

## [Unreleased]

## [0.1.0] - 2026-03-19

### Added
- パッケージの初期実装を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本構成
  - src/kabusys/__init__.py: パッケージ公開 API（data, strategy, execution, monitoring）を定義。

- 環境設定・読み込み
  - src/kabusys/config.py:
    - .env ファイルおよび OS 環境変数からの設定読み込み機能を実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env パースの堅牢化（コメント/export形式、シングル/ダブルクォート、エスケープ処理対応）。
    - .env と .env.local の読み込み優先度制御（OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化可能。
    - Settings クラスで各種必須設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス等）。
    - KABUSYS_ENV / LOG_LEVEL の入力検証とユーティリティプロパティ（is_live, is_paper, is_dev）。

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。
    - レート制限対応（固定間隔スロットリング、120 req/min）。
    - リトライ戦略（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ。
    - ページネーション対応（pagination_key を利用して全件取得）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
      - fetched_at を UTC ISO 形式で記録（Look-ahead バイアス対策）。
      - 冪等性を保証するため ON CONFLICT DO UPDATE を使用。
    - 型変換ユーティリティ（_to_float, _to_int）:
      - 空文字や不正値は None を返す。
      - "1.0" のような float 文字列を安全に int に変換するロジック。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィードから記事を取得して raw_news に保存するモジュール。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等への防御）。
      - SSRF 防止: リダイレクト毎にスキーム/ホスト検証を行うカスタムリダイレクトハンドラ、プライベート IP 判定。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ制限（最大 10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - コンテンツ整形:
      - URL 除去、空白正規化を行う preprocess_text。
      - URL 正規化・トラッキングパラメータ除去（_normalize_url）および正規化 URL からの SHA-256 ベース記事ID生成（先頭32文字）。
      - pubDate の RFC2822 パースと UTC への正規化（失敗時は現在時刻で代替）。
    - DB 保存:
      - raw_news 保存はチャンク処理とトランザクションで実装（INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用）。
      - news_symbols の紐付け保存もチャンク & トランザクションで行い、実際に挿入された件数を返す。
    - 銘柄コード抽出:
      - 4桁の数字を候補として抽出し、known_codes に含まれるもののみを採用（重複排除）。

- リサーチ（特徴量探索・ファクター）
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQLで一括取得）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク計算で実装、レコード不足時は None）。
    - ランク関数 rank（同順位の平均ランク、丸めにより浮動小数系の ties 検出漏れを抑制）。
    - factor_summary（count/mean/std/min/max/median を標準ライブラリのみで計算）。
    - 実装設計方針: DuckDB の prices_daily テーブルのみ参照、外部 API にはアクセスしない。

  - src/kabusys/research/factor_research.py:
    - モメンタム calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev、データ不足時は None）。
    - ボラティリティ calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）。
    - バリュー calc_value（raw_financials から最新財務を取得して PER/ROE を計算）。
    - DuckDB を利用したウィンドウ関数/集約による効率的な実装。
    - 実装設計方針: prices_daily / raw_financials のみ参照、本番 API には接続しない。

- スキーマ初期化
  - src/kabusys/data/schema.py:
    - DuckDB 用の DDL 定義を追加（Raw Layer のテーブル定義など）。
    - raw_prices, raw_financials, raw_news 等の CREATE TABLE 文を定義。
    - （部分表示）raw_executions の DDL の追加を含む設計（実行・約定データ用）。

- public API エクスポート
  - src/kabusys/research/__init__.py: 主要関数を __all__ でエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS フィード取得における SSRF 対策、defusedxml 利用、レスポンス上限チェック（news_collector）。
- 環境変数読み込みにおける不要な上書き防止（protected set）により OS 環境変数の安全性を確保（config）。
- ネットワーク/API クライアントでの堅牢なエラーハンドリングとリトライロジック（jquants_client）。

---

注: 実装は DuckDB を前提とした設計になっており、各関数は prices_daily / raw_financials / raw_news 等のテーブル存在を前提としています。運用時はスキーマ初期化や必要な環境変数（.env.example を参照）の設定を行ってください。