KEEP A CHANGELOG形式に準拠した CHANGELOG.md（日本語）を作成しました。初回リリース（0.1.0）向けの内容は、提示されたコードベースから推測して要点をまとめています。必要に応じて日付や項目を調整してください。

------------------------------------------------------------
CHANGELOG
=========

すべての変更は "Keep a Changelog" のガイドラインに従い、意味のあるカテゴリに分類して記録します。

[Unreleased]
-----------

- （現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-18
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルートとバージョン: src/kabusys/__init__.py に __version__ = "0.1.0"
- 設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの自動読み込み機能を実装
    - 自動読み込みの優先度: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）
  - .env パーサが以下をサポート
    - コメント・空行無視、export KEY=val 形式、シングル／ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱い
    - override / protected オプションで OS 環境変数保護
  - 必須設定取得（_require）、環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）の検証、各種設定プロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パスなど）
  - 有効な KABUSYS_ENV 値: development / paper_trading / live （不正値は例外）

- データ層（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出しユーティリティ(_request) を実装（JSON パース、エラーハンドリング）
    - レート制限（120 req/min）を固定間隔スロットリングで実装する _RateLimiter
    - 再試行ロジック（指数バックオフ、最大3回）、429 の Retry-After を尊重
    - 401 受信時の自動トークンリフレッシュ（1 回まで）とトークンキャッシュ共有
    - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements
    - JPX マーケットカレンダー取得: fetch_market_calendar
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）
    - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と不正値判定）
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得と前処理（URL 除去、空白正規化）を実装
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）
      - リダイレクト時にスキーム/プライベートアドレス検査を行う _SSRFBlockRedirectHandler
      - ホストがプライベート/ループバック/リンクローカルかを判定する _is_private_host
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍時の追加検査（Gzip bomb 対策）
    - defusedxml を用いた安全な XML パース（XML Bomb 等への防御）
    - DB 保存:
      - save_raw_news: チャンク INSERT + INSERT ... RETURNING id で新規挿入 ID を取得、1 トランザクションで処理
      - save_news_symbols / _save_news_symbols_bulk: news と銘柄コードの紐付けをチャンクで保存（重複除去、INSERT ... RETURNING で実挿入数を取得）
    - 銘柄抽出: 正規表現で 4 桁銘柄コードを抽出し、既知コードセットに基づいてフィルタ（重複排除）

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用 DDL（Raw レイヤ）を追加:
    - raw_prices, raw_financials, raw_news, raw_executions（DDL 定義を含む）
  - スキーマ管理・初期化の基盤となるモジュールを追加

- リサーチ／特徴量（src/kabusys/research）
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一括取得
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（None/非有限値除外、レコード数 < 3 は None）
    - rank: 同順位は平均ランクとして扱うランク変換（round(..., 12) で ties 検出の安定化）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算
    - 設計方針: DuckDB の prices_daily のみ参照し、本番口座・発注 API にはアクセスしない。標準ライブラリのみで実装。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を算出。NULL 伝播や欠損の扱いに注意した実装。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し、PER（EPS が 0/欠損なら None）・ROE を計算。
    - 設計方針: prices_daily / raw_financials のみ参照、DuckDB のウィンドウ関数を多用して一括計算。結果は (date, code) ベースの dict リストで返す。
  - re-export: research パッケージで主要関数を __all__ にて公開（zscore_normalize は data.stats から）

Changed
- -（初回リリースのため過去バージョンからの変更は無し）

Fixed
- -（初回リリースのため過去バージョンからの修正は無し）

Security
- ニュース収集における SSRF 対策、defusedxml による安全な XML パース、レスポンスサイズ上限と Gzip 解凍後チェックなど、外部入力・ネットワーク処理に対する複数の防御策を導入。
- J-Quants クライアントでのトークン管理と最小限のリトライポリシーにより、不正な認証状態への対処を実装。

Deprecated
- -（なし）

Notes / Known limitations
- strategy および execution パッケージの __init__.py は存在するが、発注ロジックなど実装は含まれていない（初期段階）。
- calc_value は PER/ROE を実装しており PBR・配当利回りは未実装（将来追加予定）。
- schema.py の raw_executions DDL が途中で切れている（提示コードの都合）。実運用時は完全な DDL を確認・整備すること。
- research モジュールは外部ライブラリ（pandas など）に依存せずに純 Python/SQL で実装されているため、大規模データ処理時のパフォーマンス要件は実データで検証が必要。

Acknowledgements
- この CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際のリリースノートとして使用する場合は、開発履歴・コミットログ・実装者の確認により補完してください。

------------------------------------------------------------

必要ならば
- 日付の変更、より詳細な改修内容（各関数の引数変更・戻り値の変化）、あるいは影響範囲（破壊的変更）の追記を行えます。
- また、各ファイルごとの小さな修正を個別のエントリとして分解することも可能です。どの粒度で記載したいか教えてください。