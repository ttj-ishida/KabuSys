# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠しています。  
このファイルはコードベースから推測して作成された変更履歴です（自動生成・推測によるため細部は実実装と差異がある場合があります）。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-18
初回リリース

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys（バージョン: 0.1.0）
  - top-level エクスポート: data, strategy, execution, monitoring

- 環境設定管理
  - 環境変数を .env / .env.local / OS 環境から自動読み込み（プロジェクトルートは .git / pyproject.toml を基準に探索）
  - 自動ロード抑止フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサー: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、無効行（空行/コメント）スキップ
  - 上書き制御: .env と .env.local の読み込み順と override の挙動（保護された OS 環境変数を上書きしない仕組み）
  - Settings クラス: 必須設定取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、デフォルト値（API ベース URL、DB パス等）、環境値検証（KABUSYS_ENV, LOG_LEVEL）、利便性フラグ（is_live / is_paper / is_dev）

- データ取得・永続化（kabusys.data）
  - J-Quants API クライアント（data/jquants_client.py）
    - レート制限保護（120 req/min 固定間隔スロットリング）
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx を対象）
    - 401 発生時の ID トークン自動リフレッシュ（1 回のみ、再帰防止）
    - ページネーション対応（pagination_key の追跡）
    - UTC での fetched_at 記録により Look-ahead バイアスを抑止可能
    - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 用の save_* 関数、ON CONFLICT DO UPDATE）
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な空値・不正文字列処理）
  - ニュース収集モジュール（data/news_collector.py）
    - RSS フィード取得（gzip 対応、Content-Length/応答サイズ上限チェック、最大 10MB）
    - defusedxml による XML パース（XML Bomb 対策）
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前ホスト検査、プライベートIP/ループバックのブロック
    - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除）
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保
    - テキスト前処理（URL 除去、空白正規化）
    - DuckDB へのバルク挿入（チャンク処理、INSERT ... RETURNING を使用して実挿入数を返却、トランザクション管理）
    - 銘柄コード抽出ユーティリティ（4桁数値の抽出と既知コードフィルタ）
    - 統合ジョブ run_news_collection：複数ソースの個別エラーハンドリング、記事保存→銘柄紐付けの一連処理
  - DB スキーマ定義（data/schema.py）
    - Raw Layer のテーブル DDL 定義（raw_prices, raw_financials, raw_news, raw_executions 等の基本構造）
    - 初期化用スクリプトを想定した DDL を提供

- リサーチ機能（kabusys.research）
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（1/5/21 日等のホライズン対応、単一クエリで複数ホライズン取得）
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関、欠損/無効値除外、最小サンプルチェック）
    - 基本統計量 factor_summary（count/mean/std/min/max/median）
    - ランク関数 rank（同順位は平均ランク、丸めによる ties 検出改善）
    - 設計上: DuckDB の prices_daily テーブルのみ参照、標準ライブラリのみで実装（外部依存を排除）
  - ファクター計算（research/factor_research.py）
    - モメンタム calc_momentum（1M/3M/6M、200日移動平均乖離率、データ不足時は None）
    - ボラティリティ/流動性 calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - バリュー calc_value（raw_financials から直近財務を取得して PER/ROE を算出）
    - DuckDB の prices_daily / raw_financials のみ参照する設計で、本番 API へアクセスしない点を明示

- ロギング・診断
  - 各モジュールでの情報 / 警告 / 例外ログ追加（例: fetch_* の取得件数ログ、保存時のスキップ件数警告、XML/Gzip/HTTP の失敗ログ等）

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース収集における複数のセキュリティ対策を実装
  - defusedxml による安全な XML パース
  - SSRF 緩和（スキーム検証、プライベートIPのチェック、リダイレクト先事前検査）
  - レスポンスサイズ上限チェックと Gzip 解凍後のサイズ検査（DoS 緩和）

### Notes
- research モジュールは外部ライブラリ（pandas など）に依存しない実装を目指しているため、大規模データ処理時のパフォーマンス評価・チューニングが必要な場合があります。
- DuckDB スキーマ定義は Raw Layer の DDL を含むが、プロジェクト全体のスキーマ（Processed / Feature / Execution 層）は今後の拡張を想定しています。
- news_collector の既知銘柄抽出は known_codes を渡すことを前提としている（渡さない場合は紐付けをスキップ）。

---

作成: 自動生成（ソースコード解析に基づく推測）  
補足・修正が必要な箇所があればお知らせください。