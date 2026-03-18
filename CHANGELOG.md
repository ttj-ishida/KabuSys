# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

通常のリリースカテゴリ: Added / Changed / Fixed / Removed / Deprecated / Security

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回公開リリース。

### Added
- パッケージの基本構成を追加
  - kabusys パッケージのエントリポイント（src/kabusys/__init__.py, __version__ = "0.1.0"）

- 環境変数/設定管理
  - .env ファイル自動読み込み機能（プロジェクトルート = .git または pyproject.toml を検出）
  - .env と .env.local の優先度制御（OS 環境変数 > .env.local > .env）
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 高度な .env パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメント処理対応）
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス /環境種別等のプロパティを取得可能
  - KABUSYS_ENV / LOG_LEVEL の検証ロジック（有効値チェック）

- Data レイヤー（DuckDB 統合）
  - DuckDB スキーマ定義モジュールを追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）
  - データ保存処理（冪等性を考慮した INSERT ... ON CONFLICT）を想定した設計

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足・財務・マーケットカレンダー等の取得関数を実装（ページネーション対応）
  - レート制御: 固定間隔スロットリング（120 req/min）を実装
  - リトライロジック: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx をリトライ対象とする実装
  - 401 発生時の自動トークンリフレッシュと 1 回の再試行対応
  - ページネーション間でのトークン共有（モジュールレベルキャッシュ）
  - DuckDB への保存用ユーティリティ: save_daily_quotes/save_financial_statements/save_market_calendar（冪等）
  - 入力変換ユーティリティ: _to_float / _to_int（堅牢なパース）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得 + 前処理 + raw_news テーブルへの保存ワークフローを実装
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事 ID (SHA-256 の先頭 32 文字) 生成
  - XML パースに defusedxml を使用して XML 攻撃を軽減
  - SSRF 対策:
    - URL スキーム検証 (http/https のみ)
    - リダイレクト時のスキーム/ホスト事前検査（プライベートアドレス拒否）
    - ホストがプライベートアドレスかを判定する実装（DNS 解決と IP 判定）
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip データ解凍後の検査（Gzip bomb 対策）
  - テキスト前処理（URL 除去、空白正規化）
  - 銘柄コード抽出（4桁数字、既知銘柄セットでフィルタ）
  - DB 保存はチャンク分割およびトランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数を取得

- Research モジュール（kabusys.research）
  - ファクター探索 / 解析ユーティリティを実装
  - feature_exploration:
    - calc_forward_returns: 将来リターン（1/5/21営業日等）を DuckDB の prices_daily から一括計算
    - calc_ic: スピアマンランク相関に基づく Information Coefficient 計算（ランク処理・ties 平均ランク対応）
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算
    - rank: 値リストを平均ランクに変換（round(..., 12) による丸めで ties 検出安定化）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m / ma200_dev（200日移動平均乖離）を計算
    - calc_volatility: 20日 ATR, ATR 比率, 平均売買代金, 出来高比率 を計算
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算（最新財務データの取得）

- モジュール公開
  - kabusys.research.__init__ で主要関数群を __all__ に追加して一括 import を容易に

- 空ディレクトリプレースホルダ
  - execution, strategy, monitoring のパッケージ初期化ファイルを用意（拡張準備）

### Changed
- （初回リリースのため差分なし。内部設計注記やログ出力を適宜追加。）

### Fixed
- （初回リリース: 実装時点での入力検証・エラーハンドリングを多数実施）
  - .env 読み込み失敗時の警告出力（warnings.warn）
  - RSS/XML パース失敗やサイズ超過などの条件で早期安全終了するように改良
  - DuckDB への保存時、PK 欠損行のスキップと警告ログ出力

### Security
- ニュース取得で defusedxml を使用して XML 関連攻撃を低減
- SSRF 対策を複数導入（スキーム検証・リダイレクト検査・プライベート IP 拒否）
- HTTP レスポンスのサイズ上限を設け、Gzip 解凍後も検査することで DoS（大容量レスポンス）対策を実施

### Breaking Changes
- なし（初期リリース）。ただし自動 .env 読み込みにより開発環境で環境変数の挙動が変わる可能性があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できる旨を留意してください。

---

注: 本 CHANGELOG はコードベース（src 以下）の実装内容から推測して作成しています。実際の運用や将来の変更に合わせて更新してください。