CHANGELOG
=========

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-03-18
-----------------

Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージ公開情報
    - src/kabusys/__init__.py によりパッケージ名と __version__="0.1.0" を定義。サブパッケージとして data/ strategy/ execution/ monitoring を公開。
  - 環境変数 / 設定管理
    - src/kabusys/config.py
      - プロジェクトルート検出: .git または pyproject.toml を基準に自動でプロジェクトルートを探索するロジックを追加。パッケージ配布後もカレントワーキングディレクトリに依存しない設計。
      - .env 自動読み込み機能: OS 環境変数 > .env.local > .env の順で読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - .env パーサー: export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理など実務的なパースに対応。
      - 設定ラッパー Settings を提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）・ログレベルの検証機能を追加。
  - Data レイヤー（DuckDB 連携）
    - src/kabusys/data/schema.py
      - Raw Layer のテーブル DDL（raw_prices / raw_financials / raw_news / raw_executions 等）を定義するモジュールを追加（DuckDB 用のスキーマ初期化向け）。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - API 呼び出しユーティリティを実装。120 req/min のレート制限を守る固定間隔スロットリング（_RateLimiter）を導入。
      - リトライ戦略（指数バックオフ、最大 3 回）とステータス別処理（408/429/5xx の再試行、429 の Retry-After 優先）を実装。
      - 401 Unauthorized を検知した際の ID トークン自動リフレッシュ（1 回だけ）を実装。
      - ページネーション対応の取得関数を追加（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
      - DuckDB への冪等保存関数を追加（save_daily_quotes / save_financial_statements / save_market_calendar）。INSERT ... ON CONFLICT DO UPDATE により重複を排除。fetched_at を UTC で記録して Look-ahead Bias を防止。
      - 型変換ユーティリティ（_to_float / _to_int）を実装し、不正値の扱いを明確化。
  - ニュース収集（RSS）
    - src/kabusys/data/news_collector.py
      - RSS フィードから記事取得・前処理・DuckDB 保存までの一連処理を実装。
      - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト先のスキーム/ホスト検証、プライベートIP の判定）、許可スキームは http/https のみ。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES: 10MB）や gzip 解凍後のサイズ検証による DoS 対策を実装。
      - 記事 ID の生成は URL 正規化（トラッキングパラメータ削除、ソート、フラグメント除去）後の SHA-256 ハッシュ先頭 32 文字で冪等性を保証。
      - テキスト前処理（URL 削除・空白正規化）と pubDate の堅牢なパース（失敗時は現在時刻で代替）を実装。
      - DB 保存はチャンク単位で INSERT ... RETURNING を使い、1 トランザクションで処理。news_symbols の一括保存用ヘルパーも実装。
      - 銘柄コード抽出ユーティリティ（4桁コードの正規表現 + known_codes によるフィルタ）を追加。
      - 統合ジョブ run_news_collection により複数ソースの取得・保存・銘柄紐付けを実行。
  - Research / Feature 工具
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算 calc_forward_returns を実装（DuckDB の prices_daily を参照）。複数ホライズンをまとめて取得し、欠損は None を返す設計。
      - IC（Information Coefficient）計算 calc_ic（Spearman の ρ）を実装。ランク関数 rank（同順位は平均ランク、丸め処理で ties 検出を安定化）を提供。
      - ファクターの統計要約 factor_summary（count/mean/std/min/max/median）を実装。
      - 実装は標準ライブラリのみでの依存に抑える設計。
    - src/kabusys/research/factor_research.py
      - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
        - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）。データ不足時は None。
        - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。true_range の NULL 伝播を注意深く扱う。
        - calc_value: raw_financials から直近の財務データを取得し PER / ROE を計算（EPS 欠損/0 の場合は None）。
      - DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番発注 API にはアクセスしない設計。
    - src/kabusys/research/__init__.py
      - 主要な関数をパッケージ公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - その他
    - いくつかのモジュールで詳細なログ出力（logger.debug/info/warning/exception）を追加し、障害解析や運用観察を容易に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector: XML パースは defusedxml を利用して XML 関連の攻撃を軽減。
- news_collector: SSRF 対策（リダイレクト検査、プライベートIP 判定）、許可スキーム制限、レスポンスサイズ検査、gzip 解凍後の上限チェックを導入。
- jquants_client: トークン自動リフレッシュとリトライ制御により認証・ネットワーク障害に対する堅牢性を向上。

Notes / Limitations
- DuckDB のスキーマ定義は Raw Layer（および一部 Execution Layer）まで用意されていますが、プロジェクト全体の DDL は将来的に拡張される想定です（本リリースでは一部定義が途中まで）。
- research モジュールは外部依存（pandas 等）を使わない設計ですが、大規模データでのパフォーマンスチューニングや並列処理は今後の改善候補です。
- news_collector の URL 正規化やトラッキング除去ロジックは一般的なケースを想定しており、特殊なフィードの実装差異には追加対応が必要になる場合があります。

作者
- KabuSys 開発チーム

（以降のリリースでは Unreleased セクションに変更を追加の上、バージョンを上げて記載してください）