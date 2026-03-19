CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
-------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能群を追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にてバージョン（0.1.0）と公開モジュール一覧を定義。
  - 設定管理
    - src/kabusys/config.py
      - .env ファイルと環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）。
      - .env / .env.local の読み込み優先度制御、既存 OS 環境変数保護（protected keys）を実装。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
      - 環境値のパース（export プレフィックス、クォート・エスケープ、行内コメントなどに対応）。
      - Settings クラスを提供（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、環境モード検証、ログレベル検証など）。
      - env / log_level の検証ロジック、および is_live/is_paper/is_dev のヘルパーを実装。
  - Data レイヤー
    - src/kabusys/data/schema.py
      - DuckDB 用のスキーマ定義（Raw Layer のテーブル定義を含む初期DDLを追加）。
    - src/kabusys/data/jquants_client.py
      - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
      - HTTP リトライ（指数バックオフ）、対象ステータスコードの再試行、429 の Retry-After 処理、最大リトライ回数の設定。
      - 401 受信時の自動トークンリフレッシュを実装（1 回限定のリトライ）。トークン取得用 get_id_token を提供。
      - ページネーション対応のデータ取得関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
      - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT を用いた更新戦略。
      - 型安全な変換ユーティリティ _to_float / _to_int を実装（空値・形式不正時の取り扱い明示）。
    - src/kabusys/data/news_collector.py
      - RSS からニュースを収集して DuckDB に保存する機能を実装。
      - セキュリティ対策:
        - defusedxml による XML パース（XML Bomb 等への保護）。
        - SSRF 対策: リダイレクト時のスキーム検証、ホストがプライベートアドレスでないことの事前検証、カスタム RedirectHandler による検査。
        - 非 http/https スキーム拒否。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）の導入と過剰サイズ検出（gzip 解凍後も検査）。
      - URL 正規化とトラッキングパラメータ除去（_normalize_url）。正規化 URL から SHA-256 ハッシュ（先頭32文字）で記事IDを生成。
      - テキスト前処理（URL除去・空白正規化）。
      - RSS の取得・パース（fetch_rss）、記事の冪等保存（save_raw_news: INSERT ... RETURNING を使用、チャンク & 単一トランザクション）、記事と銘柄コード紐付け（save_news_symbols / _save_news_symbols_bulk）。
      - 銘柄コード抽出（4桁数字、known_codes によるフィルタリング）。
      - run_news_collection による全ソース収集ワークフロー。個別ソースでのエラーは他ソースに影響させず続行。
  - Research レイヤー
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns: DuckDB の prices_daily を参照して指定ホライズン（デフォルト [1,5,21]）の将来リターンを効率的に取得。
      - IC（Information Coefficient）計算 calc_ic: factor_records と forward_records を code で結合し、スピアマンランク相関を計算。データ不足時は None を返す。
      - rank, factor_summary といった統計ユーティリティを実装（外部ライブラリに依存しない、標準ライブラリのみで実装）。
    - src/kabusys/research/factor_research.py
      - 複数のファクター計算を実装:
        - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率(ma200_dev) を計算。データ不足の扱いが明確化。
        - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播制御あり。
        - calc_value: raw_financials から最新財務情報を取得して PER/ROE を計算（報告日以前の最新レコードを取得）。
      - 各関数は DuckDB 接続を受け取り prices_daily/raw_financials のみ参照する設計（外部 API へのアクセスは行わない）。
    - src/kabusys/research/__init__.py で主要な関数をエクスポート（calc_momentum 等、zscore_normalize の import を含む）。
  - その他
    - 空のパッケージプレースホルダ: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を追加（将来の拡張のための名前空間）。

Security
- news_collector の設計で複数の SSRF / XML インジェクション / 大容量応答に対する保護を実装。
- jquants_client は認証トークンの自動更新処理を実装し、不正な無限再帰を防止するための allow_refresh フラグを導入。

Changed
- （初版のため特になし）

Fixed
- （初版のため特になし）

Notes / Implementation details
- DuckDB の SQL は可能な限りウィンドウ関数を活用して効率的に計算する設計（スキャン範囲をカレンダーバッファで制限するなどの工夫あり）。
- 外部依存について:
  - research モジュールは pandas 等に依存せず標準ライブラリのみで動作するように設計されています。
  - news_collector は defusedxml を使用して安全に XML をパースします。
- エラーハンドリングとログ出力を重視。各処理は適切にログを残し、トランザクション整合性を確保しています（news_collector の DB 書き込みはトランザクションで保護）。

--- 

注記:
- 本 CHANGELOG はソースコードから推測して作成した概要です。実際のリリースノートや追加の変更点（ドキュメント、テスト、CI 設定等）は別途反映してください。