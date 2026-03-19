# CHANGELOG

この変更履歴は Keep a Changelog の形式に準拠します。  
コードベースの内容（モジュール、関数、設計コメント）から推測して記載しています。実際のコミット履歴ではなく、現行コードをまとめた「初回公開相当のリリースノート」です。

全般:
- バージョンはパッケージルートの __version__ に従い v0.1.0 として記載しています。
- 日付: 2026-03-19（推定初回リリース日）
- 意図的に外部依存を抑えた実装方針や設計上の注意点（Look-ahead バイアス回避、冪等性、SSRF対策など）が多くのモジュールの docstring に明記されています。

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-03-19
初期リリース。日本株自動売買システム「KabuSys」のコアライブラリを提供します。以下は主要な追加機能・設計上のポイントです。

### Added
- パッケージ基本構成
  - kabusys パッケージのスケルトンを追加（data / research / strategy / execution / monitoring などの名前空間を公開）。
  - __version__ = "0.1.0" を設定。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートの探索は __file__ から親ディレクトリをたどって `.git` または `pyproject.toml` を探す方式（CWD に依存しない挙動）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能（テスト向け）。
  - .env のパースはシェル風の書式（export プレフィックス、シングル/ダブルクォート、インラインコメント等）に対応する堅牢な実装を追加。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パスやログレベル、環境（development/paper_trading/live）等のプロパティを取得。必須環境変数が未設定の場合は ValueError を投げる。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - RateLimiter による 120 req/min の固定間隔スロットリング。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
    - 401 発生時の自動トークンリフレッシュ（1回まで）と ID トークンのモジュールレベルキャッシュ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE により重複を排除。
    - 型変換ユーティリティ (_to_float / _to_int) を追加し不正データに寛容に対応。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集・前処理・DB 保存する一連の機能を提供。
    - URL 正規化（トラッキングパラメータ除去・クエリソート）と記事ID（SHA-256 の先頭32文字）生成。
    - XML パースに defusedxml を使用して XML Bomb 等からの防御。
    - SSRF 対策:
      - リダイレクト時にスキーム検査とホストのプライベート/ループバック判定を行う専用ハンドラ（_SSRFBlockRedirectHandler）。
      - 初期 URL と最終 URL 双方のスキーム/ホスト検証。
      - ホストの DNS 解決結果を検査し、プライベートアドレスアクセスを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）チェックおよび gzip 解凍後の再チェック（Gzip bomb 対策）。
    - テキスト前処理（URL除去、空白正規化）と銘柄コード抽出（4桁数値、known_codes によるフィルタ）。
    - DB 保存はバルク INSERT + INSERT ... RETURNING を用い、チャンク単位でトランザクション管理。raw_news 保存（save_raw_news）と記事-銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）を実装。
    - 集約ジョブ run_news_collection を提供（複数ソースを個別エラーハンドリングで実行）。

- リサーチ／特徴量（kabusys.research）
  - feature_exploration モジュール
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照し、指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマン順位相関（IC）を計算（ties 対応、有効レコード3未満は None）。
    - rank: 同順位の平均ランクを返す実装（round(v,12) による丸めで浮動小数点の tie 判定強化）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値除外）。
  - factor_research モジュール
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算。ウィンドウ不足時は None。
    - calc_volatility: 20日 ATR（avg true range）、相対ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播設計により正確なカウント。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が存在かつ非ゼロの場合）と ROE を算出。最新の target_date 以前の財務レコードを ROW_NUMBER() で拾う実装。
  - モジュール内の関数群は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照する設計（本番発注API へはアクセスしない）。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のテーブル DDL を追加（Raw Layer の raw_prices / raw_financials / raw_news / raw_executions 等の定義を含む）。
  - 初期化のための DDL をコード上に保持（DataSchema.md に基づく3層モデルを想定）。

- ロギングと例外処理
  - 各処理で適切な logger 呼び出し（info/warning/exception/debug）を追加し、運用時の調査性を向上。
  - ネットワーク系や DB トランザクションで例外発生時にロールバックやリトライを行う保護を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （コードから推測される設計改善点を反映した形で初期実装内に盛り込み済み）
  - .env のパースやコメント処理、クォート処理の堅牢化。
  - RSS 処理での不正スキーム・プライベートアドレスや過剰レスポンスサイズを検出してスキップする安全設計。
  - API 呼び出しでのトークン自動リフレッシュとリトライロジックの追加により、一時的な認証/ネットワーク障害耐性を強化。

### Removed
- （初回リリースのため該当なし）

### Security
- news_collector にて SSRF 対策を実装（スキームチェック、プライベートアドレス検出、リダイレクト先事前検査）。
- defusedxml を採用して XML パース時の脆弱性を軽減。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能で、意図しない環境漏洩を抑制。

### Notes / Limitations
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリと DuckDB の SQL を中心に実装されているため、非常に軽量かつデータベース側に依存した設計になっています。一方で大規模な表計算処理やメモリ上での高速集計が必要な場合、追加の最適化や pandas 等の導入を検討してください。
- 一部テーブル（raw_executions 等）の DDL がファイル内で途中まで定義されているため、実際のスキーマ追加や Execution レイヤー実装は継続的な作業が必要です。
- J-Quants クライアントは HTTP/urllib を用いた実装。より柔軟な接続管理や非同期処理が必要であれば将来的に httpx などへの移行を検討できます。

---

今後の予定（例）
- execution/monitoring/strategy モジュールの具体実装（発注連携・モニタリング・ストラテジ実行フロー）。
- schema の完全化とマイグレーションツールの追加。
- 単体テスト・統合テストの追加（.env 自動ロードやネットワーク依存コードのモック化を含む）。
- ドキュメント（Usage, Deployment, DataPipeline）の整備。

（以上）