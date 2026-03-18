# Changelog

すべての注記は Keep a Changelog の方針に従い、重要な変更点を分かりやすくまとめています。  
フォーマット: [Unreleased] / 各リリース (SemVer)。日付はリリース日を示します。

## [Unreleased]
- （今後の開発・追加項目を記載）

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能群を追加しました。以下はコードベースから推測される実装内容と設計方針の要約です。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージのバージョン定義 (__version__ = "0.1.0") と公開モジュール一覧 (__all__) を追加。

- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイルや環境変数から設定を自動読込する機能を実装。
    - プロジェクトルート検出 (pyproject.toml / .git を探索) によりカレントワーキングディレクトリに依存しない自動読み込み。
    - .env のパース実装: export 記法、クォート内のエスケープ、インラインコメント処理などに対応。
    - .env 読み込み時の override/protected の仕組みを導入（OS 環境変数を保護）。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
    - Settings クラスを提供し、必須環境変数取得（_require）と各種プロパティ（J-Quants トークン、kabu API 設定、Slack トークン・チャネル、DB パス、実行環境判定、ログレベル検証など）を型安全に取得・検証。

- データ取得・永続化（J-Quants）
  - src/kabusys/data/jquants_client.py:
    - J-Quants API クライアントを実装。
    - レートリミッタ（固定間隔スロットリング）を実装し、API 制限（120 req/min）を厳守。
    - リトライロジック（指数バックオフ、最大試行回数、特定ステータスでの再試行）を実装。429 の Retry-After を優先。
    - 401 受信時にリフレッシュトークンで自動トークン更新を行い 1 回リトライする仕組みを実装。モジュールレベルのトークンキャッシュ共有。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。fetched_at を UTC で記録し、ON CONFLICT DO UPDATE による冪等性を確保。
    - 数値変換ユーティリティ (_to_float, _to_int) を搭載し不正入力に対処。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 等対策）。
      - SSRF 対策: リダイレクト先のスキーム検証、プライベート IP のブロック（DNS 解決による A/AAAA チェック）、_SSRFBlockRedirectHandler を導入。
      - URL のスキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 展開後の再チェックを導入しメモリ DoS を軽減。
      - トラッキングパラメータ（utm_ 等）の除去と URL 正規化、SHA-256 ベース（先頭32文字）の記事 ID 生成を実装して冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）や pubDate の安全なパース（UTC 正規化）を実装。
    - raw_news / news_symbols へのバルク挿入はチャンク化（最大サイズ）してトランザクション内で行い、INSERT ... RETURNING を用いて実際に挿入された件数を返す設計。
    - 銘柄抽出ユーティリティ（4桁銘柄コードの抽出）を実装し、既知コード集合によるフィルタリングを提供。

- DuckDB スキーマ（スキーマ定義の追加）
  - src/kabusys/data/schema.py:
    - Raw layer のテーブル DDL を定義（raw_prices, raw_financials, raw_news, raw_executions の定義断片を含む）。
    - DataSchema に基づく 3 層構造（Raw / Processed / Feature / Execution）を想定した設計方針を明記。

- 研究用（Research）: ファクター計算と探索
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定日から各ホライズン先までの将来リターンを DuckDB の prices_daily テーブルから一括取得して計算（LEAD を利用）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。ties の扱い、NaN/無限値除外、最小サンプル数チェックを実装。
    - rank: 同順位は平均ランクとするランク化ユーティリティ（小数丸めで ties 判定の安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算するユーティリティ。
    - （外部ライブラリに依存せず標準ライブラリのみで実装する方針を維持）

  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離 (ma200_dev) を計算。ウィンドウ不足時は None を返す。
    - calc_volatility: ATR(20), 相対 ATR (atr_pct), 20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials から target_date 以前の最新財務データを join して PER / ROE を計算（EPS=0 または欠損時は None）。
    - DuckDB 上で SQL ウィンドウ関数を駆使した実装で、prices_daily / raw_financials のみ参照、外部 API は呼ばない設計。

- 研究パッケージの公開インターフェイス
  - src/kabusys/research/__init__.py: 主要関数と zscore_normalize（kabusys.data.stats から）を __all__ で公開。

- モジュール分割/スケルトン
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py: 空のパッケージ初期化ファイルを追加（将来の発注・戦略モジュールのためのプレースホルダ）。
  - これにより top-level の __all__ と整合。

### 変更 (Changed)
- （初回リリースのため該当なし。ただし設計上の重要点を文書化）
  - Look-ahead bias 対策として fetched_at を UTC で記録する方針を明示。
  - DuckDB 保存処理は ON CONFLICT（DO UPDATE / DO NOTHING）を使い冪等性を確保。

### 修正 (Fixed)
- （初回リリースのため該当なし。実装内に含まれる防御的なエラーハンドリングや入力検証を記載）
  - .env パーサの強化（クォート内エスケープ、コメント処理）により .env の解釈誤りを低減。
  - RSS パーサでの不正スキーマ・大容量レスポンス・gzip 解凍エラー等を検知して安全にスキップする実装。

### セキュリティ (Security)
- RSS / HTTP 周りで複数のセキュリティ対策を導入:
  - defusedxml による XML パース。
  - SSRF 対策: リダイレクト先検査、プライベート IP ブロック、スキーム検証。
  - レスポンスサイズの上限チェック（読み込み時と gzip 解凍後）を実施。
- J-Quants クライアントはトークンの自動リフレッシュとキャッシュを備え、不正な再帰や漏洩の回避を考慮。

### 既知の制限・今後の課題 (Known issues / Future)
- strategy や execution のコアロジック（発注戦略、発注 API 呼び出し、ポジション管理など）はまだ実装または公開されておらず、空のパッケージが残っている（プレースホルダ）。
- research モジュールは pandas 等に依存しない方針で標準ライブラリのみで実装されているため、大規模データ処理や高性能な集計は将来的に外部ライブラリ導入を検討する余地がある。
- schema.py は Raw レイヤの DDL を中心に含むが、Processed / Feature / Execution 層の完全な DDL は今後の拡張対象。
- DuckDB に対する接続/トランザクション周りの追加ユーティリティやマイグレーション機能は今後の実装予定。

---

貢献・バグ報告・改善提案はリポジトリの Issue を通じて歓迎します。