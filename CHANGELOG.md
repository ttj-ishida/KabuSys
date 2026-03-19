# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

## [0.1.0] - 2026-03-19 (初回リリース)

### 追加 (Added)
- パッケージ基盤
  - パッケージ情報を定義（src/kabusys/__init__.py）。
  - エントリ名前空間として data, strategy, execution, monitoring を公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env / .env.local の自動読み込み（OS 環境変数優先、.env.local は上書き）。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサを実装（export プレフィックス、クォート・エスケープ、コメント処理対応）。
  - Settings クラスを実装し主要設定をプロパティで公開（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル判定など）。
  - 環境値の妥当性チェック（KABUSYS_ENV / LOG_LEVEL の許容値検証）。必須値未設定時は例外を投げる。

- データレイヤ（DuckDB）ユーティリティ
  - スキーマ初期化モジュール（src/kabusys/data/schema.py）に Raw レイヤのテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義）。
  - DuckDB を前提とした冪等保存戦略を想定した設計。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API との通信機能を実装（トークン取得、日足・財務・カレンダー取得）。
  - レート制限管理（固定間隔スロットリング、120 req/min）を実装する RateLimiter。
  - 冪等での DB 保存を想定した fetch/save 連携（ページネーション対応）。
  - リトライロジック（指数バックオフ、最大3回）、HTTP 429 の Retry-After ヘッダ考慮、ネットワークエラーリトライ。
  - 401 受信時の自動トークンリフレッシュを実装（1回のみ再取得してリトライ）。
  - save_* 系関数で fetched_at を UTC ISO8601 で付与、ON CONFLICT DO UPDATE による冪等挿入を実装。
  - 入力データを安全に変換するユーティリティ _to_float / _to_int を実装（不正値は None）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・解析・前処理・DB 保存ワークフローを実装。
  - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
  - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェックでメモリ DoS を軽減。
  - リダイレクト時の SSRF 対策（スキーム検証、プライベート IP 検出によるブロック）を実装するカスタム RedirectHandler と事前ホスト検証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭 32 文字）。
  - テキスト前処理（URL 削除・空白正規化）。
  - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いた新規記事ID取得）を実装。チャンク挿入とトランザクションを採用。
  - news_symbols（記事と銘柄の紐付け）保存をバルクで行う内部ユーティリティを実装。重複除去とチャンク挿入による性能配慮。
  - 記事本文・タイトルから銘柄コード抽出ユーティリティ（4桁数字候補 + known_codes フィルタ）。

- リサーチ用ファクター計算（src/kabusys/research/*）
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1クエリで取得）。
    - ファクターと将来リターンのランク相関（スピアマン ρ）を計算する calc_ic（None / 非有限値除外、最小有効数チェック）。
    - 値リストをランクに変換する rank（同順位は平均ランク、丸めによる ties 対策）。
    - ファクター列の基本統計量を計算する factor_summary（count/mean/std/min/max/median）。
  - factor_research.py
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA 乖離）を DuckDB SQL ウィンドウ関数で計算。データ不足時は None。
    - calc_volatility: 20日 ATR（true range の平均）・相対 ATR、20日平均売買代金・出来高比等を計算。true_range の NULL 伝播制御。
    - calc_value: raw_financials から最新財務を取得して PER, ROE を計算（EPS が 0/欠損なら PER は None）。
  - research/__init__.py で主要関数をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- その他
  - news のデフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
  - 各所でログ出力（logger）を適切に追加。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- news_collector:
  - XML パーサに defusedxml を使用して XML ベース攻撃に対処。
  - リダイレクト先のスキーム/ホスト検証やプライベートアドレス判定により SSRF を緩和。
  - レスポンスサイズ制限と gzip 解凍後の再チェックにより Gzip Bomb / メモリ枯渇攻撃を緩和。

### 既知の制限 / 注意点 (Known issues / Notes)
- research モジュールは外部ライブラリ（pandas など）に依存しない純粋 Python 実装であり、大量データ処理時のメモリ・性能に留意が必要。
- schema.py によるテーブル定義は Raw レイヤ中心のDDLが含まれるが、プロジェクト全体で必要なすべてのテーブル（Processed/Feature/Execution 層など）がこのリリースで完全に定義済みかは確認が必要（部分的に定義が続く想定）。
- data.stats.zscore_normalize は research/__init__.py で参照しているが、本差分に含まれるファイル群に定義の全体が含まれているか確認が必要（別ファイルで提供される想定）。

---

今後のバージョンでは、以下のような改善を予定しています。
- Processed / Feature 層の完全な DDL とマイグレーション機能の追加。
- strategy / execution / monitoring モジュールの具体実装（現在はパッケージ公開のみ）。
- 大量データ処理性能の改善（バルク処理最適化、メモリ使用削減、並列化など）。
- 単体テスト・統合テスト追加および CI の整備。