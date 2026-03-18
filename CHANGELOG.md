CHANGELOG
=========

すべての変更はセマンティックバージョニングに従います。  
このファイルは "Keep a Changelog" の形式に準拠します。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初回リリース: KabuSys 0.1.0
  - top-level:
    - src/kabusys/__init__.py: パッケージ名と __version__ を定義。公開サブパッケージを __all__ で指定。
  - 設定・環境変数管理:
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供（settings インスタンスをモジュールレベルで公開）。
      - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない .env 自動読み込みを実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
      - 強力な .env パーサーを実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント処理など）。
      - 必須キー検査（_require）と環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
  - Data レイヤー（データ取得・保存）:
    - src/kabusys/data/jquants_client.py:
      - J-Quants API クライアントを実装。
      - 固定間隔スロットリングによるレート制限制御（_RateLimiter）。
      - 冪等な DuckDB 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による重複更新をサポート。
      - ページネーション対応の fetch_* 関数（fetch_daily_quotes・fetch_financial_statements）、および市場カレンダー取得。
      - リトライロジック（指数バックオフ、最大3回、408/429/5xx の再試行）、429 の Retry-After を考慮した待機。
      - 401 受信時の自動トークン再取得（get_id_token）とモジュールレベルのトークンキャッシュ。get_id_token 呼び出しの再帰保護。
      - 入出力変換ユーティリティ（_to_float/_to_int）を実装し、受信値の堅牢な正規化を行う。
  - News / テキスト収集:
    - src/kabusys/data/news_collector.py:
      - RSS フィード収集パイプラインを実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
      - セキュリティ強化:
        - defusedxml を使った安全な XML パース（XML Bomb 等に対策）。
        - SSRF 対策: リダイレクト時のスキーム/ホスト検証用ハンドラ（_SSRFBlockRedirectHandler）、事前ホスト検査（_is_private_host）を実装。http/https 以外を拒否。
        - レスポンスサイズ制限（MAX_RESPONSE_BYTES、デフォルト 10 MB）と gzip 解凍後の再検査によりメモリDoS を防止。
      - 記事ID は URL 正規化（トラッキングパラメータ除去、ソート等）→ SHA-256 の先頭32文字で生成し冪等性を確保。
      - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁の数字、known_codes に基づくフィルタ）を実装。
      - DuckDB への保存はチャンク INSERT とトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された件数を正確に取得。
  - Research / 特徴量・ファクター計算:
    - src/kabusys/research/feature_exploration.py:
      - 将来リターン計算（calc_forward_returns）: DuckDB の prices_daily を参照して指定日から各ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
      - IC（Information Coefficient）計算（calc_ic）: ファクター値と将来リターンのスピアマン順位相関を実装。データ不足・定数分散を考慮して None を返す挙動。
      - ランク関数（rank）: 同順位は平均ランクにし、丸め誤差対策（round(..., 12)）を含む実装。
      - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を標準ライブラリのみで計算。
    - src/kabusys/research/factor_research.py:
      - モメンタム（calc_momentum）: 1M/3M/6M リターン、ma200 乖離率（200日移動平均）を計算。データ不足時は None を返す。
      - ボラティリティ・流動性（calc_volatility）: 20日 ATR（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を意図的に制御。
      - バリュー（calc_value）: raw_financials から target_date 以前の最新財務を取得し PER/ROE を計算（EPS が 0/欠損なら PER は None）。
      - 設計方針として DuckDB の prices_daily / raw_financials のみ参照し、外部 API や実際の発注系にアクセスしないことを明記。
    - src/kabusys/research/__init__.py:
      - 主要関数を外部公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - スキーマ
    - src/kabusys/data/schema.py:
      - DuckDB 用の DDL を定義（raw_prices, raw_financials, raw_news, raw_executions など、Raw/Processed/Feature/Execution 層の枠組み）。テーブル定義と初期化の骨格を提供。

Security
- news_collector における SSRF 対策（リダイレクト検査、ホストのプライベートアドレス検出）と defusedxml による XML パースの硬化を導入。
- RSS レスポンスのサイズ上限・gzip 解凍後の再チェックによりリソース消費攻撃を緩和。

Performance & Reliability
- J-Quants クライアントでレート制限（固定間隔スロットリング）と retry/backoff を実装し API レートと一時障害に耐性を追加。
- ページネーション対応（pagination_key）を実装して大量データ取得をサポート。
- DuckDB へのバルク挿入はチャンク／トランザクション化してオーバーヘッドを低減し、INSERT ... RETURNING により正確な挿入件数を把握可能に。

Documentation / Usability
- 各モジュールに詳細な docstring を付与。設計方針と想定利用方法（DuckDB 接続を渡す、外部 API へはアクセスしない等）を明記。
- 環境変数の既定値・必須キーや検証ロジック（KABUSYS_ENV の値制限、LOG_LEVEL 検証）を設定し利用者の誤設定を早期検出。

Notes / Known limitations
- 外部依存: duckdb と defusedxml が想定される（コード内コメント参照）。pandas 等には依存していない旨を明記。
- 一部ファイル（例: execution/__init__.py, strategy/__init__.py）は空のプレースホルダーとして存在。
- 一部スキーマ / テーブル定義はファイル末尾で途切れている（raw_executions の定義が続く想定）。実運用前に完全なスキーマ定義を確認してください。

Closed issues
- （なし：初回リリースのため特定の issue 対応履歴は記載なし）

Breaking Changes
- 初回リリースのため該当なし。